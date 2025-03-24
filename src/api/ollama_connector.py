#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import requests
import logging
import time
from typing import Dict, Any, List, Optional

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ollama_connector')

class OllamaConnector:
    """
    Ollama API'ye bağlanarak yerel LLM modellerini kullanmak için connector sınıfı.
    Bu sınıf, mevcut CV Analyzer koduna entegre olabilir ve LLMManager sınıfının yerine kullanılabilir.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", default_model: Optional[str] = None):
        """
        Ollama API bağlantısını başlatır.
        
        Args:
            base_url (str): Ollama API URL'si
            default_model (str, optional): Varsayılan olarak kullanılacak model adı
        """
        self.base_url = base_url
        self.default_model = default_model
        self.available_models = []
        self._refresh_models()
        
        if not self.default_model and self.available_models:
            # En iyi modeli otomatik seç (Llama3 > DeepSeek > diğerleri)
            for model_pattern in ["llama3:8b", "deepseek", "llama", "mistral"]:
                for model in self.available_models:
                    if model_pattern in model.lower():
                        self.default_model = model
                        logger.info(f"Varsayılan model otomatik seçildi: {model}")
                        break
                if self.default_model:
                    break
            
            # Hala seçilmediyse ilk modeli kullan
            if not self.default_model and self.available_models:
                self.default_model = self.available_models[0]
                logger.info(f"İlk mevcut model varsayılan olarak seçildi: {self.default_model}")
    
    def _refresh_models(self) -> List[str]:
        """Mevcut modelleri yeniler ve döndürür"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            models_data = response.json().get('models', [])
            self.available_models = [model.get('name') for model in models_data]
            logger.info(f"Mevcut modeller: {', '.join(self.available_models)}")
            return self.available_models
        except Exception as e:
            logger.error(f"Modeller alınırken hata: {str(e)}")
            self.available_models = []
            return []
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        Tüm mevcut modelleri detaylı bilgileriyle döndürür
        
        Returns:
            List[Dict[str, Any]]: Model listesi
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.json().get('models', [])
        except Exception as e:
            logger.error(f"Modeller alınırken hata: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        """
        Ollama API'sinin çalışıp çalışmadığını kontrol eder
        
        Returns:
            bool: API çalışıyorsa True, aksi halde False
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except:
            return False
    
    def load_model(self, model_name: Optional[str] = None) -> bool:
        """
        Belirtilen modeli yükler (ön belleğe alır)
        
        Args:
            model_name (str, optional): Yüklenecek model adı, belirtilmezse varsayılan model kullanılır
            
        Returns:
            bool: Yükleme başarılıysa True, aksi halde False
        """
        model = model_name or self.default_model
        
        if not model:
            logger.error("Yüklenecek model belirtilmedi ve varsayılan model yok!")
            return False
        
        try:
            # Modeli ön belleğe almak için kısa bir mesaj gönder
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': model,
                    'prompt': 'Merhaba',
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Model başarıyla yüklendi: {model}")
                return True
            else:
                logger.error(f"Model yüklenemedi: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            return False
    
    def generate(self, prompt: str, model_name: Optional[str] = None, 
                 temperature: float = 0.2, max_tokens: int = 2000) -> str:
        """
        Verilen promptu kullanarak metin üretir.
        CV Analyzer'daki LLMManager.generate metodunun yerini alır.
        
        Args:
            prompt (str): Giriş metni
            model_name (str, optional): Kullanılacak model adı
            temperature (float): Yaratıcılık seviyesi (0-1 arası)
            max_tokens (int): Üretilecek maksimum token sayısı
            
        Returns:
            str: Üretilen metin
        """
        model = model_name or self.default_model
        
        if not model:
            logger.error("Model belirtilmedi ve varsayılan model yok!")
            return "Model bulunamadı. Lütfen Ollama'yı başlatın ve bir model yükleyin."
        
        try:
            logger.info(f"'{model}' modeli ile metin üretiliyor...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': temperature,
                    'num_predict': max_tokens,
                },
                timeout=120  # 2 dakika timeout
            )
            
            if response.status_code != 200:
                error_msg = f"API hatası: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return f"Metin üretme hatası: {error_msg}"
            
            result = response.json().get('response', '')
            
            elapsed_time = time.time() - start_time
            logger.info(f"Metin üretildi! ({len(result)} karakter, {elapsed_time:.2f} saniye)")
            
            return result
            
        except Exception as e:
            error_msg = f"Metin üretme hatası: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def analyze_cv(self, cv_text: str, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        CV metnini analiz eder.
        CV Analyzer'daki LLMManager.analyze_cv metodunun yerini alır.
        
        Args:
            cv_text (str): CV metni
            model_name (str, optional): Kullanılacak model adı
            
        Returns:
            Dict[str, Any]: Analiz sonuçları (Bilgiler, eğitim, deneyim, vb.)
        """
        model = model_name or self.default_model
        
        if not model:
            logger.error("Model belirtilmedi ve varsayılan model yok!")
            return {"error": "Model bulunamadı"}
        
        # CV metni çok uzunsa kısalt
        if len(cv_text) > 8000:
            logger.warning(f"CV metni çok uzun ({len(cv_text)} karakter), kısaltılıyor...")
            cv_text = cv_text[:8000]
        
        prompt = f"""
        <KONU>CV ANALİZİ</KONU>
        
        <CV>
        {cv_text}
        </CV>
        
        <GÖREV>
        Yukarıdaki CV'yi analiz edip aşağıdaki JSON formatında bilgileri çıkar.
        Sadece JSON döndür, başka açıklama yapma.
        </GÖREV>
        
        ```json
        {{
          "kisisel_bilgiler": {{
            "isim": "İsim",
            "email": "Email",
            "telefon": "Telefon"
          }},
          "egitim": [
            {{
              "okul": "Okul",
              "bolum": "Bölüm", 
              "tarih": "Tarih"
            }}
          ],
          "beceriler": ["Beceri1", "Beceri2"],
          "is_deneyimi": [
            {{
              "sirket": "Şirket",
              "pozisyon": "Pozisyon",
              "tarih": "Tarih"
            }}
          ]
        }}
        ```
        """
        
        try:
            logger.info(f"'{model}' modeli ile CV analizi yapılıyor...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json={
                    'model': model,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.2,  # Daha tutarlı sonuçlar için düşük sıcaklık
                    'num_predict': 4000  # Yeterince uzun yanıt için
                },
                timeout=180  # 3 dakika timeout
            )
            
            if response.status_code != 200:
                error_msg = f"API hatası: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
            
            response_text = response.json().get('response', '')
            
            # İşlem süresini hesapla
            elapsed_time = time.time() - start_time
            logger.info(f"CV analizi tamamlandı! ({elapsed_time:.2f} saniye)")
            
            # JSON çıktısını ayıkla
            return self._extract_json(response_text)
            
        except Exception as e:
            error_msg = f"CV analizi hatası: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Metin içinden JSON içeriğini çıkarır ve ayrıştırır
        
        Args:
            text (str): JSON içeren metin
            
        Returns:
            Dict[str, Any]: Ayrıştırılmış JSON verisi
        """
        # Markdown JSON bloğunu temizle
        text = text.replace('```json', '').replace('```', '')
        
        # JSON başlangıç ve bitiş konumlarını bul
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start == -1 or json_end <= json_start:
            logger.error(f"JSON yapısı bulunamadı: {text[:100]}...")
            return {"error": "JSON yapısı bulunamadı", "raw_text": text[:300]}
        
        # JSON içeriğini çıkar
        json_content = text[json_start:json_end]
        
        try:
            # JSON ayrıştırma dene
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON ayrıştırma hatası, düzeltme deneniyor: {str(e)}")
            # Hata durumunda JSON düzeltme girişimi
            try:
                # Tek tırnak yerine çift tırnak
                fixed_json = json_content.replace("'", '"')
                
                # Gereksiz virgülleri temizle
                fixed_json = fixed_json.replace(",}", "}")
                fixed_json = fixed_json.replace(",]", "]")
                
                return json.loads(fixed_json)
            except:
                logger.error(f"JSON düzeltme başarısız oldu")
                return {
                    "error": f"JSON ayrıştırılamadı",
                    "raw_json": json_content[:300]
                }


# Test için
if __name__ == "__main__":
    connector = OllamaConnector()
    
    if not connector.is_available():
        print("❌ Ollama API çalışmıyor! Lütfen 'ollama serve' komutunu çalıştırın.")
        exit(1)
    
    print("✅ Ollama API çalışıyor!")
    
    models = connector.get_models()
    if models:
        print("\nKurulu modeller:")
        for i, model in enumerate(models, 1):
            model_name = model.get('name', 'Bilinmeyen model')
            model_size = model.get('size', 0) / 1024 / 1024 / 1024  # Byte -> GB
            print(f"{i}. {model_name} ({model_size:.1f} GB)")
    else:
        print("\n❌ Hiç model bulunamadı! Önce 'ollama pull model_adı' komutuyla model indirin.")
        exit(1)
    
    # Varsayılan model bilgisi
    print(f"\nVarsayılan model: {connector.default_model or 'Seçilmedi'}")
    
    # Basit bir test
    test_prompt = "Yapay zeka nedir?"
    print(f"\nTest promtu: '{test_prompt}'")
    print("Yanıt alınıyor...")
    
    response = connector.generate(test_prompt)
    
    print("\nYanıt:")
    print(response[:500] + "..." if len(response) > 500 else response)
    
    print("\nConnector testi başarıyla tamamlandı!") 