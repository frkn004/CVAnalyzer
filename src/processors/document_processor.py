import os
from typing import Optional
from PyPDF2 import PdfReader
from docx import Document
import re

class DocumentProcessor:
    def __init__(self):
        self.supported_extensions = {'.pdf', '.docx', '.txt'}
        
    def extract_text(self, file_path: str) -> Optional[str]:
        """Desteklenen dosya formatlarından metin çıkarır"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.supported_extensions:
            raise ValueError(f"Desteklenmeyen dosya formatı: {ext}")
            
        try:
            if ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif ext == '.docx':
                return self._extract_from_docx(file_path)
            else:  # .txt
                return self._extract_from_txt(file_path)
        except Exception as e:
            print(f"Metin çıkarma hatası: {str(e)}")
            return None
            
    def _extract_from_pdf(self, file_path: str) -> str:
        """PDF dosyasından metin çıkarır"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return self._clean_text(text)
        
    def _extract_from_docx(self, file_path: str) -> str:
        """DOCX dosyasından metin çıkarır"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return self._clean_text(text)
        
    def _extract_from_txt(self, file_path: str) -> str:
        """TXT dosyasından metin çıkarır"""
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return self._clean_text(text)
        
    def _clean_text(self, text: str) -> str:
        """Metni temizler ve normalleştirir"""
        # Gereksiz boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Özel karakterleri temizle
        text = re.sub(r'[^\w\s@.,-]', '', text)
        
        # Email adreslerini koru
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        
        # Telefon numaralarını koru
        phones = re.findall(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}', text)
        
        # Metin normalizasyonu
        text = text.strip()
        text = re.sub(r'\n+', '\n', text)
        
        return text 