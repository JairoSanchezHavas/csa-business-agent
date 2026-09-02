import hmac, hashlib, json, pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings

from app.database import init_db

init_db()
client = TestClient(app)
settings = get_settings()

def generate_signature(payload_bytes: bytes, secret: str) -> str:
    mac = hmac.new(key=secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

def test_handshake_success():
    resp = client.get("/webhook", params={"hub.mode": "subscribe", "hub.challenge": "12345", "hub.verify_token": settings.VERIFY_TOKEN})
    assert resp.status_code == 200
    assert resp.text == "12345"

def test_handshake_invalid():
    resp = client.get("/webhook", params={"hub.mode": "subscribe", "hub.challenge": "12345", "hub.verify_token": "invalido"})
    assert resp.status_code == 403

def test_post_invalid_signature():
    payload = json.dumps({"test": "data"}).encode("utf-8")
    sig = generate_signature(payload, "clave_falsa")
    resp = client.post("/webhook", content=payload, headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
    assert resp.status_code == 403

def test_dashboard_get():
    resp = client.get("/dashboard")
    assert resp.status_code == 200

