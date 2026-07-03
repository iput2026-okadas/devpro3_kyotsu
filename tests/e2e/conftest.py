import os
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT_DIR / "Server"
FIXTURE_DIR = ROOT_DIR / "tests" / "fixtures" / "csv_viewer"


def _find_available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(
    base_url: str, process: subprocess.Popen[str], timeout: float = 10
) -> None:
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            pytest.fail(f"Flask server exited before startup:\n{stderr}")

        try:
            with urlopen(base_url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.1)

    pytest.fail(f"Flask server did not start within {timeout} seconds")


@pytest.fixture(scope="session")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    data_dir = tmp_path_factory.mktemp("csv-viewer-data")
    for csv_file in FIXTURE_DIR.glob("data-*.csv"):
        shutil.copy2(csv_file, data_dir / csv_file.name)

    port = _find_available_port()
    url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["E2E_DATA_DIR"] = str(data_dir)
    env["E2E_PORT"] = str(port)

    command = (
        "import os\n"
        "from pathlib import Path\n"
        "import app as csv_app\n"
        "csv_app.DATA_DIR = Path(os.environ['E2E_DATA_DIR'])\n"
        "csv_app.app.run("
        "host='127.0.0.1', "
        "port=int(os.environ['E2E_PORT']), "
        "debug=False, "
        "use_reloader=False"
        ")\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", command],
        cwd=SERVER_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_server(url, process)
        yield url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    headless = os.environ.get("E2E_HEADLESS", "true").lower() not in {
        "0",
        "false",
        "no",
    }
    slow_mo = float(os.environ.get("E2E_SLOW_MO", "0"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        yield browser
        browser.close()


@pytest.fixture
def page(browser: Browser) -> Iterator[Page]:
    context = browser.new_context(accept_downloads=True)
    context.route("https://fonts.googleapis.com/**", lambda route: route.abort())
    page = context.new_page()
    yield page
    context.close()
