# CV Analiz ve Eşleştirme Sistemi

![Sistem Logosu](assets/logo.png)

## 🌟 Proje Özeti

CV Analiz ve Eşleştirme Sistemi, tamamen yerel (**on-premise**) çalışan, CV'lerden otomatik bilgi çıkarımı yapan ve iş pozisyonlarıyla eşleştiren yapay zeka destekli bir araçtır. Sistem, büyük dil modelleri (LLM) kullanarak CV içindeki önemli bilgileri (eğitim, deneyim, beceriler vb.) yapılandırılmış formata dönüştürür ve iş pozisyonlarıyla eşleştirerek en uygun adayları tespit eder. Tüm işlemler kullanıcının kendi cihazında veya sunucusunda gerçekleştirilir - hiçbir veri dış servislere gönderilmez.

### 🔒 Gizlilik Odaklı Yaklaşım

Bu sistem, yaygın bulut API'lere (OpenAI, Claude, vb.) alternatif olarak geliştirilmiştir. CV analizi ve işe alım süreçlerinde kritik öneme sahip kişisel verilerin korunması için **hiçbir harici AI servisi kullanılmaz**, tüm işlemler yerel donanımda gerçekleştirilir.

---

## 📋 Özellikler

### 🧠 Akıllı CV Analizi

- **Çoklu Format Desteği**: PDF, DOCX, TXT, RTF formatlarında CV dosyalarını destekler
- **Derin Anlama**: CV içeriğini anlayarak yapılandırılmış veriye dönüştürür
- **Otomatik Bilgi Çıkarımı**:
  - Kişisel bilgiler (isim, e-posta, telefon)
  - Eğitim geçmişi (okul, bölüm, mezuniyet)
  - İş deneyimi (şirket, pozisyon, tarih aralığı, sorumluluklar)
  - Teknik ve profesyonel beceriler
  - Sertifikalar ve başarılar
  - Dil becerileri

### 🎯 Gelişmiş Eşleştirme

- **Çok Boyutlu Puanlama**: Becerileri, deneyimi, eğitimi ve diğer faktörleri değerlendiren puanlama sistemi
- **Semantik Eşleştirme**: Anahtar kelime eşleştirmesinin ötesinde CV içeriğinin anlamsal olarak pozisyonla uyumunu değerlendirir
- **Ağırlıklı Kriterler**: Pozisyona göre farklı kriterlere farklı ağırlıklar verebilme
- **Pozisyon Profilleri**: Tekrar kullanılabilir pozisyon tanımları ve gereksinimleri
- **Adayları Sıralama**: En uygun adayları puanlarına göre listeleme ve filtreleme

### 🛠️ Teknik Altyapı

- **Yerel LLM Entegrasyonu**: DeepSeek model ailesi ile tam yerel çalışma
- **Çoklu Platform Desteği**: MacOS (Apple Silicon) ve Windows (CUDA GPU) için optimize edilmiş
- **Otomatik Platform Tespiti**: İşletim sistemi ve donanıma göre uygun modeli otomatik seçer
- **Donanım Hızlandırma**: Metal Performance Shaders (MPS) ve CUDA desteği
- **API Altyapısı**: Modern FastAPI tabanlı REST API
- **Ölçeklenebilir Mimari**: Birden fazla CV'yi asenkron olarak işleyebilir
- **Veritabanı Entegrasyonu**: SQLite (geliştirme) ve PostgreSQL (üretim) desteği

---

## 🖥️ Sistem Gereksinimleri

### 🍎 MacOS (Geliştirme Ortamı)
- **İşlemci**: Apple Silicon (M serisi) - M1/M2/M3 veya daha yeni
- **RAM**: Minimum 16GB, önerilen 32GB veya üzeri
- **Disk**: 10GB+ boş alan (SSD tavsiye edilir)
- **İşletim Sistemi**: macOS 12 (Monterey) veya daha yeni
- **Python**: 3.11 veya daha yeni

### 🪟 Windows (Test ve Üretim Ortamı)
- **İşlemci**: Modern x86-64 CPU (8+ çekirdek tavsiye edilir)
- **RAM**: Minimum 32GB, önerilen 64GB veya üzeri
- **GPU**: NVIDIA GPU (en az 8GB VRAM, önerilen 16GB+ VRAM)
- **Disk**: 50GB+ boş alan (SSD tavsiye edilir)
- **İşletim Sistemi**: Windows 10/11 64-bit
- **CUDA**: CUDA Toolkit 11.8 veya daha yeni
- **Python**: 3.11 veya daha yeni

### 🐧 Linux (Sunucu Ortamı - İsteğe Bağlı)
- **İşlemci**: Modern x86-64 CPU (16+ çekirdek tavsiye edilir)
- **RAM**: Minimum 64GB, önerilen 128GB veya üzeri
- **GPU**: NVIDIA GPU (önerilen 24GB+ VRAM)
- **Disk**: 100GB+ boş alan (SSD tavsiye edilir)
- **İşletim Sistemi**: Ubuntu 20.04+ veya benzer Linux dağıtımı
- **CUDA**: CUDA Toolkit 11.8 veya daha yeni
- **Python**: 3.11 veya daha yeni

---

## 🧩 Sistem Mimarisi

```
┌───────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│                       │     │                   │     │                   │
│  CV Dosya İşleme      │────▶│  LLM Analiz       │────▶│  Veri Depolama    │
│  Modülü               │     │  Motoru           │     │  Sistemi          │
│                       │     │                   │     │                   │
└───────────────────────┘     └───────────────────┘     └───────────────────┘
          ▲                             │                         │
          │                             ▼                         │
┌───────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│                       │     │                   │     │                   │
│  Web Arayüzü          │◀───▶│  API Katmanı      │◀───▶│  Pozisyon Profil  │
│                       │     │                   │     │  Yönetimi         │
│                       │     │                   │     │                   │
└───────────────────────┘     └───────────────────┘     └───────────────────┘
                                       │                         │
                                       ▼                         ▼
                              ┌───────────────────┐     ┌───────────────────┐
                              │                   │     │                   │
                              │  Eşleştirme       │◀───▶│  Raporlama        │
                              │  Motoru           │     │  Sistemi          │
                              │                   │     │                   │
                              └───────────────────┘     └───────────────────┘
```

### 📁 Ana Bileşenler

1. **CV Dosya İşleme Modülü**
   - PDF, DOCX ve diğer formatlardan metin çıkarımı
   - İçerik normalleştirme ve ön işleme
   - OCR (Optik Karakter Tanıma) entegrasyonu

2. **LLM Analiz Motoru**
   - Platform tespiti ve uygun model seçimi
   - DeepSeek model yükleme ve yapılandırma
   - CV içerik analizi ve yapılandırılmış veri çıkarımı
   - Prompt şablonları ve optimizasyonu

3. **Veri Depolama Sistemi**
   - CV veritabanı yönetimi
   - Çıkarılan verilerin güvenli saklanması
   - İndeksleme ve hızlı erişim

4. **API Katmanı**
   - FastAPI tabanlı REST API
   - Asenkron istek işleme
   - Kimlik doğrulama ve yetkilendirme
   - Belgelendirme (OpenAPI)

5. **Pozisyon Profil Yönetimi**
   - Pozisyon tanımları oluşturma ve düzenleme
   - Gereksinim ve tercih edilen becerileri belirtme
   - Pozisyon şablonları ve kategorizasyon

6. **Eşleştirme Motoru**
   - Çok boyutlu puanlama algoritması
   - Semantik benzerlik hesaplama
   - Aday sıralama ve filtreleme

7. **Web Arayüzü**
   - Modern ve kullanıcı dostu UI
   - CV yükleme ve analiz sonuçlarını görüntüleme
   - Pozisyon yönetimi ve eşleştirme sonuçları

8. **Raporlama Sistemi**
   - Aday havuzu analizi
   - Eşleştirme istatistikleri
   - İçgörü ve öneriler

---

## 📦 Teknoloji Yığını

### 🐍 Backend
- **Dil**: Python 3.11+
- **API Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **Doküman İşleme**: PyPDF2, python-docx, pytesseract
- **LLM Altyapısı**: llama-cpp-python
- **Embedding**: sentence-transformers
- **Asenkron İşleme**: asyncio, uvloop

### 🗃️ Veritabanı
- **Geliştirme**: SQLite
- **Üretim**: PostgreSQL 14+

### 🧠 AI Modelleri
- **MacOS (Geliştirme)**:
  - DeepSeek-Coder-7B (Q4_0.gguf, ~4GB)
  - MPS hızlandırma ile

- **Windows/Linux (Test/Üretim)**:
  - DeepSeek-LLM-67B (Q5_K_M.gguf, ~35GB)
  - CUDA hızlandırma ile

### 🎨 Frontend (İsteğe Bağlı)
- **Framework**: React 18+
- **UI Kit**: Tailwind CSS veya Material-UI
- **State Yönetimi**: Context API veya Redux Toolkit
- **Grafik Kütüphaneleri**: Chart.js veya D3.js

### 🛠️ DevOps & Dağıtım
- **Konteynerizasyon**: Docker
- **Orkestrasyon**: Docker Compose (küçük ölçekli) / Kubernetes (büyük ölçekli)
- **CI/CD**: GitHub Actions veya GitLab CI
- **Monitoring**: Prometheus + Grafana

---

## 💾 Kurulum

### 📋 Önkoşullar

**Tüm Platformlar İçin**:
```bash
# Git'i yükleyin (platform bazlı talimatları takip edin)
# Python 3.11+ yükleyin (platform bazlı talimatları takip edin)
```

**MacOS Özellikleri**:
```bash
# Homebrew kurulumu (yoksa)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Gerekli araçlar
brew install cmake
brew install pkg-config
```

**Windows Özellikleri**:
```bash
# CUDA Toolkit kurulumu (NVIDIA resmi sitesinden)
# Visual Studio 2019+ Build Tools kurulumu
# CMake kurulumu (https://cmake.org/download/)
```

### 🔄 Depoyu Klonlama

```bash
# Depoyu klonlayın
git clone https://github.com/kullanici/cv-analiz.git
cd cv-analiz

# Proje kök dizininde sanal ortam oluşturun
python -m venv venv

# Sanal ortamı etkinleştirin
# Windows
venv\Scripts\activate
# MacOS/Linux
source venv/bin/activate
```

### 📥 Bağımlılıkların Kurulumu

**MacOS (Apple Silicon)**:
```bash
# Temel bağımlılıkları yükleyin
pip install -r requirements/macos.txt

# Metal (MPS) destekli llama-cpp-python
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```

**Windows (CUDA)**:
```bash
# Temel bağımlılıkları yükleyin
pip install -r requirements/windows.txt

# CUDA destekli llama-cpp-python
set CMAKE_ARGS=-DLLAMA_CUBLAS=on
pip install llama-cpp-python
```

### 🧠 Model İndirme

**MacOS için Model (Küçük)**:
```bash
# models/ dizinine 7B model indirin
mkdir -p models
wget https://huggingface.co/TheBloke/deepseek-coder-7b-instruct-GGUF/resolve/main/deepseek-coder-7b-instruct.Q4_0.gguf -O models/deepseek-coder-7b.Q4_0.gguf
```

**Windows için Model (Büyük)**:
```bash
# models/ dizinine 67B model indirin (uzun sürebilir)
mkdir -p models
wget https://huggingface.co/TheBloke/deepseek-llm-67b-chat-GGUF/resolve/main/deepseek-llm-67b-chat.Q5_K_M.gguf -O models/deepseek-llm-67b.Q5_K_M.gguf
```

### ⚙️ Konfigürasyon

```bash
# Örnek konfigürasyon dosyasını kopyalayın
cp config.example.yml config.yml

# Konfigürasyon dosyasını düzenleyin
# - Veritabanı bağlantı bilgileri
# - Model yolları ve ayarları
# - API ayarları
```

### 🏃 Uygulamayı Çalıştırma

```bash
# Veritabanı şemasını oluşturun
python src/db/init_db.py

# API sunucusunu başlatın
cd src
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API şimdi `http://localhost:8000` adresinde çalışıyor olacak. Swagger belgelendirmesine `http://localhost:8000/docs` adresinden erişebilirsiniz.

---

## 🔍 Kullanım Rehberi

### 🌐 API Kullanımı

#### 1. CV Analizi

```python
import requests
import json

# CV analizi için API endpoint'i
url = "http://localhost:8000/api/v1/analyze-cv"

# CV dosyasını hazırlayın
files = {
    "cv_file": ("ornek_cv.pdf", open("ornek_cv.pdf", "rb"), "application/pdf")
}

# İstemci tarafı parametreleri (opsiyonel)
params = {
    "extraction_detail": "high",  # 'basic', 'standard', 'high'
    "language": "auto"            # veya 'en', 'tr', vs.
}

# İsteği gönderin
response = requests.post(url, files=files, params=params)

# Yanıtı işleyin
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Önemli bilgileri gösterin
    print(f"İsim: {result.get('personal_info', {}).get('name')}")
    print(f"E-posta: {result.get('personal_info', {}).get('email')}")
    print(f"Tespit edilen beceriler: {result.get('skills')}")
else:
    print(f"Hata: {response.status_code}")
    print(response.text)
```

#### 2. Pozisyon Oluşturma

```python
import requests
import json

# Pozisyon oluşturma için API endpoint'i
url = "http://localhost:8000/api/v1/positions"

# Pozisyon verilerini hazırlayın
position_data = {
    "title": "Senior Python Geliştirici",
    "department": "Yazılım Geliştirme",
    "description": "Backend sistemleri geliştirmek için deneyimli bir Python geliştiricisi arıyoruz.",
    "requirements": {
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        "min_experience_years": 3,
        "education_level": "lisans",
        "languages": ["İngilizce"]
    },
    "preferred_skills": ["AWS", "Kubernetes", "CI/CD", "Test otomasyonu"],
    "location": "İstanbul",
    "employment_type": "Tam zamanlı"
}

# İsteği gönderin
headers = {"Content-Type": "application/json"}
response = requests.post(url, data=json.dumps(position_data), headers=headers)

# Yanıtı işleyin
if response.status_code == 201:
    result = response.json()
    position_id = result.get("id")
    print(f"Pozisyon oluşturuldu, ID: {position_id}")
else:
    print(f"Hata: {response.status_code}")
    print(response.text)
```

#### 3. CV-Pozisyon Eşleştirme

```python
import requests
import json

# Eşleştirme için API endpoint'i
url = "http://localhost:8000/api/v1/match"

# Eşleştirme parametrelerini hazırlayın
match_data = {
    "cv_id": 123,              # Veritabanındaki CV ID'si
    "position_id": 456,        # Veritabanındaki pozisyon ID'si
    "weighting": {
        "skills": 0.4,         # Becerilere %40 ağırlık ver
        "experience": 0.3,     # Deneyime %30 ağırlık ver
        "education": 0.2,      # Eğitime %20 ağırlık ver
        "languages": 0.1       # Dillere %10 ağırlık ver
    }
}

# İsteği gönderin
headers = {"Content-Type": "application/json"}
response = requests.post(url, data=json.dumps(match_data), headers=headers)

# Yanıtı işleyin
if response.status_code == 200:
    result = response.json()
    print(f"Eşleştirme Skoru: {result.get('overall_score')}%")
    
    # Detaylı sonuçları göster
    for category, details in result.get("detailed_scores", {}).items():
        print(f"{category}: {details.get('score')}%")
        
    # Eşleşen ve eksik becerileri göster
    print(f"Eşleşen beceriler: {result.get('matched_skills')}")
    print(f"Eksik beceriler: {result.get('missing_skills')}")
else:
    print(f"Hata: {response.status_code}")
    print(response.text)
```

#### 4. Toplu Eşleştirme

```python
import requests
import json

# Toplu eşleştirme için API endpoint'i
url = "http://localhost:8000/api/v1/batch-match"

# Eşleştirme parametrelerini hazırlayın
batch_match_data = {
    "position_id": 456,        # Pozisyon ID'si
    "min_score": 70,           # Minimum eşleşme skoru (%)
    "max_results": 10,         # En fazla 10 sonuç getir
    "weighting": {
        "skills": 0.4,
        "experience": 0.3,
        "education": 0.2,
        "languages": 0.1
    }
}

# İsteği gönderin
headers = {"Content-Type": "application/json"}
response = requests.post(url, data=json.dumps(batch_match_data), headers=headers)

# Yanıtı işleyin
if response.status_code == 200:
    result = response.json()
    
    print(f"Toplam eşleşen CV sayısı: {len(result.get('matches', []))}")
    
    # En iyi eşleşmeleri göster
    for idx, match in enumerate(result.get("matches", []), 1):
        print(f"{idx}. {match.get('cv_info', {}).get('name')} - "
              f"Skor: {match.get('overall_score')}%")
else:
    print(f"Hata: {response.status_code}")
    print(response.text)
```

### 🖥️ Komut Satırı Arayüzü (CLI)

Sistem ayrıca basit bir komut satırı arayüzü de sağlar:

```bash
# Tek bir CV'yi analiz etme
python -m cv_analyzer.cli analyze path/to/cv.pdf

# Birden fazla CV'yi analiz etme
python -m cv_analyzer.cli analyze_batch path/to/cv_folder

# Pozisyon oluşturma (interaktif)
python -m cv_analyzer.cli create_position

# CV'yi pozisyonla eşleştirme
python -m cv_analyzer.cli match --cv_id 123 --position_id 456
```

---

## 🔧 Özelleştirme

### 📝 Prompt Şablonları

LLM'ler için kullanılan prompt şablonları `src/llm/prompts` dizininde bulunur. Bunları kendi ihtiyaçlarınıza göre düzenleyebilirsiniz.

**Örnek CV Analiz Prompt Şablonu**:

```
# src/llm/prompts/cv_analysis.txt

<|im_start|>system
Sen CV analizi konusunda uzman bir asistansın. Aşağıdaki CV metnini analiz edip JSON formatında yapılandırılmış bilgileri çıkaracaksın.

Şu bilgileri çıkarman gerekiyor:
1. Kişisel bilgiler (isim, e-posta, telefon)
2. Eğitim geçmişi (okul, bölüm, mezuniyet)
3. İş deneyimi (şirket, pozisyon, tarih aralığı, sorumluluklar)
4. Beceriler
5. Dil becerileri
6. Sertifikalar ve başarılar

Lütfen bu bilgileri aşağıdaki JSON formatında döndür:
{
  "personal_info": {
    "name": "İsim Soyisim",
    "email": "ornek@email.com",
    "phone": "telefon numarası",
    "location": "konum bilgisi"
  },
  "education": [
    {
      "institution": "Okul adı",
      "degree": "Derece türü",
      "field": "Bölüm",
      "date": "Mezuniyet tarihi"
    }
  ],
  "experience": [
    {
      "company": "Şirket adı",
      "position": "Pozisyon",
      "start_date": "Başlangıç tarihi",
      "end_date": "Bitiş tarihi",
      "responsibilities": ["Sorumluluk 1", "Sorumluluk 2"]
    }
  ],
  "skills": ["Beceri 1", "Beceri 2", "Beceri 3"],
  "languages": [
    {
      "language": "Dil adı",
      "proficiency": "Seviye"
    }
  ],
  "certificates": ["Sertifika 1", "Sertifika 2"]
}

Eğer bazı bilgiler CV'de bulunmuyorsa, ilgili alanları boş bırak veya "unknown" olarak işaretle. Tahmin yapma, sadece CV'de açıkça belirtilen bilgileri kullan.
<|im_end|>

<|im_start|>user
Aşağıdaki CV'yi analiz et:

{{CV_TEXT}}
<|im_end|>

<|im_start|>assistant
```

### ⚖️ Eşleştirme Algoritması

Eşleştirme algoritmasını `src/matching/algorithm.py` dosyasını düzenleyerek özelleştirebilirsiniz. Farklı kriterlere farklı ağırlıklar atayabilir veya tamamen yeni kriterler ekleyebilirsiniz.

**Örnek Ağırlık Yapılandırması**:

```python
# src/matching/config.py

DEFAULT_WEIGHTS = {
    "skills": {
        "weight": 0.35,
        "subcategories": {
            "required_skills": 0.7,
            "preferred_skills": 0.3
        }
    },
    "experience": {
        "weight": 0.25,
        "min_years_bonus": 0.5,  # Minimum yılı aşmanın bonus değeri
        "relevant_experience_multiplier": 1.5  # İlgili sektör deneyimi çarpanı
    },
    "education": {
        "weight": 0.20,
        "levels": {
            "doktora": 1.0,
            "yüksek lisans": 0.8,
            "lisans": 0.6,
            "önlisans": 0.4,
            "lise": 0.2
        }
    },
    "languages": {
        "weight": 0.10
    },
    "semantic_similarity": {
        "weight": 0.10  # CV ve iş tanımı arasındaki semantik benzerlik
    }
}
```

---

## 🧪 Test Etme

### 🧮 Birim Testleri

```bash
# Tüm testleri çalıştırma
pytest tests/

# Belirli bir modülün testlerini çalıştırma
pytest tests/test_cv_parser.py

# Kod kapsama raporu ile çalıştırma
pytest tests/ --cov=src
```

### 📊 Performans Testleri

```bash
# Farklı modellerin performansını karşılaştırma
python benchmarks/model_comparison.py

# API performans testi
python benchmarks/api_load_test.py
```

### 🔄 Farklı Platformlarda Test

Sistemi hem MacOS hem de Windows'ta test etmek için:

1. Her iki platformda da kurulum adımlarını takip edin
2. `config.yml` dosyasında model yollarını platformunuza göre ayarlayın (veya otomatik platforma tespitini kullanın)
3. Aynı test CV'lerini her iki platformda da çalıştırın
4. Sonuçları ve performansı karşılaştırın

---

## 🛠️ Geliştirici Rehberi

### 📂 Proje Yapısı

```
cv-analiz/
│
├── config.yml                  # Ana konfigürasyon dosyası
├── requirements/               # Platform bazlı gereksinimler
│   ├── base.txt                # Temel gereksinimler
│   ├── macos.txt               # MacOS özellikleri 
│   └── windows.txt             # Windows özellikleri
│
├── models/                     # LLM modelleri (git ile izlenmiyor)
│   ├── .gitignore              # Büyük model dosyalarını yoksayma
│   └── README.md               # Model indirme talimatları
│
├── src/                        # Kaynak kod
│   ├── api/                    # API katmanı
│   │   ├── __init__.py
│   │   ├── main.py             # Ana FastAPI uygulaması
│   │   ├── routers/            # API endpoint'leri
│   │   └── schemas.py          # Pydantic modelleri
│   │
│   ├── db/                     # Veritabanı işlemleri
│   │   ├── __init__.py
│   │   ├── base.py             # Temel DB ayarları
│   │   ├── models.py           # SQLAlchemy modelleri
│   │   └── repositories.py     # Veri erişim katmanı
│   │
│   ├── document_processing/    # Doküman işleme
│   │   ├── __init__.py
│   │   ├── parser.py           # CV ayrıştırıcı
│   │   ├── extractor.py        # Metin çıkarma
│   │   └── normalizer.py       # Metin normalleştirme
│   │
│   ├── llm/                    # LLM entegrasyonu
│   │   ├── __init__.py
│   │   ├── platform_config.py  # Platform tespiti
│   │   ├── model_manager.py    # Model yükleme ve yönetimi
│   │   ├── prompts/            # Prompt şablonları
│   │   └── processor.py        # LLM istek işleme
│   │
│   ├── matching/               # Eşleştirme motoru
│   │   ├── __init__.py
│   │   ├── algorithm.py        # Eşleştirme algoritması
│   │   ├── scoring.py          # Puanlama mantığı
│   │   └── utils.py            # Yardımcı fonksiyonlar
│   │
│   └── utils/                  # Yardımcı modüller
│       ├── __init__.py
│       ├── config.py           # Konfigürasyon yükleme
│       ├── logging.py          # Loglama
│       └── helpers.py          # Genel yardımcılar
│
├── tests/                      # Testler
│   ├── conftest.py             # Test konfigürasyonu
│   ├── test_api.py             # API testleri
│   ├── test_cv_parser.py       # CV ayrıştırıcı testleri
│   └── test_matching.py        # Eşleştirme testleri
│
├── benchmarks/                 # Performans testleri
│   ├── model_comparison.py     # Model karşılaştırma
│   └── api_load_test.py        # API yük testi
│
├── web/                        # Web arayüzü (opsiyonel)
│   ├── src/                    # React uygulama kaynakları
│   ├── public/                 # Statik dosyalar
│   └── package.json            # Bağımlılıklar
│
└── docs/                       # Dokümantasyon
    ├── installation.md         # Detaylı kurulum rehberi
    ├── api.md                  # API belgelendirmesi
    ├── prompts.md              # Prompt rehberi
    └── development.md          # Geliştirme rehberi
```

### 🔄 Git İş Akışı

```bash
# Yeni bir özellik için branch oluşturma
git checkout -b feature/yeni-ozellik

# Değişiklikleri commit etme
git add .
git commit -m "Yeni özellik: <açıklama>"

# Ana branch ile birleştirme
git checkout main
git pull
git merge feature/yeni-ozellik
git push
```

### 🧩 Yeni Özellik Ekleme

1. İlgili modülü `src/` altında oluşturun
2. Testleri `tests/` dizinine ekleyin
3. Belgelendirmeyi `docs/` içinde güncelleyin
4. Değişiklikleri commit edin ve PR oluşturun

---

## 🚀 İleri Seviye Özellikler

### 🌐 Dağıtık Çalışma (Gelecek Planı)

Büyük CV havuzları için birden fazla sunucuda paralel işleme:

```python
# Dağıtık işleme konfigürasyonu örneği
distributed_config = {
    "mode": "distributed",
    "workers": [
        {"host": "worker1.local", "port": 5000, "gpu": True},
        {"host": "worker2.local", "port": 5000, "gpu": True}
    ],
    "coordinator": {"host": "master.local", "port": 5000},
    "task_distribution": "round_robin"  # veya "load_balanced"
}
```

### 🧠 Model Geliştirme (Gelecek Planı)

CV analizi için özel fine-tuning yapılmış modeller:

```bash
# Fine-tuning için veri toplama
python tools/collect_training_data.py

# Modeli fine-tune etme
python tools/fine_tune_model.py --base_model models/deepseek-7b.Q4_0.gguf --training_data data/cv_samples.jsonl
```

### 🌍 Çoklu Dil Desteği

Sistem şu anda şu dilleri destekler:

- Türkçe (ana dil)
- İngilizce
- Almanca
- Fransızca
- İspanyolca

Yeni dil eklemek için:

1. `src/llm/prompts/{language}/` dizininde ilgili dil için prompt şablonları oluşturun
2. `src/utils/language_detector.py` dosyasında dil tespiti mantığını güncelleyin
3. Veritabanı şemasını ve API şemalarını ilgili dil için güncelleyin

---

## 📈 Performans Beklentileri

### 🍎 MacBook Pro M3 (64GB RAM)

| İşlem | Model | Ortalama Süre | Bellek Kullanımı |
|-------|-------|---------------|------------------|
| CV Analizi | DeepSeek-Coder-7B | 3-5 saniye | ~12GB RAM |
| Eşleştirme (tek CV) | - | <1 saniye | ~500MB RAM |
| Toplu Eşleştirme (100 CV) | - | 5-10 saniye | ~2GB RAM |

### 🪟 Windows (128GB RAM, NVIDIA RTX 4090)

| İşlem | Model | Ortalama Süre | Bellek Kullanımı |
|-------|-------|---------------|------------------|
| CV Analizi | DeepSeek-LLM-67B | 4-8 saniye | ~50GB RAM |
| Eşleştirme (tek CV) | - | <1 saniye | ~500MB RAM |
| Toplu Eşleştirme (100 CV) | - | 3-6 saniye | ~2GB RAM |

**Not**: Bu değerler tahminidir ve kullanılan donanıma, CV boyutuna ve karmaşıklığına göre değişebilir.

---

## 🔒 Gizlilik ve Veri Güvenliği

### 🛡️ Veri Yönetimi

- **Yerel İşleme**: Tüm CV verileri yerel olarak işlenir ve saklanır
- **Şifreleme**: İsteğe bağlı olarak veritabanı şifrelemesi yapılabilir
- **Veri Saklama**: CV'lerin sadece gerekli kısımları yapılandırılmış formatta saklanır

### 🧹 Veri Temizleme

Otomatik veya manuel veri temizleme için araçlar:

```bash
# 6 aydan eski CV verilerini temizleme
python tools/data_cleanup.py --older-than 6m

# Belirli bir müşteriye ait verileri temizleme
python tools/data_cleanup.py --customer-id 12345

# Tüm kişisel bilgileri anonimleştirme
python tools/anonymize_data.py
```

---

## 📋 Lisans ve Atıflar

Bu proje, MIT Lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

### 🧠 Model Lisansları

- **DeepSeek-Coder**: DeepSeek kullanım koşulları altında
- **DeepSeek-LLM**: DeepSeek kullanım koşulları altında

### 🙏 Teşekkürler

Bu projenin geliştirilmesinde kullanılan açık kaynak araçlar:

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Hugging Face](https://huggingface.co/)
- [Sentence Transformers](https://www.sbert.net/)

---

## 📞 Destek ve İletişim

Sorularınız veya geri bildirimleriniz için:

- GitHub Issues: [Yeni bir sorun oluşturun](https://github.com/kullanici/cv-analiz/issues/new)
- E-posta: destek@ornek.com

---

## 🛣️ Yol Haritası

### 🔜 Planlanan Geliştirmeler

- [ ] Çok dilli CV analizi iyileştirmeleri
- [ ] Şirket içi otomatik pozisyon önerisi
- [ ] Görsel CV analizi (layout analizi)
- [ ] Gelişmiş raporlama ve analitik
- [ ] Kullanıcı eğitimi için daha fazla örnek ve rehber
- [ ] Docker ve Kubernetes için kapsamlı dağıtım rehberleri

### 🔮 Gelecekteki Hedefler

- [ ] Özelleştirilmiş, domain-specific LLM modelleri
- [ ] Yarı-otomatik işe alım iş akışı entegrasyonu
- [ ] Aday-bazlı kariyer tavsiyeleri
- [ ] Trend analizi ve piyasa iç görüleri

---

*Bu döküman, 2025 itibarıyla günceldir. En son geliştirmeler için GitHub deposunu kontrol edin.*
<<<<<<< HEAD
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
=======


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

# Homebrew ile wget kurulumu
brew install wget

# Sonra wget ile indirme
wget https://huggingface.co/TheBloke/deepseek-coder-7b-instruct-GGUF/resolve/main/deepseek-coder-7b-instruct.Q4_0.gguf -O models/deepseek-coder-7b.Q4_0.gguf

# Phi-2 modeli (~1.5GB) - çok daha küçük
curl -L https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_0.gguf --output models/phi-2.Q4_0.gguf
>>>>>>> fe8fba65cec76fb8aa0f030a28447ee5ae3770dd
