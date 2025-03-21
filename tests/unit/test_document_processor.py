import pytest
import os
from src.processors.document_processor import DocumentProcessor
from docx import Document
from PyPDF2 import PdfWriter

@pytest.fixture
def doc_processor():
    return DocumentProcessor()

@pytest.fixture
def sample_text():
    return """John Doe
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

@pytest.fixture
def temp_txt_file(tmp_path, sample_text):
    file_path = tmp_path / "test.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(sample_text)
    return file_path

@pytest.fixture
def temp_docx_file(tmp_path, sample_text):
    file_path = tmp_path / "test.docx"
    doc = Document()
    doc.add_paragraph(sample_text)
    doc.save(str(file_path))
    return file_path

@pytest.fixture
def temp_pdf_file(tmp_path, sample_text):
    file_path = tmp_path / "test.pdf"
    writer = PdfWriter()
    # TODO: PDF oluşturma işlemi eklenecek
    return file_path

def test_supported_extensions(doc_processor):
    """Desteklenen dosya uzantılarını test eder"""
    assert '.pdf' in doc_processor.supported_extensions
    assert '.docx' in doc_processor.supported_extensions
    assert '.txt' in doc_processor.supported_extensions
    assert len(doc_processor.supported_extensions) == 3

def test_extract_from_txt(doc_processor, temp_txt_file, sample_text):
    """TXT dosyasından metin çıkarma işlemini test eder"""
    extracted_text = doc_processor.extract_text(str(temp_txt_file))
    assert extracted_text is not None
    
    # Email adresi korunmalı
    assert "john.doe@email.com" in extracted_text
    
    # Telefon numarası korunmalı
    assert "+90 555 123 4567" in extracted_text
    
    # Gereksiz boşluklar temizlenmeli
    assert "  " not in extracted_text

def test_extract_from_docx(doc_processor, temp_docx_file, sample_text):
    """DOCX dosyasından metin çıkarma işlemini test eder"""
    extracted_text = doc_processor.extract_text(str(temp_docx_file))
    assert extracted_text is not None
    
    # Temel içerik kontrolü
    assert "John Doe" in extracted_text
    assert "EĞİTİM" in extracted_text
    assert "DENEYİM" in extracted_text
    assert "BECERİLER" in extracted_text

def test_nonexistent_file(doc_processor):
    """Var olmayan dosya için hata kontrolü"""
    with pytest.raises(FileNotFoundError):
        doc_processor.extract_text("nonexistent.txt")

def test_unsupported_extension(doc_processor):
    """Desteklenmeyen dosya uzantısı için hata kontrolü"""
    with pytest.raises(ValueError):
        doc_processor.extract_text("test.xyz")

def test_text_cleaning(doc_processor):
    """Metin temizleme işlemini test eder"""
    dirty_text = """Test   User    
    test.user@email.com
    
    +90 555 987 6543
    
    Multiple    Spaces    Here
    """
    
    cleaned_text = doc_processor._clean_text(dirty_text)
    
    # Gereksiz boşluklar temizlenmeli
    assert "  " not in cleaned_text
    
    # Email adresi korunmalı
    assert "test.user@email.com" in cleaned_text
    
    # Telefon numarası korunmalı
    assert "+90 555 987 6543" in cleaned_text
    
    # Gereksiz satır sonları temizlenmeli
    assert "\n\n" not in cleaned_text 