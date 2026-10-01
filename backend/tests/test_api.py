import io

from fastapi.testclient import TestClient
from PIL import Image

from app import db
from app.main import app


def png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 9), color=(48, 112, 97)).save(output, format="PNG")
    return output.getvalue()


def test_health_never_returns_api_key(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "health.sqlite3"))
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    db.initialize_database()
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["gemini_configured"] is True
    assert "api_key" not in response.json()
    assert "not-a-real-key" not in response.text


def test_unsupported_upload_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "unsupported.sqlite3"))
    db.initialize_database()
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"file": ("notes.txt", b"not media", "text/plain")})
    assert response.status_code == 415


def test_corrupt_image_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "corrupt.sqlite3"))
    db.initialize_database()
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"file": ("broken.png", b"not an image", "image/png")})
    assert response.status_code == 422


def test_oversized_upload_is_rejected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "oversized.sqlite3"))
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "32")
    db.initialize_database()
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"file": ("large.png", png_bytes(), "image/png")})
    assert response.status_code == 413


def test_image_upload_returns_persisted_analysis(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "analysis.sqlite3"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "100000")
    db.initialize_database()
    with TestClient(app) as client:
        response = client.post("/api/analyze", files={"file": ("sample.png", png_bytes(), "image/png")})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "queued"
        analysis = client.get("/api/analyze/{}".format(payload["id"]))
        evidence = client.get("/api/analyze/{}/evidence".format(payload["id"]))
        timeline = client.get("/api/analyze/{}/timeline".format(payload["id"]))
        report = client.get("/api/analyze/{}/report".format(payload["id"]))
        pdf = client.get("/api/analyze/{}/report.pdf".format(payload["id"]))
    assert analysis.status_code == 200
    result = analysis.json()
    assert result["status"] == "completed"
    assert result["trust_state"] == "INSUFFICIENT / CONFLICTING"
    assert result["media_kind"] == "image"
    assert result["gemini"]["status"] == "not_configured"
    assert result["evidence"]
    assert "fabricated" in " ".join(result["limitations"])
    assert evidence.status_code == 200
    assert evidence.json()["evidence"] == result["evidence"]
    assert timeline.status_code == 200
    assert report.status_code == 200
    assert report.json()["trust_state"] == result["trust_state"]
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
