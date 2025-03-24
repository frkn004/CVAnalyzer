#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import logging
import tempfile
import time
from flask import Flask, request, render_template, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from gelismis_cv_analiz import GelismisCVAnalizci, pdf_to_text

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cv_analiz_web')

# Flask uygulaması
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'doc', 'docx'}
app.config['MODEL_NAME'] = 'llama3:8b'  # Varsayılan model

# Klasörleri oluştur
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

def allowed_file(filename):
    """Dosya uzantısı izin verilen uzantılar arasında mı?"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_available_models():
    """Ollama API üzerinden kullanılabilir modelleri döndürür"""
    try:
        analizci = GelismisCVAnalizci()
        return analizci.available_models
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
        # Dosya içeriğini oku
        if file_path.lower().endswith('.pdf'):
            cv_text = pdf_to_text(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                cv_text = f.read()
        
        # CV analizi yap
        analizci = GelismisCVAnalizci(model_name=model_name)
        analiz_sonuc = analizci.cv_analiz_et(cv_text)
        
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
        analizci = GelismisCVAnalizci(model_name=model_name)
        pozisyon_sonuc = analizci.pozisyon_eslesme_analizi(analiz_sonuc, pozisyon)
        
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
            # Dosya içeriğini oku
            if file_path.lower().endswith('.pdf'):
                cv_text = pdf_to_text(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cv_text = f.read()
            
            # CV analizi yap
            analizci = GelismisCVAnalizci(model_name=selected_model)
            analiz_sonuc = analizci.cv_analiz_et(cv_text)
            
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

@app.route('/favicon.ico')
def favicon():
    """Favicon servis et"""
    return send_from_directory('static/images', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    # Template dizinini oluştur
    os.makedirs('templates', exist_ok=True)
    
    # HTML şablonlarını oluştur (ilk çalıştırmada)
    if not os.path.exists('templates/index.html'):
        with open('templates/index.html', 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CV Analizci</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background-color: #f8f9fa; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container { 
            max-width: 800px; 
            margin-top: 2rem;
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        h1 { 
            color: #343a40; 
            margin-bottom: 1.5rem;
        }
        .logo {
            text-align: center;
            margin-bottom: 2rem;
        }
        .logo img {
            max-width: 150px;
        }
        .upload-form {
            background-color: #f1f3f5;
            padding: 1.5rem;
            border-radius: 10px;
        }
        .footer {
            text-align: center;
            margin-top: 2rem;
            color: #6c757d;
            font-size: 0.9rem;
        }
        .features {
            margin-top: 2rem;
        }
        .feature-item {
            display: flex;
            margin-bottom: 1rem;
        }
        .feature-icon {
            margin-right: 1rem;
            font-size: 1.5rem;
            color: #007bff;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>CV Analizci</h1>
            <p class="lead">Özgeçmişinizi yapay zeka ile analiz edin</p>
        </div>
        
        <div class="upload-form">
            <form action="/upload" method="post" enctype="multipart/form-data">
                <div class="mb-3">
                    <label for="file" class="form-label">CV Dosyası Seçin (PDF, TXT)</label>
                    <input class="form-control" type="file" id="file" name="file" accept=".pdf,.txt,.doc,.docx" required>
                </div>
                
                <div class="mb-3">
                    <label for="model" class="form-label">Model Seçin</label>
                    <select class="form-select" id="model" name="model">
                        {% for model in models %}
                        <option value="{{ model }}">{{ model }}</option>
                        {% endfor %}
                    </select>
                </div>
                
                <button type="submit" class="btn btn-primary w-100">Analiz Et</button>
            </form>
        </div>
        
        <div class="features">
            <h4>Özellikler:</h4>
            <div class="feature-item">
                <div class="feature-icon">📊</div>
                <div>Detaylı CV analizi ve puanlama</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🎯</div>
                <div>Pozisyon uyumluluğu değerlendirmesi</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">💪</div>
                <div>Güçlü yönler ve geliştirilmesi gereken alanların tespiti</div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📝</div>
                <div>Detaylı proje ve deneyim analizi</div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2024 CV Analizci. Tüm hakları saklıdır.</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    if not os.path.exists('templates/sonuc.html'):
        with open('templates/sonuc.html', 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CV Analiz Sonucu</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background-color: #f8f9fa; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container { 
            max-width: 900px; 
            margin-top: 2rem;
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { 
            color: #343a40; 
        }
        .section {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #e9ecef;
        }
        .card {
            margin-bottom: 1rem;
            border: none;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }
        .progress {
            height: 25px;
        }
        .back-btn {
            margin-top: 2rem;
        }
        .badge {
            font-size: 0.85rem;
            padding: 0.5em 0.8em;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .strength-item, .weakness-item {
            margin-bottom: 0.75rem;
        }
        .position-form {
            background-color: #f1f3f5;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4 text-center">CV Analiz Sonucu</h1>
        
        <div class="position-form section">
            <h3>Pozisyon Uyumluluğu Kontrol Et</h3>
            <form action="/pozisyon_analiz" method="post">
                <div class="mb-3">
                    <label for="pozisyon" class="form-label">Pozisyon Bilgisi Girin</label>
                    <input type="text" class="form-control" id="pozisyon" name="pozisyon" 
                           placeholder="Örnek: Senior Python Developer" required>
                </div>
                <input type="hidden" name="session_id" value="{{ session_id }}">
                <input type="hidden" name="model" value="{{ model }}">
                <button type="submit" class="btn btn-primary">Pozisyon Uyumluluğunu Analiz Et</button>
            </form>
        </div>
        
        <!-- Kişisel Bilgiler -->
        <div class="section">
            <h3>📋 Kişisel Bilgiler</h3>
            <div class="card">
                <div class="card-body">
                    <p><strong>İsim:</strong> {{ analiz.kisisel_bilgiler.isim }}</p>
                    <p><strong>E-posta:</strong> {{ analiz.kisisel_bilgiler.email }}</p>
                    <p><strong>Telefon:</strong> {{ analiz.kisisel_bilgiler.telefon }}</p>
                    <p><strong>Lokasyon:</strong> {{ analiz.kisisel_bilgiler.lokasyon }}</p>
                    {% if analiz.kisisel_bilgiler.linkedin %}
                    <p><strong>LinkedIn:</strong> {{ analiz.kisisel_bilgiler.linkedin }}</p>
                    {% endif %}
                    {% if analiz.kisisel_bilgiler.web_sitesi %}
                    <p><strong>Web Sitesi:</strong> {{ analiz.kisisel_bilgiler.web_sitesi }}</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- CV Puanlama -->
        <div class="section">
            <h3>📊 CV Puanlama</h3>
            <div class="card">
                <div class="card-body">
                    <h4 class="mb-3">Toplam Puan: {{ analiz.cv_puanlama.toplam_puan }}/100</h4>
                    
                    <p><strong>Eğitim Puanı:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar" role="progressbar" 
                             style="width: {{ analiz.cv_puanlama.egitim_puani }}%;" 
                             aria-valuenow="{{ analiz.cv_puanlama.egitim_puani }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ analiz.cv_puanlama.egitim_puani }}%
                        </div>
                    </div>
                    
                    <p><strong>Deneyim Puanı:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-success" role="progressbar" 
                             style="width: {{ analiz.cv_puanlama.deneyim_puani }}%;" 
                             aria-valuenow="{{ analiz.cv_puanlama.deneyim_puani }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ analiz.cv_puanlama.deneyim_puani }}%
                        </div>
                    </div>
                    
                    <p><strong>Beceri Puanı:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-info" role="progressbar" 
                             style="width: {{ analiz.cv_puanlama.beceri_puani }}%;" 
                             aria-valuenow="{{ analiz.cv_puanlama.beceri_puani }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ analiz.cv_puanlama.beceri_puani }}%
                        </div>
                    </div>
                    
                    <p><strong>Proje Puanı:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-warning" role="progressbar" 
                             style="width: {{ analiz.cv_puanlama.proje_puani }}%;" 
                             aria-valuenow="{{ analiz.cv_puanlama.proje_puani }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ analiz.cv_puanlama.proje_puani }}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Güçlü ve Geliştirilmesi Gereken Yönler -->
        <div class="section">
            <div class="row">
                <div class="col-md-6">
                    <h3>💪 Güçlü Yönler</h3>
                    <div class="card">
                        <div class="card-body">
                            <ul class="list-unstyled">
                                {% for gucu in analiz.guclu_yonler %}
                                <li class="strength-item">✅ {{ gucu }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h3>🔍 Geliştirilmesi Gereken Yönler</h3>
                    <div class="card">
                        <div class="card-body">
                            <ul class="list-unstyled">
                                {% for zayif in analiz.gelistirilmesi_gereken_yonler %}
                                <li class="weakness-item">⚠️ {{ zayif }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Uygun Pozisyonlar -->
        <div class="section">
            <h3>🎯 Uygun Pozisyonlar</h3>
            <div class="card">
                <div class="card-body">
                    {% for pozisyon in analiz.uygun_pozisyonlar %}
                    <span class="badge bg-primary">{{ pozisyon }}</span>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- Yetenek Özeti -->
        <div class="section">
            <h3>📝 Yetenek Özeti</h3>
            <div class="card">
                <div class="card-body">
                    <p>{{ analiz.yetenek_ozeti }}</p>
                </div>
            </div>
        </div>
        
        <!-- Eğitim Bilgileri -->
        <div class="section">
            <h3>🎓 Eğitim Bilgileri</h3>
            {% for edu in analiz.egitim_bilgileri %}
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">{{ edu.okul }}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">{{ edu.bolum }}</h6>
                    <p><strong>Derece:</strong> {{ edu.derece }}</p>
                    <p><strong>Tarih:</strong> {{ edu.tarih }}</p>
                    {% if edu.notlar %}
                    <p><strong>Notlar:</strong> {{ edu.notlar }}</p>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- İş Deneyimi -->
        <div class="section">
            <h3>💼 İş Deneyimi</h3>
            {% for job in analiz.is_deneyimi %}
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">{{ job.sirket }}</h5>
                    <h6 class="card-subtitle mb-2 text-muted">{{ job.pozisyon }}</h6>
                    <p><strong>Tarih:</strong> {{ job.tarih }}</p>
                    <p><strong>Lokasyon:</strong> {{ job.lokasyon }}</p>
                    {% if job.aciklama %}
                    <p><strong>Açıklama:</strong> {{ job.aciklama }}</p>
                    {% endif %}
                    {% if job.anahtar_basarilar %}
                    <p><strong>Anahtar Başarılar:</strong></p>
                    <ul>
                        {% for basari in job.anahtar_basarilar %}
                        <li>{{ basari }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Projeler -->
        <div class="section">
            <h3>🔨 Projeler</h3>
            {% for proje in analiz.projeler %}
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">{{ proje.ad }}</h5>
                    {% if proje.tarih %}
                    <p><strong>Tarih:</strong> {{ proje.tarih }}</p>
                    {% endif %}
                    {% if proje.aciklama %}
                    <p>{{ proje.aciklama }}</p>
                    {% endif %}
                    {% if proje.teknolojiler %}
                    <p><strong>Kullanılan Teknolojiler:</strong></p>
                    <div class="mb-2">
                        {% for tech in proje.teknolojiler %}
                        <span class="badge bg-secondary">{{ tech }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}
                    {% if proje.kazanimlar %}
                    <p><strong>Kazanımlar:</strong></p>
                    <ul>
                        {% for kazanim in proje.kazanimlar %}
                        <li>{{ kazanim }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Beceriler -->
        <div class="section">
            <h3>🛠️ Beceriler</h3>
            <div class="card">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h5>Teknik Beceriler</h5>
                            <div class="mb-3">
                                {% for beceri in analiz.beceriler.teknik_beceriler %}
                                <span class="badge bg-info text-dark">{{ beceri }}</span>
                                {% endfor %}
                            </div>
                            
                            <h5>Yazılım Dilleri</h5>
                            <div class="mb-3">
                                {% for dil in analiz.beceriler.yazilim_dilleri %}
                                <span class="badge bg-success">{{ dil }}</span>
                                {% endfor %}
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <h5>Diller</h5>
                            <div class="mb-3">
                                {% for dil in analiz.beceriler.diller %}
                                <span class="badge bg-warning text-dark">{{ dil }}</span>
                                {% endfor %}
                            </div>
                            
                            <h5>Soft Beceriler</h5>
                            <div class="mb-3">
                                {% for beceri in analiz.beceriler.soft_beceriler %}
                                <span class="badge bg-secondary">{{ beceri }}</span>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="text-center back-btn">
            <a href="/" class="btn btn-secondary">Ana Sayfaya Dön</a>
            <a href="/static/analiz_sonuc_{{ session_id }}.json" class="btn btn-primary" download>Sonuçları İndir (JSON)</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    if not os.path.exists('templates/pozisyon_sonuc.html'):
        with open('templates/pozisyon_sonuc.html', 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pozisyon Uyum Analizi</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background-color: #f8f9fa; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container { 
            max-width: 900px; 
            margin-top: 2rem;
            background-color: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { 
            color: #343a40; 
        }
        .section {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #e9ecef;
        }
        .card {
            margin-bottom: 1rem;
            border: none;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }
        .progress {
            height: 25px;
        }
        .back-btn {
            margin-top: 2rem;
        }
        .badge {
            font-size: 0.85rem;
            padding: 0.5em 0.8em;
            margin-right: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .strength-item, .weakness-item {
            margin-bottom: 0.75rem;
        }
        .position-form {
            background-color: #f1f3f5;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .match-indicator {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
            text-align: center;
            font-size: 1.2rem;
            font-weight: bold;
        }
        .match-high {
            background-color: #d4edda;
            color: #155724;
        }
        .match-medium {
            background-color: #fff3cd;
            color: #856404;
        }
        .match-low {
            background-color: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4 text-center">Pozisyon Uyum Analizi</h1>
        
        <!-- Pozisyon Bilgisi -->
        <div class="section">
            <h3>🎯 Pozisyon: {{ eslesme.pozisyon }}</h3>
            
            {% if eslesme.uyumluluk_puani >= 80 %}
            <div class="match-indicator match-high">
                Mükemmel Uyum ({{ eslesme.uyumluluk_puani }}/100)
            </div>
            {% elif eslesme.uyumluluk_puani >= 60 %}
            <div class="match-indicator match-medium">
                İyi Uyum ({{ eslesme.uyumluluk_puani }}/100)
            </div>
            {% else %}
            <div class="match-indicator match-low">
                Düşük Uyum ({{ eslesme.uyumluluk_puani }}/100)
            </div>
            {% endif %}
        </div>
        
        <!-- Detaylı Puanlama -->
        <div class="section">
            <h3>📈 Detaylı Puanlama</h3>
            <div class="card">
                <div class="card-body">                    
                    <p><strong>Eğitim Uyumu:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar" role="progressbar" 
                             style="width: {{ eslesme.detayli_puanlama.egitim_uyumu }}%;" 
                             aria-valuenow="{{ eslesme.detayli_puanlama.egitim_uyumu }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ eslesme.detayli_puanlama.egitim_uyumu }}%
                        </div>
                    </div>
                    
                    <p><strong>Deneyim Uyumu:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-success" role="progressbar" 
                             style="width: {{ eslesme.detayli_puanlama.deneyim_uyumu }}%;" 
                             aria-valuenow="{{ eslesme.detayli_puanlama.deneyim_uyumu }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ eslesme.detayli_puanlama.deneyim_uyumu }}%
                        </div>
                    </div>
                    
                    <p><strong>Beceri Uyumu:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-info" role="progressbar" 
                             style="width: {{ eslesme.detayli_puanlama.beceri_uyumu }}%;" 
                             aria-valuenow="{{ eslesme.detayli_puanlama.beceri_uyumu }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ eslesme.detayli_puanlama.beceri_uyumu }}%
                        </div>
                    </div>
                    
                    <p><strong>Proje Uyumu:</strong></p>
                    <div class="progress mb-3">
                        <div class="progress-bar bg-warning" role="progressbar" 
                             style="width: {{ eslesme.detayli_puanlama.proje_uyumu }}%;" 
                             aria-valuenow="{{ eslesme.detayli_puanlama.proje_uyumu }}" 
                             aria-valuemin="0" aria-valuemax="100">
                            {{ eslesme.detayli_puanlama.proje_uyumu }}%
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Güçlü Yönler ve Eksik Beceriler -->
        <div class="section">
            <div class="row">
                <div class="col-md-6">
                    <h3>💪 Güçlü Yönler</h3>
                    <div class="card">
                        <div class="card-body">
                            <ul class="list-unstyled">
                                {% for gucu in eslesme.guclu_yonler %}
                                <li class="strength-item">✅ {{ gucu }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <h3>⚠️ Eksik Beceriler</h3>
                    <div class="card">
                        <div class="card-body">
                            <ul class="list-unstyled">
                                {% for beceri in eslesme.eksik_beceriler %}
                                <li class="weakness-item">❌ {{ beceri }}</li>
                                {% endfor %}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Tavsiyeler -->
        <div class="section">
            <h3>💡 Tavsiyeler</h3>
            <div class="card">
                <div class="card-body">
                    <ul class="list-unstyled">
                        {% for tavsiye in eslesme.tavsiyeler %}
                        <li class="mb-2">🔸 {{ tavsiye }}</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Genel Değerlendirme -->
        <div class="section">
            <h3>📝 Genel Değerlendirme</h3>
            <div class="card">
                <div class="card-body">
                    <p>{{ eslesme.genel_degerlendirme }}</p>
                </div>
            </div>
        </div>
        
        <!-- Diğer Pozisyon Analizi -->
        <div class="position-form section">
            <h3>Başka Bir Pozisyon İçin Analiz Yap</h3>
            <form action="/pozisyon_analiz" method="post">
                <div class="mb-3">
                    <label for="pozisyon" class="form-label">Pozisyon Bilgisi Girin</label>
                    <input type="text" class="form-control" id="pozisyon" name="pozisyon" 
                           placeholder="Örnek: Senior Python Developer" required>
                </div>
                <input type="hidden" name="session_id" value="{{ session_id }}">
                <input type="hidden" name="model" value="{{ model }}">
                <button type="submit" class="btn btn-primary">Pozisyon Uyumluluğunu Analiz Et</button>
            </form>
        </div>
        
        <div class="text-center back-btn">
            <a href="/" class="btn btn-secondary">Ana Sayfaya Dön</a>
            <a href="/static/pozisyon_sonuc_{{ session_id }}.json" class="btn btn-primary" download>Sonuçları İndir (JSON)</a>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>""")
    
    print("Flask web uygulaması başlatılıyor...")
    print("Tarayıcınızda http://localhost:8080 adresine gidin")
    app.run(debug=True, host='0.0.0.0', port=8080) 