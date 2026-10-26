import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import URL

_test_database_directory = tempfile.TemporaryDirectory(prefix='campus_trade_test_')
_test_database_path = Path(_test_database_directory.name) / 'campus_trade_test.sqlite'
os.environ['SQLALCHEMY_DATABASE_URI'] = URL.create(
    'sqlite', database=str(_test_database_path)
).render_as_string(hide_password=False)

from app import create_app, db
from models import Address, EmailCode, Favorite, Order, OrderMessage, Product, ProductCategory, User


@pytest.fixture(scope='session')
def test_app():
    app = create_app('testing')

    with app.app_context():
        if db.engine.url.get_backend_name() != 'sqlite':
            raise RuntimeError('Tests must use an isolated SQLite database')
        db.create_all()
        yield app
        db.drop_all()
        db.session.remove()
        db.engine.dispose()
    _test_database_directory.cleanup()


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