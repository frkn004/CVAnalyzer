import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import os
from unittest.mock import patch

client = TestClient(app)

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

def test_root():
    """Kök endpoint testi"""
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "system_info" in response.json()
    assert response.json()["status"] == "active"

@patch('os.path.exists')
def test_analyze_cv_endpoint(mock_exists, sample_cv_file):
    """CV analiz endpoint'i testi"""
    mock_exists.return_value = True
    
    with open(sample_cv_file, "rb") as f:
        response = client.post(
            "/analyze-cv",
            files={"file": ("test_cv.txt", f, "text/plain")}
        )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "kisisel_bilgiler" in result
    assert "egitim" in result
    assert "deneyimler" in result
    assert "beceriler" in result

@patch('os.path.exists')
def test_match_cv_endpoint(mock_exists, sample_cv_file, sample_position):
    """CV eşleştirme endpoint'i testi"""
    mock_exists.return_value = True
    
    with open(sample_cv_file, "rb") as f:
        response = client.post(
            "/match-cv",
            files={"file": ("test_cv.txt", f, "text/plain")},
            json=sample_position
        )
    
    assert response.status_code == 200
    result = response.json()
    
    assert "genel_skor" in result
    assert "kategori_skorlari" in result
    assert "guclu_yonler" in result
    assert "eksik_yonler" in result
    assert "tavsiyeler" in result

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
        response = client.post(
            "/match-cv",
            files={"file": ("test_cv.txt", f, "text/plain")},
            json={"invalid": "data"}
        )
    
    assert response.status_code == 422  # Validation Error

def test_analyze_cv_empty_file():
    """Boş dosya testi"""
    response = client.post(
        "/analyze-cv",
        files={"file": ("empty.txt", b"", "text/plain")}
    )
    
    assert response.status_code == 400
    assert "CV metnini çıkarma başarısız" in response.json()["detail"] 