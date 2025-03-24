# CV Analizci

CVAnalyzer, özgeçmişleri (CV) yapay zeka modellerini kullanarak analiz eden ve detaylı raporlar üreten bir uygulamadır. Hem komut satırı hem de web arayüzü üzerinden kullanılabilir.

## Özellikler

- **CV Analizi**: PDF ve metin formatındaki CV'leri analiz eder
- **Detaylı Raporlama**: Kişisel bilgiler, eğitim, iş deneyimi, beceriler, projeler ve daha fazlasını çıkarır
- **CV Puanlama**: CV'nin çeşitli bölümlerini puanlandırır
- **Pozisyon Eşleştirme**: CV'nin belirli bir pozisyon için uygunluğunu değerlendirir
- **Yerel LLM Kullanımı**: Ollama ile yerel LLM modellerini kullanarak veri gizliliğini korur
- **Web Arayüzü**: Kullanıcı dostu bir web arayüzü sunar

## Kurulum

### Gereksinimler

- Python 3.8 veya üzeri
- [Ollama](https://ollama.ai/) (Yerel LLM çalıştırmak için)
- Llama3 veya diğer uyumlu LLM modelleri

### Adımlar

1. Depoyu klonlayın:
   ```
   git clone https://github.com/kullanıcı-adı/CVAnalyzer.git
   cd CVAnalyzer
   ```

2. Sanal ortam oluşturun ve etkinleştirin:
   ```
python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\\Scripts\\activate  # Windows
   ```

3. Bağımlılıkları yükleyin:
   ```
   pip install -r requirements.txt
   ```

4. Ollama'yı kurun ve başlatın:
   ```
   # Ollama'nın resmi web sitesinden kurulum yapın: https://ollama.ai/
   ollama serve  # Ollama API'yi başlat
   ```

5. Gerekli modelleri indirin:
   ```
   ollama pull llama3:8b
   ```

## Kullanım

### Web Arayüzü

Web arayüzünü başlatmak için:

```
python app.py
```

Tarayıcınızda `http://localhost:8080` adresine gidin.

### Komut Satırı

Komut satırından CV analizi yapmak için:

```
python -m src.core.gelismis_cv_analiz cv_dosyası.pdf
```

Ek seçenekler:
- `-m, --model`: Kullanılacak model adı (varsayılan: llama3:8b)
- `-p, --pozisyon`: Eşleştirme yapılacak pozisyon
- `-j, --json`: Sonuçları JSON dosyası olarak kaydet
- `-o, --output`: Çıktı dosyası adı
- `-s, --simple`: Basit görünüm kullan

## Proje Yapısı

```
CVAnalyzer/
├── app.py                  # Ana başlatma scripti
├── requirements.txt        # Proje bağımlılıkları
├── src/                    # Kaynak kodlar
│   ├── api/                # API bağlantıları
│   │   └── ollama_connector.py  # Ollama API bağlantısı
│   ├── core/               # Çekirdek işlevsellik
│   │   └── gelismis_cv_analiz.py  # Ana CV analiz modülü
│   ├── utils/              # Yardımcı fonksiyonlar
│   │   └── pdf_to_text.py  # PDF'den metin çıkarma
│   └── web/                # Web uygulaması
│       └── cv_analiz_web.py  # Flask web uygulaması
├── static/                 # Statik dosyalar (CSS, JS, görüntüler)
└── templates/              # HTML şablonları
```

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.

## Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen bir pull request açın veya özellik istekleri/hata raporları için bir issue oluşturun.
