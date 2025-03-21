import pytest
from pathlib import Path
from src.processors.document_processor import DocumentProcessor

@pytest.fixture
def processor():
    """Belge işlemci fixture'ı"""
    return DocumentProcessor()

@pytest.fixture
def sample_txt_file(tmp_path):
    """Örnek TXT dosyası oluşturur"""
    file_path = tmp_path / "test.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Test içeriği")
    return file_path

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Örnek PDF dosyası oluşturur"""
    # TODO: PDF dosyası oluşturma kodu eklenecek
    pass

@pytest.fixture
def sample_docx_path(tmp_path):
    """Örnek DOCX dosyası oluşturur"""
    # TODO: DOCX dosyası oluşturma kodu eklenecek
    pass

def test_extract_text_txt(processor, sample_txt_file):
    """TXT dosyası okuma testi"""
    text = processor.extract_text(str(sample_txt_file))
    assert text == "Test içeriği"

def test_extract_text_invalid_file(processor):
    """Geçersiz dosya testi"""
    with pytest.raises(ValueError) as exc_info:
        processor.extract_text("nonexistent.txt")
    assert "Dosya bulunamadı" in str(exc_info.value)

def test_extract_text_unsupported_format(processor, tmp_path):
    """Desteklenmeyen format testi"""
    file_path = tmp_path / "test.xyz"
    file_path.touch()
    with pytest.raises(ValueError) as exc_info:
        processor.extract_text(str(file_path))
    assert "Desteklenmeyen dosya formatı" in str(exc_info.value)

def test_analyze_cv(processor):
    """CV analiz testi"""
    text = """John Doe
john@example.com
+90 555 123 4567

Eğitim:
XYZ Üniversitesi, Bilgisayar Mühendisliği, 2015-2019

Deneyim:
ABC Şirketi, Python Geliştirici, 2019-2023
- Python ve FastAPI ile web servisleri geliştirdim
- Docker ve Kubernetes ile mikroservis mimarisi kurdum

Beceriler:
Python, FastAPI, Docker, Kubernetes, PostgreSQL"""

    result = processor.analyze_cv(text)
    assert result["personal_info"]["name"] == "John Doe"
    assert result["personal_info"]["email"] == "john@example.com" 