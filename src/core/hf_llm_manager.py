import requests
import json
import logging

logger = logging.getLogger(__name__)

class HFLLMManager:
    def __init__(self, api_token, model="meta-llama/Meta-Llama-3-8B-Instruct"):
        """
        Hugging Face API ile LLM yönetici sınıfı
        """
        self.api_token = api_token
        self.model = model
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
        self.headers = {"Authorization": f"Bearer {api_token}"}
        
    def load_model(self):
        """API ile çalışırken model yüklemeye gerek yok"""
        logger.info(f"Hugging Face API hazır: {self.model}")
        return True
        
    def analyze_cv(self, cv_text):
        """CV metnini Hugging Face API ile analiz eder"""
        # JSON şablonu
        json_template = '''
{
  "kisisel_bilgiler": {
    "isim": "Ad Soyad",
    "email": "ornek@email.com",
    "telefon": "555-123-4567"
  },
  "egitim": [
    {
      "okul": "Üniversite Adı",
      "bolum": "Bölüm",
      "tarih": "2020-2024"
    }
  ],
  "is_deneyimi": [
    {
      "sirket": "Şirket Adı",
      "pozisyon": "Pozisyon",
      "tarih": "2020-2022",
      "gorevler": ["Görev 1", "Görev 2"]
    }
  ],
  "beceriler": ["Beceri 1", "Beceri 2"],
  "profil_degerlendirmesi": {
    "guclu_yonler": ["Güçlü yön 1", "Güçlü yön 2"],
    "gelistirilmesi_gereken_alanlar": ["Alan 1", "Alan 2"]
  }
}
'''
        
        # Prompt oluştur (Llama formatında)
        prompt = f"""Bir CV uzmanı olarak, aşağıdaki özgeçmişi analiz et ve sonuçları JSON formatında döndür.

CV metni:
{cv_text[:8000]}

Analiz sonucunu aşağıdaki JSON formatında döndür:
```json
{json_template}
```
"""
        
        try:
            logger.info(f"CV metni uzunluğu: {len(cv_text)}, API analizi başlıyor...")
            
            # API isteği parametrelerini logla
            logger.info(f"API isteği: {self.api_url}, kullanılan model: {self.model}")
            
            # API isteği gönder
            payload = {"inputs": prompt, "parameters": {"max_new_tokens": 2000}}
            logger.info(f"API gönderiliyor, prompt uzunluğu: {len(prompt)}")
            
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=60)
                logger.info(f"API yanıt durum kodu: {response.status_code}")
            except requests.exceptions.Timeout:
                logger.error("API isteği zaman aşımına uğradı (60 saniye)")
                return {"error": "API isteği zaman aşımına uğradı", "raw_response": "Zaman aşımı hatası"}
            except requests.exceptions.ConnectionError:
                logger.error("API bağlantı hatası")
                return {"error": "API bağlantı hatası", "raw_response": "Bağlantı hatası"}
            
            if response.status_code != 200:
                error_msg = f"API hatası: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # Model hala yükleniyor mu?
                if "loading" in response.text.lower():
                    logger.info("Model hala yükleniyor, lütfen bekleyin...")
                    return {
                        "error": "Model yükleniyor. Lütfen biraz bekleyin ve tekrar deneyin.",
                        "raw_response": response.text
                    }
                
                return {"error": error_msg, "raw_response": response.text}
                
            # API yanıtını al
            try:
                result = response.json()
                logger.info(f"API yanıtı başarıyla alındı ve JSON'a dönüştürüldü")
            except json.JSONDecodeError:
                logger.error(f"API yanıtı JSON formatında değil: {response.text[:500]}")
                return {"error": "API yanıtı JSON formatında değil", "raw_response": response.text[:500]}
            
            if isinstance(result, list) and len(result) > 0:
                response_text = result[0].get("generated_text", "")
                logger.info(f"Liste formatında yanıt alındı, uzunluk: {len(response_text)}")
            else:
                response_text = str(result)
                logger.info(f"Tek değer formatında yanıt alındı, uzunluk: {len(response_text)}")
                
            logger.info(f"API yanıtı alındı, yanıt uzunluğu: {len(response_text)}")
            
            # JSON yanıtını ayıkla
            try:
                # Önce ```json ve ``` arasındaki içeriği bulmaya çalış
                if "```json" in response_text and "```" in response_text.split("```json")[1]:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                    logger.info(f"JSON kod bloğu bulundu, uzunluk: {len(json_str)}")
                else:
                    # Eğer bulunamazsa, { ve } arasındaki içeriği al
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    
                    if json_start != -1 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        logger.info(f"JSON sınırları bulundu, uzunluk: {len(json_str)}")
                    else:
                        logger.warning(f"JSON formatı bulunamadı! Yanıt: {response_text[:500]}")
                        return {"error": "JSON formatı bulunamadı", "raw_response": response_text[:500]}
            except Exception as e:
                logger.error(f"JSON ayıklama hatası: {str(e)}")
                return {"error": f"JSON ayıklama hatası: {str(e)}", "raw_response": response_text[:500]}
                    
            try:
                result_dict = json.loads(json_str)
                logger.info(f"JSON başarıyla ayrıştırıldı, alanlar: {', '.join(result_dict.keys())}")
                return result_dict
            except json.JSONDecodeError as e:
                logger.error(f"JSON ayrıştırma hatası: {e}")
                
                # JSON düzeltme denemeleri
                logger.info("JSON düzeltme denemeleri yapılıyor...")
                try:
                    # Tek tırnaklı değerleri çift tırnaklı yap
                    corrected_json = json_str.replace("'", '"')
                    # Virgül düzeltmeleri
                    corrected_json = corrected_json.replace(",\n}", "\n}")
                    corrected_json = corrected_json.replace(",\n]", "\n]")
                    
                    result_dict = json.loads(corrected_json)
                    logger.info("JSON düzeltme başarılı, veri ayrıştırıldı")
                    return result_dict
                except json.JSONDecodeError as e2:
                    logger.error(f"Düzeltilen JSON ayrıştırılamadı: {e2}")
                    return {
                        "error": f"JSON ayrıştırma hatası: {str(e2)}", 
                        "raw_response": response_text[:500]
                    }
                
        except Exception as e:
            logger.error(f"API isteği sırasında beklenmeyen hata: {str(e)}")
            import traceback
            logger.error(f"Hata ayrıntıları: {traceback.format_exc()}")
            return {"error": f"API hatası: {str(e)}", "raw_response": "API isteği sırasında hata oluştu"} 