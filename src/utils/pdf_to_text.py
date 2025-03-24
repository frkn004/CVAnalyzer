#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import re
import os
import time
import pdfplumber
from typing import Optional, List, Dict, Any

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pdf_to_text')

class PDFToText:
    """
    PDF dosyalarını metin formatına çeviren sınıf
    """
    
    @staticmethod
    def convert_pdf_to_text(pdf_path: str) -> str:
        """
        PDF dosyasını metin formatına çevirir
        
        Args:
            pdf_path (str): PDF dosyasının yolu
            
        Returns:
            str: PDF içeriğinin metin formatı
        """
        if not os.path.exists(pdf_path):
            logger.error(f"Dosya bulunamadı: {pdf_path}")
            return ""
            
        if not pdf_path.lower().endswith('.pdf'):
            logger.error(f"Dosya PDF formatında değil: {pdf_path}")
            return ""
            
        try:
            # pdfplumber ile PDF'i işle
            text = PDFToText._extract_with_pdfplumber(pdf_path)
            
            # Metin önişleme
            text = PDFToText._preprocess_text(text)
            
            return text
        except Exception as e:
            logger.error(f"PDF işleme hatası: {str(e)}")
            return ""
    
    @staticmethod
    def _extract_with_pdfplumber(pdf_path: str) -> str:
        """
        pdfplumber kütüphanesi ile PDF metnini çıkarır
        
        Args:
            pdf_path (str): PDF dosyasının yolu
            
        Returns:
            str: Çıkarılan metin
        """
        logger.info(f"pdfplumber ile PDF işleniyor: {pdf_path}")
        text = ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=1, y_tolerance=3)
                    if page_text:
                        text += page_text + "\n\n"
            
            return text
        except Exception as e:
            logger.error(f"pdfplumber hatası: {str(e)}")
            return ""
    
    @staticmethod
    def _preprocess_text(text: str) -> str:
        """
        Çıkarılan metni temizler ve yapılandırır
        
        Args:
            text (str): İşlenecek ham metin
            
        Returns:
            str: Temizlenmiş metin
        """
        if not text:
            return ""
            
        # Gereksiz boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Çok fazla boş satırı temizle
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

def clean_text(text):
    """
    Metni temizler ve düzenler
    
    Args:
        text (str): Temizlenecek metin
        
    Returns:
        str: Temizlenmiş metin
    """
    if not text:
        return ""
    
    # Ardışık boşlukları tek boşlukla değiştir
    text = re.sub(r'\s+', ' ', text)
    
    # Gereksiz sekme karakterlerini temizle
    text = text.replace('\t', ' ')
    
    # URL'leri koru (e-posta veya web sitesi)
    url_pattern = r'https?://\S+|www\.\S+|\S+@\S+\.\S+'
    
    # Metni satırlara böl
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # İçinde URL var mı kontrol et
            urls = re.findall(url_pattern, line)
            # URL varsa, onu koru; yoksa satırı ekle
            if urls:
                cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
    
    # Temizlenmiş metni birleştir
    return '\n'.join(cleaned_lines)

def pdf_to_text(pdf_path):
    """
    PDF dosyasından metin çıkarır
    
    Args:
        pdf_path (str): PDF dosyasının yolu
    
    Returns:
        str: PDF'den çıkarılan metin
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF dosyası bulunamadı: {pdf_path}")
        raise FileNotFoundError(f"PDF dosyası bulunamadı: {pdf_path}")
    
    text = ""
    methods_tried = []
    errors = []
    
    # 1. Yöntem: textract kütüphanesi (en iyi metin çıkarma kalitesi)
    try:
        methods_tried.append("textract")
        logger.info(f"textract ile PDF metin çıkarma deneniyor: {pdf_path}")
        text = textract.process(pdf_path, method='pdfminer').decode('utf-8')
        
        # Metin başarıyla çıkarıldı mı kontrol et
        if text and len(text.strip()) > 100:  # En az 100 karakter
            logger.info("textract ile metin çıkarma başarılı")
            # Satır sonlarını düzelt, fazla boşlukları temizle
            text = re.sub(r'\s*\n\s*\n\s*', '\n\n', text)  # Çift boş satırları tek boş satır yap
            text = re.sub(r'[ \t]+', ' ', text)  # Yan yana boşlukları tek boşluk yap
            return text
    except Exception as e:
        logger.error(f"textract ile PDF metin çıkarma hatası: {str(e)}")
    
    # 2. Yöntem: PyPDF2 kütüphanesi (yaygın destek)
    try:
        import PyPDF2
        methods_tried.append("PyPDF2")
        logger.info(f"PyPDF2 ile PDF metin çıkarma deneniyor: {pdf_path}")
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            pages_text = []
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                # Sayfa metnini çıkar
                page_text = page.extract_text()
                # Boş sayfaları atla
                if page_text and len(page_text.strip()) > 0:
                    pages_text.append(page_text)
            
            if pages_text:
                # Tüm sayfaları birleştir
                text = "\n\n".join(pages_text)
                
                # Temizleme ve biçimlendirme
                text = re.sub(r'[ \t]+', ' ', text)  # Fazla boşlukları temizle
                
                # CV içeriğini paragraf yapısını koruyacak şekilde düzenle
                # Başlık satırlarını koru (büyük harflerle yazılmış satırlar genellikle başlıktır)
                text = re.sub(r'([A-Z][A-Z\s]{3,})\s*\n', r'\1\n\n', text)
                
                # Noktalama işaretleriyle biten cümlelerin ardına çift satır sonu ekle
                text = re.sub(r'([.!?])\s*\n', r'\1\n\n', text)
                
                # CV yapısını korumak için tipik başlıkları tanı ve ayrı paragraflar olarak ayır
                common_headers = ['EDUCATION', 'WORK EXPERIENCE', 'SKILLS', 'PROJECTS', 
                                  'EĞİTİM', 'İŞ DENEYİMİ', 'BECERİLER', 'PROJELER']
                
                for header in common_headers:
                    # Başlık satırlarını koru ve öncesi/sonrasına boş satır ekle
                    text = re.sub(f'([^\n])({header})([^\n])', r'\1\n\n\2\n\n\3', text, flags=re.IGNORECASE)
                
                logger.info("PyPDF2 ile metin çıkarma başarılı")
                return text
            else:
                logger.warning("PyPDF2 ile metin çıkarma başarısız - boş metin")
    except Exception as e:
        logger.error(f"PyPDF2 ile PDF metin çıkarma hatası: {str(e)}")
    
    # 3. Yöntem: pdfplumber kütüphanesi (daha iyi metin çıkarma, tablo desteği)
    try:
        methods_tried.append("pdfplumber")
        logger.info(f"pdfplumber ile PDF metin çıkarma deneniyor: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            
            for page in pdf.pages:
                # Sayfa metnini çıkar
                page_text = page.extract_text()
                # Boş sayfaları atla
                if page_text and len(page_text.strip()) > 0:
                    pages_text.append(page_text)
            
            if pages_text:
                # Tüm sayfaları birleştir
                text = "\n\n".join(pages_text)
                
                # Fazla boşlukları temizle
                text = re.sub(r'[ \t]+', ' ', text)
                
                # CV yapısını korumak için başlıkları algıla ve paragraf yapısını koruyacak şekilde düzenle
                text = re.sub(r'([A-Z][A-Z\s]{3,})\s*\n', r'\1\n\n', text)
                
                logger.info("pdfplumber ile metin çıkarma başarılı")
                return text
            else:
                logger.warning("pdfplumber ile metin çıkarma başarısız - boş metin")
    except Exception as e:
        logger.error(f"pdfplumber ile PDF metin çıkarma hatası: {str(e)}")
    
    # Tüm metotlar başarısız olduysa, PDF komut satırı araçlarını deneyelim
    try:
        if os.name == 'posix':  # Linux, Mac
            logger.info(f"pdftotext ile PDF metin çıkarma deneniyor: {pdf_path}")
            
            # Geçici metin dosyası
            import tempfile
            temp_txt = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
            temp_txt.close()
            
            # pdftotext aracını çalıştır
            import subprocess
            result = subprocess.run(['pdftotext', '-layout', pdf_path, temp_txt.name], 
                                   capture_output=True, text=True)
            
            if result.returncode == 0:
                # Metin dosyasını oku
                with open(temp_txt.name, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                
                # Geçici dosyayı sil
                os.unlink(temp_txt.name)
                
                # Temizleme ve biçimlendirme
                text = re.sub(r'[ \t]+', ' ', text)
                text = re.sub(r'\n{3,}', '\n\n', text)
                
                logger.info("pdftotext ile metin çıkarma başarılı")
                return text
            else:
                logger.warning(f"pdftotext ile metin çıkarma başarısız: {result.stderr}")
    except Exception as e:
        logger.error(f"pdftotext ile PDF metin çıkarma hatası: {str(e)}")
    
    # Hiçbir yöntem başarılı olmazsa boş metin döndür
    logger.error(f"PDF metin çıkarma tamamen başarısız: {pdf_path}")
    return "PDF metni çıkarılamadı. Dosya biçimini kontrol ediniz."

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Kullanım: python pdf_to_text.py <pdf_dosyası> [çıktı_dosyası]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    text = pdf_to_text(pdf_file)
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Metin {output_file} dosyasına kaydedildi.")
    else:
        print(text) 