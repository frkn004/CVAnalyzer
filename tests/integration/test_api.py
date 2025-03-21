import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import os
import json
from unittest.mock import patch, MagicMock
from io import BytesIO

client = TestClient(app)

@pytest.fixture
def sample_cv_file():
    return {
        "file": ("test.txt", "John Doe\njohn@example.com", "text/plain")
    }

@pytest.fixture
def sample_position_data():
    return {
        "title": "Python Developer",
        "description": "We are looking for a Python developer",
        "requirements": ["Python", "FastAPI", "Docker"]
    }

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "system_info" in response.json()

def test_analyze_cv_endpoint():
    content = "John Doe\njohn@example.com"
    files = {"file": ("test.txt", content.encode(), "text/plain")}
    response = client.post("/analyze-cv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "personal_info" in data
    assert data["personal_info"]["name"] == "John Doe"
    assert data["personal_info"]["email"] == "john@example.com"

def test_analyze_cv_empty_file():
    files = {"file": ("empty.txt", b"", "text/plain")}
    response = client.post("/analyze-cv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "personal_info" in data
    assert data["personal_info"]["name"] == ""
    assert data["personal_info"]["email"] == ""

def test_match_cv_endpoint():
    content = "John Doe\nPython Developer\n5 years experience"
    files = {"file": ("test.txt", content.encode(), "text/plain")}
    position_data = {
        "title": "Python Developer",
        "description": "We are looking for a Python developer",
        "requirements": ["Python", "FastAPI", "Docker"]
    }
    response = client.post(
        "/match-cv",
        files=files,
        data={"position": json.dumps(position_data)}
    )
    assert response.status_code == 200
    data = response.json()
    assert "match_score" in data
    assert "category_scores" in data
    assert "strengths" in data
    assert "weaknesses" in data
    assert "recommendations" in data

def test_match_cv_invalid_position():
    content = "John Doe\nPython Developer"
    files = {"file": ("test.txt", content.encode(), "text/plain")}
    invalid_position = {"invalid": "data"}
    response = client.post(
        "/match-cv",
        files=files,
        data={"position": json.dumps(invalid_position)}
    )
    assert response.status_code == 400
    assert "detail" in response.json()

def test_analyze_cv_invalid_file():
    files = {"file": ("test.bin", b"\x00\x01", "application/octet-stream")}
    response = client.post("/analyze-cv", files=files)
    assert response.status_code == 400
    assert "detail" in response.json()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.fixture
def sample_cv_file(tmp_path):
    """Örnek CV dosyası oluşturur"""
    content = """John Doe
john.doe@email.com
+90 555 123 4567

EĞİTİM
XYZ Üniversitesi, Bilgisayar Mühendisliği (2015-2019)

DENEYİM
ABC Teknoloji - Senior Developer (2019-2023)
- Python ve FastAPI ile backend geliştirme
- Docker ve Kubernetes ile deployment
- AWS servisleri yönetimi

BECERİLER
Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL"""

    file_path = tmp_path / "test_cv.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path

@pytest.fixture
def sample_position():
    """Örnek pozisyon verisi"""
    return {
        "title": "Senior Python Developer",
        "description": "Backend geliştirme pozisyonu",
        "requirements": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AWS"]
    }

def test_analyze_cv_invalid_file():
    """Geçersiz dosya formatı testi"""
    response = client.post(
        "/analyze-cv",
        files={"file": ("test.xyz", b"invalid content", "text/plain")}
    )
    
    assert response.status_code == 400
    assert "Desteklenmeyen dosya formatı" in response.json()["detail"]

def test_match_cv_invalid_position(sample_cv_file):
    """Geçersiz pozisyon verisi testi"""
    with open(sample_cv_file, "rb") as f:
        files = {"file": ("test_cv.txt", f, "text/plain")}
        data = {"position": json.dumps({"invalid": "data"})}
        response = client.post(
            "/match-cv",
            files=files,
            data=data
        )
    
    assert response.status_code == 400
    assert "Geçersiz pozisyon verisi" in response.json()["detail"] 