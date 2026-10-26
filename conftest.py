import pytest
from app import create_app, db # 工厂函数隔绝
from sqlalchemy import URL
from models import Address, EmailCode, Favorite, Order, OrderMessage, Product, ProductCategory, User


@pytest.fixture(scope='session')
def test_app(tmp_path_factory):
    app = create_app('testing')

    # Use an isolated file database so the threaded requests test server can
    # safely use independent SQLite connections without touching the dev DB.
    database_path = tmp_path_factory.getbasetemp() / 'campus_trade_test.sqlite'
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': URL.create(
            'sqlite', database=str(database_path)
        ).render_as_string(hide_password=False),
        'WTF_CSRF_ENABLED': False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='session')
def client(test_app):
    return test_app.test_client()


@pytest.fixture(autouse=True)
def clean_db(test_app):
    db.session.rollback()
    db.session.remove()
    for model in (OrderMessage, Favorite, Order, Address, Product, EmailCode, User, ProductCategory):
        db.session.execute(db.delete(model))
    db.session.commit()
    yield
    db.session.rollback()
    db.session.remove()