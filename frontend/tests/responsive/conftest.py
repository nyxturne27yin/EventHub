from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


FRONTEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def frontend_url():
    handler = partial(
        SimpleHTTPRequestHandler,
        directory=str(FRONTEND_DIR),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


@pytest.fixture(scope="session")
def browser():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)

    yield driver

    driver.quit()
