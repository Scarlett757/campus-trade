from datetime import datetime, timedelta

import pytest

from app import db
from models import EmailCode, User

pytestmark = pytest.mark.login


@pytest.mark.parametrize(
    'email, password, expected_success',
    [
        ('student@example.test', 'SecurePass123!', True),
        ('', 'SecurePass123!', False),
        ('student@example.test', '', False),
        ('existing@example.test', 'SecurePass123!', False),
    ],
)
def test_register_boundary(client, email, password, expected_success):
    db.session.add(
        EmailCode(
            email=email,
            code='123456',
            create_time=datetime.now() - timedelta(minutes=1),
        )
    )
    if email == 'existing@example.test':
        db.session.add(
            User(email=email, username='Existing', password='ExistingPass123!')
        )
    db.session.commit()

    response = client.post(
        '/register',
        data={
            'email': email,
            'username': 'Test User',
            'password': password,
            'confirm': password,
            'code': '123456',
        },
    )

    assert response.status_code == 200
    assert response.get_json()['result'] is expected_success, response.get_json()
    user = User.query.filter_by(email=email).first() if email else None
    if expected_success:
        assert user is not None
        assert user.check_password(password)
        assert user.password_hashed != password
        assert EmailCode.query.filter_by(email=email).count() == 0
    elif email == 'existing@example.test':
        assert user is not None
        assert user.username == 'Existing'
    elif email:
        assert user is None


class TestUserLogin:
    @pytest.fixture(autouse=True)
    def setup_data(self, client):
        db.session.add(
            User(
                username='test_username',
                email='testuser@example.test',
                password='SecurePass123!',
            )
        )
        db.session.commit()
        with client.session_transaction() as user_session:
            user_session.clear()

    @pytest.mark.parametrize(
        'email, password, expected_success',
        [
            ('testuser@example.test', 'SecurePass123!', True),
            ('nobody@example.test', 'SecurePass123!', False),
            ('testuser@example.test', 'WrongPassword', False),
            ('', 'SecurePass123!', False),
            ('testuser@example.test', '', False),
        ],
    )
    def test_login_boundary(self, client, email, password, expected_success):
        response = client.post(
            '/login',
            data={'email': email, 'password': password},
            headers={'Accept': 'application/json'},
        )
        result = response.get_json()

        assert response.status_code == 200
        assert result['result'] is expected_success
        if expected_success:
            assert response.headers.get('Set-Cookie')
            with client.session_transaction() as user_session:
                assert user_session.get('user_id') is not None
        else:
            assert '邮箱或密码错误' in result['message']
