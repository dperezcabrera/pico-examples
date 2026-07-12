import pytest

CONFIG = {
    "fastapi": {"title": "secure-notes"},
    "server_auth": {
        "issuer": "http://notes.local",
        "audience": "notes",
        "auto_create_admin": True,
        "admin_email": "admin@notes.local",
        "admin_password": "secret",
        "admin_role": "admin",
    },
    "auth_client": {"enabled": True, "issuer": "http://notes.local", "audience": "notes"},
}


@pytest.fixture
def harness(make_container, make_client, monkeypatch):
    container = make_container("pico_fastapi", "pico_server_auth", "pico_client_auth", config=CONFIG)
    client = make_client(container)

    # In production the validator fetches the JWKS over HTTP from the issuer.
    # Here issuer and API are the same in-process app: capture the key set
    # up front and hand it to the validator without touching the network.
    from pico_client_auth.jwks_client import JWKSClient

    jwks = client.get("/api/v1/auth/jwks").json()

    async def _fetch_captured(self):
        self._keys = {k["kid"]: k for k in jwks["keys"]}
        self._fetched_at = float("inf")

    monkeypatch.setattr(JWKSClient, "_fetch_keys", _fetch_captured)
    return client, container


def login(client) -> dict:
    r = client.post("/api/v1/auth/login", json={"email": "admin@notes.local", "password": "secret"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_reads_are_public(harness):
    client, _ = harness
    assert client.get("/api/v1/notes").status_code == 200


def test_writes_require_a_token(harness):
    client, _ = harness
    assert client.post("/api/v1/notes", json={"text": "x"}).status_code == 401


def test_full_flow_with_issued_token(harness):
    client, _ = harness
    headers = login(client)
    note_id = client.post("/api/v1/notes", json={"text": "rotate the tokens"}, headers=headers).json()["id"]
    assert {"id": note_id, "text": "rotate the tokens"} in client.get("/api/v1/notes").json()
    assert client.delete(f"/api/v1/notes/{note_id}", headers=headers).json() == {"deleted": note_id}


def test_delete_requires_admin_role(harness):
    client, container = harness
    from pico_server_auth import TokenIssuer

    # same issuer, valid signature, but role=user: create is allowed, delete is not
    token = container.get(TokenIssuer).issue_access_token(subject="eve@notes.local", role="user")
    headers = {"Authorization": f"Bearer {token}"}
    note_id = client.post("/api/v1/notes", json={"text": "mine"}, headers=headers).json()["id"]
    assert client.delete(f"/api/v1/notes/{note_id}", headers=headers).status_code == 403
