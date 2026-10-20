import re
import sys
from pathlib import Path

import pyotp
import pytest
from cryptography.fernet import Fernet

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    """Import the Flask app with an isolated working directory and datastore."""
    monkeypatch.setenv("DB_SECRET_KEY", Fernet.generate_key().decode())
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(REPO_ROOT))

    for name in ["app", "utility", "utility.data_function", "utility.hash_function"]:
        sys.modules.pop(name, None)

    import app as application

    application.app.config.update(TESTING=True)
    yield application

    for name in ["app", "utility", "utility.data_function", "utility.hash_function"]:
        sys.modules.pop(name, None)


def test_full_passwordless_flow(app_module):
    application = app_module
    client = application.app.test_client()

    assert client.get("/").status_code == 302
    assert client.get("/register").status_code == 200

    response = client.post("/register", data={"email": "demo@example.com"})
    assert response.status_code == 302
    assert "/setup" in response.headers["Location"]

    response = client.get("/setup")
    assert response.status_code == 200
    assert b"data:image/png;base64" in response.data

    token = pyotp.TOTP(application.db["secret"]).now()
    response = client.post("/verify-setup", data={"token": token})
    assert response.status_code == 200

    recovery_codes = re.findall(rb'<div class="code-box">([0-9a-f]{8})</div>', response.data)
    assert len(recovery_codes) == 5
    assert (Path.cwd() / "database.json").read_bytes().startswith(b"gAAAAA")

    # Setup cannot be repeated after the account is active.
    response = client.post("/verify-setup", data={"token": token})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    assert b"Benvenuto" in client.get("/dashboard").data
    client.get("/logout")

    login_token = pyotp.TOTP(application.db["secret"]).now()
    response = client.post("/login", data={"token": login_token})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

    # The same TOTP cannot be replayed.
    assert client.post("/login", data={"token": login_token}).status_code == 400

    client.get("/logout")

    # Recovery codes are single-use.
    recovery_code = recovery_codes[0].decode()
    response = client.post("/recovery", data={"token": recovery_code})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]

    client.get("/logout")
    assert client.post("/recovery", data={"token": recovery_code}).status_code == 401

    # Five failures lock both login and recovery.
    wrong_code = next(
        f"{value:08x}" for value in range(1000)
        if f"{value:08x}".encode() not in recovery_codes
    )
    for _ in range(4):
        assert client.post("/recovery", data={"token": wrong_code}).status_code == 401

    assert client.get("/login").status_code == 403
    assert client.get("/recovery").status_code == 403


def test_recovery_code_hashing_is_salted():
    from utility.hash_function import hash_code, verify_code

    first_hash = hash_code("a1b2c3d4")
    second_hash = hash_code("a1b2c3d4")

    assert first_hash != second_hash
    assert verify_code("a1b2c3d4", first_hash)
    assert not verify_code("wrong-code", first_hash)
