import errno
from threading import Thread

import pytest
import requests
from werkzeug.serving import make_server


@pytest.fixture(scope='session')
def api_base_url(test_app):
    server = None
    for port in range(18765, 18865):
        try:
            server = make_server('127.0.0.1', port, test_app, threaded=True)
            break
        except OSError as error:
            if error.errno != errno.EADDRINUSE and getattr(error, 'winerror', None) != 10048:
                raise
    if server is None:
        raise RuntimeError('No available local port for the API test server')

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture
def http():
    client = requests.Session()
    yield client
    client.close()
