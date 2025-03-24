#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from io import StringIO
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

def pdf_to_text(pdf_file, output_file=None):
    """PDF dosyasını metin formatına dönüştürür"""
    output = StringIO()
    with open(pdf_file, 'rb') as fp:
        extract_text_to_fp(fp, output, laparams=LAParams())
    
    text = output.getvalue()
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Metin {output_file} dosyasına kaydedildi.")
    else:
        print(text)
    
    return text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python pdf_to_text.py <pdf_dosyası> [çıktı_dosyası]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    pdf_to_text(pdf_file, output_file) 