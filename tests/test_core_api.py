from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import requests

from app import db
from models import Address, EmailCode, Order, OrderMessage, OrderStatus, Product, ProductCategory, User

pytestmark = pytest.mark.api


@pytest.fixture
def market():
    seller = User(email='seller@example.test', username='Seller', password='SellerPass123!')
    buyer = User(email='buyer@example.test', username='Buyer', password='BuyerPass123!')
    other = User(email='other@example.test', username='Other', password='OtherPass123!')
    db.session.add_all([seller, buyer, other])
    db.session.flush()

    buyer_address = Address(
        user_id=buyer.id, receiver='Buyer', phone='13800000000',
        province='Test', city='Test', district='Test', detail='Buyer address',
    )
    other_address = Address(
        user_id=other.id, receiver='Other', phone='13900000000',
        province='Test', city='Test', district='Test', detail='Other address',
    )
    product = Product(
        name='Used textbook', content='Good condition', price=10.0, num=1,
        picture='book.png', origin_place='Campus', ship_name='Pickup',
        category_id=1, publisher_id=seller.id,
    )
    category = ProductCategory(name='Books')
    db.session.add(category)
    db.session.flush()
    product.category_id = category.id
    db.session.add_all([buyer_address, other_address, product])
    db.session.commit()
    return {
        'seller_id': seller.id,
        'buyer_id': buyer.id,
        'other_id': other.id,
        'buyer_address_id': buyer_address.id,
        'other_address_id': other_address.id,
        'product_id': product.id,
    }


def login_client(client, base_url, email, password):
    response = client.post(
        f'{base_url}/login',
        json={'email': email, 'password': password},
    )
    assert response.status_code == 200
    assert response.json()['result'] is True, response.json()


def refresh_database_session():
    db.session.remove()


def test_login_required_order_endpoint_redirects_anonymous_request(http, api_base_url, market):
    response = http.post(
        f'{api_base_url}/api/order/create',
        json={'product_id': market['product_id'], 'address_id': market['buyer_address_id']},
    )
    assert response.history
    assert response.history[0].status_code == 302
    assert response.url.endswith('/login')


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {},
        {'product_id': 'not-an-id', 'address_id': 1},
        {'product_id': 1},
        {'product_id': 0, 'address_id': 1},
    ],
)
@pytest.mark.order
def test_order_create_rejects_invalid_payloads(http, api_base_url, market, payload):
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    response = http.post(f'{api_base_url}/api/order/create', json=payload)
    assert response.status_code == 400
    assert db.session.query(Order).count() == 0
    assert db.session.get(Product, market['product_id']).num == 1


@pytest.mark.order
def test_order_failure_rolls_back_stock_and_order(http, api_base_url, market):
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    with patch('app.db.session.commit', side_effect=RuntimeError('simulated commit failure')):
        response = http.post(
            f'{api_base_url}/api/order/create',
            json={'product_id': market['product_id'], 'address_id': market['buyer_address_id']},
        )

    assert response.status_code == 500
    refresh_database_session()
    assert db.session.get(Product, market['product_id']).num == 1
    assert Order.query.count() == 0
    assert OrderMessage.query.count() == 0


@pytest.mark.order
def test_create_order_decrements_stock_and_creates_order_with_message(http, api_base_url, market):
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    response = http.post(
        f'{api_base_url}/api/order/create',
        json={'product_id': market['product_id'], 'address_id': market['buyer_address_id']},
    )

    assert response.status_code == 200
    assert response.json()['success'] is True
    order_id = response.json()['order_id']
    refresh_database_session()
    order = db.session.get(Order, order_id)
    assert order.status is OrderStatus.PAID
    assert order.buyer_id == market['buyer_id']
    assert order.seller_id == market['seller_id']
    assert order.price == 10.0
    assert db.session.get(Product, market['product_id']).num == 0
    assert OrderMessage.query.filter_by(order_id=order.id, msg_type='system').count() == 1


@pytest.mark.order
def test_concurrent_orders_cannot_oversell_single_unit(api_base_url, market):
    clients = []
    for _ in range(2):
        client = requests.Session()
        client.headers['Connection'] = 'close'
        login_client(client, api_base_url, 'buyer@example.test', 'BuyerPass123!')
        clients.append(client)

    def submit_order(client):
        return client.post(
                f'{api_base_url}/api/order/create',
                json={'product_id': market['product_id'], 'address_id': market['buyer_address_id']},
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(submit_order, clients))
    finally:
        for client in clients:
            client.close()

    assert sorted(response.status_code for response in responses) == [200, 400]
    refresh_database_session()
    assert db.session.get(Product, market['product_id']).num == 0
    assert Order.query.filter_by(product_id=market['product_id']).count() == 1
    assert OrderMessage.query.filter(OrderMessage.msg_type == 'system').count() == 1


@pytest.mark.parametrize(
    ('product_owner', 'stock', 'address_key', 'expected_status'),
    [
        ('seller', 0, 'buyer_address_id', 400),
        ('seller', 1, 'other_address_id', 400),
        ('buyer', 1, 'buyer_address_id', 400),
    ],
)
def test_order_rejects_sold_out_self_purchase_and_foreign_address(
    http, api_base_url, market, product_owner, stock, address_key, expected_status
):
    product = db.session.get(Product, market['product_id'])
    product.num = stock
    if product_owner == 'buyer':
        product.publisher_id = market['buyer_id']
    db.session.commit()

    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    response = http.post(
        f'{api_base_url}/api/order/create',
        json={
            'product_id': market['product_id'],
            'address_id': market[address_key],
        },
    )
    assert response.status_code == expected_status
    assert Order.query.count() == 0


def test_order_create_returns_not_found_for_missing_product(http, api_base_url, market):
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    response = http.post(
        f'{api_base_url}/api/order/create',
        json={'product_id': 999999, 'address_id': market['buyer_address_id']},
    )
    assert response.status_code == 404
    assert Order.query.count() == 0


@pytest.mark.order
@pytest.mark.security
def test_only_seller_can_ship_and_repeated_transition_is_rejected(http, api_base_url, market):
    order = Order(
        order_no='TEST-SHIP-1', buyer_id=market['buyer_id'], seller_id=market['seller_id'],
        product_id=market['product_id'], price=10.0, address_id=market['buyer_address_id'],
        status=OrderStatus.PAID,
    )
    db.session.add(order)
    db.session.commit()

    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    denied = http.post(f'{api_base_url}/api/order/{order.id}/ship')
    assert denied.status_code == 403

    http.cookies.clear()
    login_client(http, api_base_url, 'seller@example.test', 'SellerPass123!')
    shipped = http.post(f'{api_base_url}/api/order/{order.id}/ship')
    repeated = http.post(f'{api_base_url}/api/order/{order.id}/ship')

    assert shipped.status_code == 200
    order_id = order.id
    refresh_database_session()
    assert db.session.get(Order, order_id).status is OrderStatus.SHIPPED
    assert repeated.status_code == 400
    assert OrderMessage.query.filter_by(order_id=order.id, msg_type='system').count() == 1


def test_order_lists_are_scoped_to_logged_in_user(http, api_base_url, market):
    order = Order(
        order_no='TEST-LIST-1', buyer_id=market['buyer_id'], seller_id=market['seller_id'],
        product_id=market['product_id'], price=10.0, address_id=market['buyer_address_id'],
        status=OrderStatus.PAID,
    )
    db.session.add(order)
    db.session.commit()

    login_client(http, api_base_url, 'other@example.test', 'OtherPass123!')
    assert http.get(f'{api_base_url}/api/orders?role=buyer').json() == []
    assert http.get(f'{api_base_url}/api/orders?role=seller').json() == []

    http.cookies.clear()
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    buyer_orders = http.get(f'{api_base_url}/api/orders?role=buyer').json()
    assert [item['order_no'] for item in buyer_orders] == ['TEST-LIST-1']


@pytest.mark.security
@pytest.mark.parametrize('method', ['get', 'post'])
def test_non_participant_cannot_access_order_messages(http, api_base_url, market, method):
    order = Order(
        order_no='TEST-MSG-1', buyer_id=market['buyer_id'], seller_id=market['seller_id'],
        product_id=market['product_id'], price=10.0, address_id=market['buyer_address_id'],
        status=OrderStatus.PAID,
    )
    db.session.add(order)
    db.session.commit()
    login_client(http, api_base_url, 'other@example.test', 'OtherPass123!')

    response = getattr(http, method)(
        f'{api_base_url}/api/order/{order.id}/messages',
        json={'content': 'Should not be visible'},
    )
    assert response.status_code == 403
    assert OrderMessage.query.filter_by(order_id=order.id, msg_type='text').count() == 0


@pytest.mark.security
def test_non_participant_cannot_open_order_chat_page(http, api_base_url, market):
    order = Order(
        order_no='TEST-CHAT-1', buyer_id=market['buyer_id'], seller_id=market['seller_id'],
        product_id=market['product_id'], price=10.0, address_id=market['buyer_address_id'],
        status=OrderStatus.PAID,
    )
    db.session.add(order)
    db.session.commit()
    login_client(http, api_base_url, 'other@example.test', 'OtherPass123!')

    response = http.get(f'{api_base_url}/order/{order.id}/chat')
    assert response.status_code == 403


@pytest.mark.parametrize('payload', [None, {}, {'content': '   '}, {'content': 42}])
def test_order_messages_reject_invalid_payloads(http, api_base_url, market, payload):
    order = Order(
        order_no='TEST-MSG-INVALID', buyer_id=market['buyer_id'], seller_id=market['seller_id'],
        product_id=market['product_id'], price=10.0, address_id=market['buyer_address_id'],
        status=OrderStatus.PAID,
    )
    db.session.add(order)
    db.session.commit()
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')

    response = http.post(
        f'{api_base_url}/api/order/{order.id}/messages',
        json=payload,
    )
    assert response.status_code == 400
    assert OrderMessage.query.filter_by(order_id=order.id, msg_type='text').count() == 0


@pytest.mark.security
@pytest.mark.parametrize('method, path_suffix', [
    ('put', ''),
    ('delete', ''),
    ('post', '/default'),
])
def test_address_mutations_reject_another_users_address(
    http, api_base_url, market, method, path_suffix
):
    login_client(http, api_base_url, 'buyer@example.test', 'BuyerPass123!')
    response = getattr(http, method)(
        f'{api_base_url}/api/address/{market["other_address_id"]}{path_suffix}',
        json={
            'receiver': 'Changed', 'phone': '13700000000', 'province': 'P',
            'city': 'C', 'district': 'D', 'detail': 'Changed',
        },
    )
    assert response.status_code == 403
    assert db.session.get(Address, market['other_address_id']).receiver == 'Other'


@pytest.mark.email_code
def test_registration_accepts_matching_recent_code_and_consumes_it(http, api_base_url):
    code = EmailCode(
        email='new-user@example.test',
        code='123456',
        create_time=datetime.now() - timedelta(minutes=1),
    )
    db.session.add(code)
    db.session.commit()

    response = http.post(
        f'{api_base_url}/register',
        data={
            'email': code.email, 'username': 'New User', 'password': 'SecurePass123!',
            'code': code.code,
        },
    )
    assert response.status_code == 200
    assert response.json()['result'] is True, response.json()
    email = code.email
    refresh_database_session()
    user = User.query.filter_by(email=email).one()
    assert user.check_password('SecurePass123!')
    assert user.password_hashed != 'SecurePass123!'
    assert EmailCode.query.filter_by(email=email).count() == 0

    repeated = http.post(
        f'{api_base_url}/register',
        data={
            'email': email, 'username': 'New User', 'password': 'SecurePass123!',
            'code': '123456',
        },
    )
    assert repeated.json()['result'] is False
    refresh_database_session()
    assert User.query.filter_by(email=email).count() == 1


@pytest.mark.email_code
@pytest.mark.parametrize(
    'email, code_email, code_value, age_minutes',
    [
        ('target@example.test', 'other@example.test', '123456', 0),
        ('target@example.test', 'target@example.test', 'wrong', 0),
        ('target@example.test', 'target@example.test', '123456', -31),
        ('target@example.test', 'target@example.test', '123456', 1),
    ],
)
def test_registration_rejects_mismatched_invalid_or_expired_codes(
    http, api_base_url, email, code_email, code_value, age_minutes
):
    db.session.add(EmailCode(
        email=code_email,
        code=code_value,
        create_time=datetime.now() + timedelta(minutes=age_minutes),
    ))
    db.session.commit()
    response = http.post(
        f'{api_base_url}/register',
        data={'email': email, 'username': 'Target', 'password': 'SecurePass123!', 'code': '123456'},
    )
    assert response.status_code == 200
    refresh_database_session()
    assert response.json()['result'] is False
    assert User.query.filter_by(email=email).count() == 0


@pytest.mark.email_code
@pytest.mark.parametrize(
    'data',
    [
        {'username': 'Missing email', 'password': 'SecurePass123!', 'code': '123456'},
        {'email': 'missing-password@example.test', 'username': 'Missing password', 'code': '123456'},
        {'email': 'missing-code@example.test', 'username': 'Missing code', 'password': 'SecurePass123!'},
    ],
)
def test_registration_rejects_missing_required_fields(http, api_base_url, data):
    response = http.post(f'{api_base_url}/register', data=data)
    assert response.status_code == 200
    assert response.json()['result'] is False
    assert User.query.count() == 0


@pytest.mark.email_code
@pytest.mark.parametrize('email', [None, '', 'not-an-email'])
def test_email_code_endpoint_does_not_send_for_invalid_email(http, api_base_url, email):
    with patch('app.mail.send') as send_mail:
        params = {} if email is None else {'email': email}
        response = http.get(f'{api_base_url}/email/code', params=params)
    assert response.status_code == 200
    assert response.json()['request'] is False
    send_mail.assert_not_called()


@pytest.mark.email_code
def test_email_code_endpoint_persists_code_after_successful_send(http, api_base_url):
    email = 'verification@example.test'
    with patch('app.mail.send') as send_mail:
        response = http.get(f'{api_base_url}/email/code', params={'email': email})
    assert response.status_code == 200
    assert response.json()['request'] is True
    send_mail.assert_called_once()
    refresh_database_session()
    saved_code = EmailCode.query.filter_by(email=email).one()
    assert len(saved_code.code) == 6
    assert saved_code.code.isdigit()


@pytest.mark.email_code
def test_email_code_endpoint_does_not_persist_when_delivery_fails(http, api_base_url):
    email = 'delivery-failure@example.test'
    with patch('app.mail.send', side_effect=RuntimeError('mail unavailable')):
        response = http.get(f'{api_base_url}/email/code', params={'email': email})

    assert response.status_code == 200
    assert response.json()['request'] is False
    refresh_database_session()
    assert EmailCode.query.filter_by(email=email).count() == 0
