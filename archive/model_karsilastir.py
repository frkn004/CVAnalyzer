#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import time
import requests
from typing import Dict, Any, List, Tuple
import os

class ModelKarsilastirma:
    """Model karşılaştırma aracı"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """Ollama API istemcisini başlatır"""
        self.base_url = base_url
        self.model_list = ["llama3:8b", "deepseek-coder:6.7b-instruct-q4_K_M"]
        self.sonuclar = {}
        
    def modelleri_kontrol_et(self) -> List[str]:
        """Hangi modellerin kurulu olduğunu kontrol eder"""
        mevcut_modeller = []
        
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            kurulu_modeller = [model.get('name') for model in response.json().get('models', [])]
            
            for model in self.model_list:
                if model in kurulu_modeller:
                    mevcut_modeller.append(model)
                else:
                    print(f"⚠️ {model} modeli bulunamadı!")
            
            return mevcut_modeller
        except Exception as e:
            print(f"Hata: {str(e)}")
            return []
        
    def tum_modelleri_test_et(self, cv_metni: str) -> Dict[str, Dict[str, Any]]:
        """Tüm modelleri test eder ve sonuçları döndürür"""
        mevcut_modeller = self.modelleri_kontrol_et()
        
        if not mevcut_modeller:
            print("Hiçbir model bulunamadı! Test yapılamıyor.")
            return {}
        
        print(f"🚀 {len(mevcut_modeller)} model test ediliyor...")
        
        for model in mevcut_modeller:
            print(f"\n📊 {model} testi başlıyor...")
            start_time = time.time()
            sonuc = self.cv_analiz_et(model, cv_metni)
            elapsed_time = time.time() - start_time
            
            # Sonuçları kaydet
            self.sonuclar[model] = {
                "sonuc": sonuc,
                "sure": elapsed_time,
                "kalite_puani": self._hesapla_kalite_puani(sonuc)
            }
            
            print(f"✅ {model} testi tamamlandı! Süre: {elapsed_time:.1f} sn, Kalite puanı: {self.sonuclar[model]['kalite_puani']}")
        
        return self.sonuclar
    
    def cv_analiz_et(self, model_name: str, cv_metni: str) -> Dict[str, Any]:
        """Seçilen model ile CV analizini gerçekleştirir"""
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
                timeout=180  # 3 dakika timeout
            )
            
            if response.status_code != 200:
                return {
                    "error": f"API hatası: {response.status_code}",
                    "message": response.text
                }
            
            response_text = response.json().get('response', '')
            
            # JSON çıktısını ayıkla
            return self._extract_json(response_text)
            
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
                    "raw_json": json_content[:300]
                }
    
    def _hesapla_kalite_puani(self, sonuc: Dict[str, Any]) -> float:
        """Sonuçların kalitesini değerlendirir (0-10 arası puan)"""
        puan = 0.0
        
        # Hata varsa sıfır puan
        if "error" in sonuc:
            return 0.0
        
        # Kişisel bilgileri kontrol et
        kisisel = sonuc.get("kisisel_bilgiler", {})
        if kisisel.get("isim") and "bulunamadı" not in kisisel.get("isim", "").lower():
            puan += 2.0
        if kisisel.get("email") and "@" in kisisel.get("email", ""):
            puan += 1.0
        if kisisel.get("telefon") and len(kisisel.get("telefon", "")) > 5:
            puan += 1.0
            
        # Eğitim bilgilerini kontrol et
        egitim = sonuc.get("egitim", [])
        if egitim and len(egitim) > 0:
            for edu in egitim[:2]:  # İlk 2 eğitim
                if edu.get("okul") and len(edu.get("okul", "")) > 3:
                    puan += 0.5
                if edu.get("bolum") and len(edu.get("bolum", "")) > 3:
                    puan += 0.5
            
        # Beceriler
        beceriler = sonuc.get("beceriler", [])
        if beceriler and len(beceriler) >= 3:
            puan += 2.0
        elif beceriler and len(beceriler) >= 1:
            puan += 1.0
            
        # İş deneyimi
        is_deneyimi = sonuc.get("is_deneyimi", [])
        if is_deneyimi and len(is_deneyimi) > 0:
            for job in is_deneyimi[:2]:  # İlk 2 iş
                if job.get("sirket") and len(job.get("sirket", "")) > 3:
                    puan += 0.5
                if job.get("pozisyon") and len(job.get("pozisyon", "")) > 3:
                    puan += 0.5
        
        return min(puan, 10.0)  # Maksimum 10 puan
    
    def en_iyi_modeli_bul(self) -> Tuple[str, float]:
        """Test sonuçlarına göre en iyi modeli döndürür"""
        if not self.sonuclar:
            return "Bilinmiyor", 0.0
            
        en_iyi_model = ""
        en_yuksek_puan = -1
        
        for model, data in self.sonuclar.items():
            if data["kalite_puani"] > en_yuksek_puan:
                en_yuksek_puan = data["kalite_puani"]
                en_iyi_model = model
                
        return en_iyi_model, en_yuksek_puan
    
    def sonuclari_goster(self):
        """Tüm sonuçları karşılaştırmalı olarak gösterir"""
        if not self.sonuclar:
            print("Henüz hiçbir test yapılmadı!")
            return
        
        print("\n========== MODEL KARŞILAŞTIRMA SONUÇLARI ==========")
        
        # En iyi modeli bul
        en_iyi_model, en_yuksek_puan = self.en_iyi_modeli_bul()
        
        # Her model için sonuçları göster
        for model, data in self.sonuclar.items():
            print(f"\n{'=' * 50}")
            print(f"📌 MODEL: {model}")
            print(f"⏱️ Süre: {data['sure']:.2f} saniye")
            print(f"📊 Kalite puanı: {data['kalite_puani']:.1f}/10.0")
            
            if model == en_iyi_model:
                print("🏆 EN İYİ MODEL!")
            
            sonuc = data["sonuc"]
            if "error" in sonuc:
                print(f"❌ HATA: {sonuc['error']}")
                continue
                
            # Kişisel bilgiler
            kisisel = sonuc.get("kisisel_bilgiler", {})
            print(f"\n👤 Kişisel bilgiler:")
            print(f"  İsim: {kisisel.get('isim', 'Bulunamadı')}")
            print(f"  E-posta: {kisisel.get('email', 'Bulunamadı')}")
            print(f"  Telefon: {kisisel.get('telefon', 'Bulunamadı')}")
            
            # Eğitim (ilk 2)
            print(f"\n🎓 Eğitim:")
            for i, edu in enumerate(sonuc.get("egitim", [])[:2], 1):
                print(f"  {i}. {edu.get('okul', 'Bulunamadı')}")
                print(f"     Bölüm: {edu.get('bolum', 'Bulunamadı')}")
                
            # Beceriler (ilk 5)
            print(f"\n🛠️ Beceriler:")
            for i, skill in enumerate(sonuc.get("beceriler", [])[:5], 1):
                print(f"  • {skill}")
            
            # İş deneyimi (ilk 2)
            print(f"\n💼 İş deneyimi:")
            for i, job in enumerate(sonuc.get("is_deneyimi", [])[:2], 1):
                print(f"  {i}. {job.get('sirket', 'Bulunamadı')}")
                print(f"     Pozisyon: {job.get('pozisyon', 'Bulunamadı')}")
        
        # Genel sonuç
        print(f"\n{'=' * 50}")
        print(f"🏆 EN İYİ MODEL: {en_iyi_model}")
        print(f"📊 En yüksek kalite puanı: {en_yuksek_puan:.1f}/10.0")
        
        # Hangi modelle devam edilmeli önerisi
        if en_yuksek_puan >= 8.0:
            print(f"\n✅ ÖNERİ: {en_iyi_model} modelini kullanmaya devam edebilirsiniz.")
        elif en_yuksek_puan >= 5.0:
            print(f"\n⚠️ ÖNERİ: {en_iyi_model} makul sonuçlar veriyor, fakat daha büyük/iyi bir model kullanabilirsiniz.")
        else:
            print("\n❌ ÖNERİ: Modeller yeterince iyi sonuç vermiyor. Daha büyük bir model kullanmayı deneyin.")
    
    def sonuclari_kaydet(self, dosya_adi: str = "model_karsilastirma_sonuc.json"):
        """Sonuçları JSON dosyasına kaydeder"""
        if not self.sonuclar:
            print("Kaydedilecek sonuç yok!")
            return False
            
        try:
            with open(dosya_adi, 'w', encoding='utf-8') as f:
                json.dump(self.sonuclar, f, ensure_ascii=False, indent=2, default=str)
            print(f"✅ Sonuçlar '{dosya_adi}' dosyasına kaydedildi.")
            return True
        except Exception as e:
            print(f"❌ Dosya kaydetme hatası: {str(e)}")
            return False


def dosyadan_cv_oku(dosya_yolu: str) -> str:
    """Dosyadan CV metnini okur"""
    try:
        with open(dosya_yolu, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Hata: CV dosyası okunamadı - {str(e)}")
        return ""


def main():
    """Ana program akışı"""
    print("CV Analyzer - Model Karşılaştırma Aracı")
    print("=======================================")
    
    # CV dosyasını al
    cv_dosya = input("CV dosyasının yolunu girin (varsayılan: cv_ornek.txt): ").strip() or "cv_ornek.txt"
    
    # CV metnini oku
    cv_metni = dosyadan_cv_oku(cv_dosya)
    if not cv_metni:
        print("CV metni okunamadı! İşlem iptal ediliyor.")
        return
    
    print(f"CV metni ({len(cv_metni)} karakter) başarıyla okundu.")
    
    # Karşılaştırma işlemini başlat
    karsilastirma = ModelKarsilastirma()
    karsilastirma.tum_modelleri_test_et(cv_metni)
    
    # Sonuçları göster
    karsilastirma.sonuclari_goster()
    
    # Sonuçları kaydet
    kaydet = input("\nSonuçları JSON dosyası olarak kaydetmek istiyor musunuz? (e/h): ").lower()
    if kaydet.startswith('e'):
        dosya_adi = input("Kaydedilecek dosya adı (varsayılan: model_karsilastirma_sonuc.json): ").strip() or "model_karsilastirma_sonuc.json"
        karsilastirma.sonuclari_kaydet(dosya_adi)


if __name__ == "__main__":
    main() 