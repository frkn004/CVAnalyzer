#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CVAnalyzer - CV analiz uygulaması başlatma scripti
"""

import os
import sys
import argparse

# Ana dizini ekleyelim
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Projenin kök dizini
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CV Analizci web uygulamasını başlat')
    parser.add_argument('port', nargs='?', type=int, default=8080, help='Web sunucusu portu (varsayılan: 8080)')
    args = parser.parse_args()
    
    # Ana modülü içe aktarıyoruz
    from src.web.cv_analiz_web import app
    
    # Klasörleri oluşturuyoruz
    os.makedirs(os.path.join(ROOT_DIR, 'temp_uploads'), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, 'static'), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, 'templates'), exist_ok=True)
    
    print(f"Flask web uygulaması başlatılıyor...")
    print(f"Tarayıcınızda http://localhost:{args.port} adresine gidin")
    app.run(debug=True, host='0.0.0.0', port=args.port) 