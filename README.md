# CV Analiz ve Eşleştirme Sistemi

Bu proje, CV'leri yerel LLM (Large Language Model) kullanarak analiz eden ve iş pozisyonlarıyla eşleştiren bir sistemdir. Sistem tamamen yerel çalışır ve hiçbir harici API kullanmaz.

## Özellikler

- PDF, DOCX ve TXT formatlarında CV dosyası desteği
- Tamamen yerel LLM tabanlı CV analizi
- Otomatik platform tespiti (MacOS/Windows)
- MacOS'ta MPS, Windows'ta CUDA hızlandırma desteği
- FastAPI tabanlı REST API
- Modüler ve genişletilebilir mimari

## Sistem Gereksinimleri

### MacOS
- MacBook Pro M3 veya üzeri
- En az 16GB RAM (önerilen: 32GB+)
- Python 3.11+
- MPS (Metal Performance Shaders) desteği

### Windows
- NVIDIA GPU (CUDA desteği ile)
- En az 32GB RAM (önerilen: 64GB+)
- Python 3.11+
- CUDA Toolkit 11.8+

## Kurulum

1. Depoyu klonlayın:
```bash
git clone https://github.com/kullanici/cv-analiz.git
cd cv-analiz
```

2. Python sanal ortam oluşturun ve etkinleştirin:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# MacOS
source venv/bin/activate
```

3. Gereksinimleri yükleyin:
```bash
pip install -r requirements.txt
```

4. LLM modellerini indirin:

### MacOS için:
```bash
# models/ dizinine indirin
wget https://huggingface.co/TheBloke/deepseek-coder-7B-base-GGUF/resolve/main/deepseek-coder-7b-q4_0.gguf -O models/deepseek-coder-7b-q4_0.gguf
```

### Windows için:
```bash
# models/ dizinine indirin
wget https://huggingface.co/TheBloke/deepseek-llm-67b-base-GGUF/resolve/main/deepseek-llm-67b-q5_k_m.gguf -O models/deepseek-llm-67b-q5_k_m.gguf
```

## Kullanım

1. API'yi başlatın:
```bash
cd src/api
uvicorn main:app --reload
```

2. Swagger UI'a erişin:
```
http://localhost:8000/docs
```

3. API endpoints:
- `POST /analyze-cv`: CV dosyası yükleyip analiz etme
- `POST /match-cv`: CV'yi pozisyon ile eşleştirme

## API Kullanım Örnekleri

### CV Analizi

```python
import requests

url = "http://localhost:8000/analyze-cv"
files = {"file": open("ornek_cv.pdf", "rb")}

response = requests.post(url, files=files)
print(response.json())
```

### CV-Pozisyon Eşleştirme

```python
import requests

url = "http://localhost:8000/match-cv"
files = {"file": open("ornek_cv.pdf", "rb")}
position = {
    "title": "Senior Python Developer",
    "description": "Backend geliştirici pozisyonu...",
    "requirements": ["Python", "FastAPI", "PostgreSQL"],
    "preferred_skills": ["Docker", "AWS"]
}

response = requests.post(url, files=files, json=position)
print(response.json())
```

## Geliştirme

1. Yeni özellik eklemek için:
   - İlgili modülü `src/` altında oluşturun
   - Testleri `tests/` dizinine ekleyin
   - API endpoint'i ekleyin

2. Test çalıştırma:
```bash
pytest tests/
```

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın. 