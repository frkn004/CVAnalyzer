#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import os
import sys
import time
from typing import Dict, List, Any, Optional

class OllamaModelManager:
    """Ollama model yönetim sınıfı"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Ollama API istemcisini başlatır"""
        self.base_url = base_url
        
    def get_models(self) -> List[Dict[str, Any]]:
        """Yüklü modelleri getirir"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.json().get('models', [])
        except Exception as e:
            print(f"Hata: Modeller getirilemedi - {str(e)}")
            return []
    
    def model_select_menu(self) -> Optional[str]:
        """Model seçim menüsü gösterir ve seçilen modeli döndürür"""
        models = self.get_models()
        
        if not models:
            print("Hiç model bulunamadı! Önce 'ollama pull model_adı' komutuyla model indirin.")
            return None
        
        print("\n=== OLLAMA MODEL SEÇİMİ ===")
        print("Kurulu modeller:")
        
        for i, model in enumerate(models, 1):
            model_name = model.get('name', 'Bilinmeyen model')
            model_size = model.get('size', 0) / 1024 / 1024 / 1024  # Byte -> GB
            print(f"{i}. {model_name} ({model_size:.1f} GB)")
        
        try:
            choice = int(input("\nSeçim yapın (1-{0}): ".format(len(models))))
            if 1 <= choice <= len(models):
                selected_model = models[choice-1].get('name')
                print(f"\nSeçilen model: {selected_model}")
                return selected_model
            else:
                print("Geçersiz seçim!")
                return None
        except ValueError:
            print("Lütfen bir sayı girin!")
            return None
        
    def cv_analiz_et(self, model_name: str, cv_metni: str) -> Dict[str, Any]:
        """Seçilen model ile CV analizini gerçekleştirir"""
        if not model_name or not cv_metni:
            return {"error": "Model adı veya CV metni boş olamaz"}
        
        # CV metni çok uzunsa kısalt
        if len(cv_metni) > 8000:
            print(f"CV metni çok uzun ({len(cv_metni)} karakter), kısaltılıyor...")
            cv_metni = cv_metni[:8000]
        
        print(f"\n'{model_name}' modeli ile CV analizi yapılıyor...")
        start_time = time.time()
        
        prompt = f"""
        <KONU>CV ANALİZİ</KONU>
        
        <CV>
        {cv_metni}
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
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json={
                    'model': model_name,
                    'prompt': prompt,
                    'stream': False
                },
                timeout=60  # 60 saniye timeout
            )
            
            if response.status_code != 200:
                return {
                    "error": f"API hatası: {response.status_code}",
                    "message": response.text
                }
            
            response_text = response.json().get('response', '')
            
            # İşlem süresini hesapla
            elapsed_time = time.time() - start_time
            print(f"Analiz tamamlandı! ({elapsed_time:.1f} saniye)")
            
            # JSON çıktısını ayıkla
            json_response = self._extract_json(response_text)
            
            if isinstance(json_response, dict):
                return json_response
            else:
                return {
                    "error": "JSON ayrıştırma hatası",
                    "raw_response": response_text[:500]
                }
            
        except Exception as e:
            return {
                "error": f"CV analizi hatası: {str(e)}",
                "details": str(e)
            }
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Metin içinden JSON içeriğini çıkarır ve ayrıştırır"""
        # Markdown JSON bloğunu temizle
        text = text.replace('```json', '').replace('```', '')
        
        # JSON başlangıç ve bitiş konumlarını bul
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start == -1 or json_end <= json_start:
            return {"error": "JSON yapısı bulunamadı", "raw_text": text[:300]}
        
        # JSON içeriğini çıkar
        json_content = text[json_start:json_end]
        
        try:
            # JSON ayrıştırma dene
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            # Hata durumunda JSON düzeltme girişimi
            try:
                # Tek tırnak yerine çift tırnak
                fixed_json = json_content.replace("'", '"')
                
                # Gereksiz virgülleri temizle
                fixed_json = fixed_json.replace(",}", "}")
                fixed_json = fixed_json.replace(",]", "]")
                
                return json.loads(fixed_json)
            except:
                return {
                    "error": f"JSON ayrıştırılamadı: {str(e)}",
                    "raw_json": json_content[:500]
                }


def dosyadan_cv_oku(dosya_yolu: str) -> str:
    """Dosyadan CV metnini okur"""
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Hata: CV dosyası okunamadı - {str(e)}")
        return ""


def sonuclari_goster(sonuc: Dict[str, Any]) -> None:
    """Analiz sonuçlarını güzel bir şekilde gösterir"""
    if "error" in sonuc:
        print(f"\n❌ HATA: {sonuc['error']}")
        if "raw_response" in sonuc:
            print(f"Ham yanıt: {sonuc['raw_response'][:200]}...")
        return
    
    print("\n=== CV ANALİZ SONUÇLARI ===")
    
    # Kişisel bilgiler
    print("\n📋 KİŞİSEL BİLGİLER:")
    kisisel = sonuc.get("kisisel_bilgiler", {})
    print(f"  İsim: {kisisel.get('isim', 'Bulunamadı')}")
    print(f"  E-posta: {kisisel.get('email', 'Bulunamadı')}")
    print(f"  Telefon: {kisisel.get('telefon', 'Bulunamadı')}")
    
    # Eğitim bilgileri
    print("\n🎓 EĞİTİM:")
    for i, edu in enumerate(sonuc.get("egitim", []), 1):
        print(f"  {i}. {edu.get('okul', 'Bulunamadı')}")
        print(f"     Bölüm: {edu.get('bolum', 'Bulunamadı')}")
        print(f"     Tarih: {edu.get('tarih', 'Bulunamadı')}")
    
    # Beceriler
    print("\n🛠️ BECERİLER:")
    for i, skill in enumerate(sonuc.get("beceriler", []), 1):
        print(f"  • {skill}")
    
    # İş deneyimi
    print("\n💼 İŞ DENEYİMİ:")
    for i, job in enumerate(sonuc.get("is_deneyimi", []), 1):
        print(f"  {i}. {job.get('sirket', 'Bulunamadı')}")
        print(f"     Pozisyon: {job.get('pozisyon', 'Bulunamadı')}")
        print(f"     Tarih: {job.get('tarih', 'Bulunamadı')}")


def main():
    """Ana program akışı"""
    manager = OllamaModelManager()
    
    # Komut satırı argümanları
    if len(sys.argv) > 1:
        cv_path = sys.argv[1]
    else:
        cv_path = input("CV dosyasının yolunu girin (varsayılan: cv.txt): ").strip() or "cv.txt"
    
    # CV metnini oku
    cv_text = dosyadan_cv_oku(cv_path)
    if not cv_text:
        print("CV metni okunamadı! Lütfen geçerli bir dosya yolu girin.")
        return
    
    # Model seçimini yap
    model_name = manager.model_select_menu()
    if not model_name:
        return
    
    # CV analizini yap
    sonuc = manager.cv_analiz_et(model_name, cv_text)
    
    # Sonuçları göster
    sonuclari_goster(sonuc)
    
    # Sonuçları JSON olarak kaydet (opsiyonel)
    kaydet = input("\nSonuçları JSON dosyası olarak kaydetmek istiyor musunuz? (e/h): ").lower()
    if kaydet.startswith('e'):
        dosya_adi = input("Kaydedilecek dosya adı (varsayılan: cv_analiz_sonuc.json): ").strip() or "cv_analiz_sonuc.json"
        try:
            with open(dosya_adi, 'w', encoding='utf-8') as f:
                json.dump(sonuc, f, ensure_ascii=False, indent=2)
            print(f"Sonuçlar '{dosya_adi}' dosyasına kaydedildi.")
        except Exception as e:
            print(f"Dosya kaydetme hatası: {str(e)}")


if __name__ == "__main__":
    print("CV Analyzer - Ollama API entegrasyonu")
    print("======================================")
    main() 