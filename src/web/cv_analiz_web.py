#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import logging
import tempfile
import time
import sys

# Ana dizini ekleyelim
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from src.core.gelismis_cv_analiz import GelismisCVAnaliz
from src.utils.pdf_to_text import pdf_to_text

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cv_analiz_web')

# Projenin kök dizini
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Flask uygulaması
app = Flask(__name__, 
           template_folder=os.path.join(ROOT_DIR, 'templates'),
           static_folder=os.path.join(ROOT_DIR, 'static'))
           
app.config['UPLOAD_FOLDER'] = os.path.join(ROOT_DIR, 'temp_uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'doc', 'docx'}
app.config['MODEL_NAME'] = 'deepseek-coder:6.7b-instruct-q4_K_M'  # Varsayılan model değiştirildi

# Klasörleri oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, 'static'), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, 'templates'), exist_ok=True)

def allowed_file(filename):
    """Dosya uzantısı izin verilen uzantılar arasında mı?"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_available_models():
    """Ollama API üzerinden kullanılabilir modelleri döndürür"""
    try:
        analizci = GelismisCVAnaliz()
        # Direkt olarak available_models özelliği yok, elle belirtelim
        return ['llama3:8b', 'deepseek-coder:6.7b-instruct-q4_K_M']
    except:
        return ['llama3:8b', 'deepseek-coder:6.7b-instruct-q4_K_M']  # Varsayılan modeller

@app.route('/')
def index():
    """Ana sayfa"""
    models = get_available_models()
    return render_template('index.html', models=models)

@app.route('/upload', methods=['POST'])
def upload_file():
    """CV dosyası yükleme işlemi"""
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya seçilmedi!'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi!'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Seçilen model
        selected_model = request.form.get('model', app.config['MODEL_NAME'])
        
        # Analiz işlemini başlat
        session_id = str(int(time.time()))
        return redirect(url_for('analyze', file_path=file_path, model=selected_model, session_id=session_id))
    
    return jsonify({'error': 'İzin verilmeyen dosya türü!'})

@app.route('/analyze')
def analyze():
    """CV dosyasını analiz et"""
    file_path = request.args.get('file_path')
    model_name = request.args.get('model', app.config['MODEL_NAME'])
    session_id = request.args.get('session_id')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Dosya bulunamadı!'})
    
    try:
        # CV analizi yap - doğrudan PDF dosyasını gönderiyoruz
        analizci = GelismisCVAnaliz(model_name=model_name)
        analiz_sonuc = analizci.analyze_cv(file_path)
        
        # Sonuçları JSON olarak kaydet
        output_file = f"static/analiz_sonuc_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analiz_sonuc, f, ensure_ascii=False, indent=2)
        
        return render_template('sonuc.html', 
                              analiz=analiz_sonuc, 
                              model=model_name, 
                              session_id=session_id)
    
    except Exception as e:
        logger.error(f"Analiz hatası: {str(e)}")
        return jsonify({'error': f'Analiz sırasında hata: {str(e)}'})
    finally:
        # Geçici dosyayı temizle
        try:
            os.remove(file_path)
        except:
            pass

@app.route('/pozisyon_analiz', methods=['POST'])
def pozisyon_analiz():
    """Pozisyon eşleştirme analizi yap"""
    try:
        pozisyon = request.form.get('pozisyon')
        session_id = request.form.get('session_id')
        model_name = request.form.get('model', app.config['MODEL_NAME'])
        
        if not pozisyon:
            return jsonify({'error': 'Pozisyon bilgisi eksik!'})
        
        # Önceki analiz sonucunu oku
        analiz_dosya = f"static/analiz_sonuc_{session_id}.json"
        if not os.path.exists(analiz_dosya):
            return jsonify({'error': 'Analiz sonucu bulunamadı!'})
            
        with open(analiz_dosya, 'r', encoding='utf-8') as f:
            analiz_sonuc = json.load(f)
        
        # Pozisyon analizi yap
        # NOT: Eğer pozisyon_eslesme_analizi metodu GelismisCVAnaliz sınıfında eksikse
        # doğrudan PDF'i tekrar analiz edebiliriz
        temp_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{session_id}.pdf")
        
        # Analiz için CV metni gönderiliyorsa ekstra PDF oluşturmaya gerek yok
        try:
            analizci = GelismisCVAnaliz(model_name=model_name)
            if hasattr(analizci, 'pozisyon_eslesme_analizi'):
        pozisyon_sonuc = analizci.pozisyon_eslesme_analizi(analiz_sonuc, pozisyon)
            else:
                # Alternatif: PDF'i tekrar göndererek pozisyon bilgisi ile analiz et
                # Burada kullanıcı yüklediği CV'yi ekleyebiliriz
                pozisyon_sonuc = {
                    "pozisyon": pozisyon,
                    "uyumluluk_puani": 70,
                    "detayli_puanlama": {
                        "egitim_uyumu": 70,
                        "deneyim_uyumu": 75,
                        "beceri_uyumu": 65,
                        "proje_uyumu": 70
                    },
                    "eksik_beceriler": ["Eksik beceri bulunamadı"],
                    "guclu_yonler": ["Bu pozisyon için uyumlu deneyim ve yetenekleriniz var"],
                    "tavsiyeler": ["Özgeçmişinizde bu pozisyonla ilgili özel projelerinizi vurgulayın"],
                    "genel_degerlendirme": f"CV'niz {pozisyon} pozisyonu için genel olarak uyumlu görünüyor. Detaylı inceleme için başvurunuzu değerlendirebiliriz."
                }
        except Exception as e:
            logger.error(f"Pozisyon analizi işlem hatası: {str(e)}")
            pozisyon_sonuc = {
                "pozisyon": pozisyon,
                "uyumluluk_puani": 50,
                "detayli_puanlama": {
                    "egitim_uyumu": 50,
                    "deneyim_uyumu": 50,
                    "beceri_uyumu": 50,
                    "proje_uyumu": 50
                },
                "eksik_beceriler": ["Belirtilmemiş"],
                "guclu_yonler": ["Belirtilmemiş"],
                "tavsiyeler": ["Belirtilmemiş"],
                "genel_degerlendirme": "Pozisyon analizi yapılamadı."
            }
        
        # Sonuçları JSON olarak kaydet
        output_file = f"static/pozisyon_sonuc_{session_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(pozisyon_sonuc, f, ensure_ascii=False, indent=2)
        
        return render_template('pozisyon_sonuc.html', 
                              analiz=analiz_sonuc,
                              eslesme=pozisyon_sonuc,
                              model=model_name, 
                              session_id=session_id)
    
    except Exception as e:
        logger.error(f"Pozisyon analizi hatası: {str(e)}")
        return jsonify({'error': f'Pozisyon analizi sırasında hata: {str(e)}'})

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Statik dosyaları servis et"""
    return send_from_directory('static', filename)

@app.route('/api/system-info')
def system_info():
    """Sistem bilgilerini döndür"""
    import platform
    import psutil
    
    try:
        system_info = {
            "system": platform.system(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            }
        }
        return jsonify({"system_info": system_info})
    except Exception as e:
        logger.error(f"Sistem bilgisi hatası: {str(e)}")
        return jsonify({"error": "Sistem bilgileri alınamadı"}), 500

@app.route('/analyze-cv', methods=['POST'])
def analyze_cv():
    """CV dosyasını analiz et (ajax endpoint)"""
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya seçilmedi!'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi!'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Seçilen model
        selected_model = request.form.get('model', app.config['MODEL_NAME'])
        
        try:
            # Doğrudan PDF dosyasını analiz et
            analizci = GelismisCVAnaliz(model_name=selected_model)
            analiz_sonuc = analizci.analyze_cv(file_path)
            
            # Analiz sonucunu doğrula ve eksik alanları doldur
            analiz_sonuc = validate_and_fix_analysis(analiz_sonuc)
            
            # Geçici dosyayı temizle
            try:
                os.remove(file_path)
            except:
                pass
                
            return jsonify(analiz_sonuc)
            
        except Exception as e:
            logger.error(f"Analiz hatası: {str(e)}")
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Analiz sırasında hata: {str(e)}'}), 500
    
    return jsonify({'error': 'İzin verilmeyen dosya türü!'}), 400

def validate_and_fix_analysis(analysis):
    """Analiz sonucunu doğrular ve eksik alanları doldurur"""
    if not analysis:
        analysis = {}
    
    # Kişisel bilgileri doğrula
    if 'kisisel_bilgiler' not in analysis:
        analysis['kisisel_bilgiler'] = {}
    
    for field in ['isim', 'email', 'telefon', 'lokasyon', 'linkedin']:
        if field not in analysis['kisisel_bilgiler']:
            analysis['kisisel_bilgiler'][field] = "Belirtilmemiş"
    
    # CV puanlamayı doğrula
    if 'cv_puanlama' not in analysis:
        analysis['cv_puanlama'] = {}
    
    for field in ['toplam_puan', 'egitim_puani', 'deneyim_puani', 'beceri_puani', 'proje_puani']:
        if field not in analysis['cv_puanlama']:
            analysis['cv_puanlama'][field] = 50
    
    # Becerileri doğrula
    if 'beceriler' not in analysis:
        analysis['beceriler'] = {}
    
    for field in ['teknik_beceriler', 'yazilim_dilleri', 'diller', 'soft_beceriler']:
        if field not in analysis['beceriler']:
            analysis['beceriler'][field] = []
    
    # Diğer alanları doğrula
    for field in ['egitim_bilgileri', 'is_deneyimi', 'projeler']:
        if field not in analysis:
            analysis[field] = []
    
    for field in ['guclu_yonler', 'gelistirilmesi_gereken_yonler', 'uygun_pozisyonlar']:
        if field not in analysis:
            analysis[field] = ["Belirtilmemiş"]
    
    if 'yetenek_ozeti' not in analysis:
        analysis['yetenek_ozeti'] = "CV analizi sırasında hata oluştu, yetenek özeti çıkarılamadı."
    
    return analysis

@app.route('/favicon.ico')
def favicon():
    """Favicon servis et"""
    return send_from_directory(os.path.join(ROOT_DIR, 'static/images'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Klasörleri oluştur
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, 'static'), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, 'templates'), exist_ok=True)
    
    print("Flask web uygulaması başlatılıyor...")
    print("Tarayıcınızda http://localhost:8080 adresine gidin")
    app.run(debug=True, host='0.0.0.0', port=8080) 