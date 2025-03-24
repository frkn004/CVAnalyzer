#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import requests
import time
import re
import sys
import os
import argparse
from typing import Dict, List, Any, Optional, Tuple

# Dizin yapısını ekleyelim
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Yardımcı modülleri ekle
from src.utils.pdf_to_text import pdf_to_text

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('gelismis_cv_analiz')

class GelismisCVAnaliz:
    def __init__(self, model_name=None):
        """CV analizci sınıfının yapıcı metodu"""
        self._init_logger()
        
        # Kullanılabilir modelleri kontrol et
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                available_models = [model["name"] for model in response.json()["models"]]
                self.logger.info(f"Ollama API bağlantısı başarılı! Mevcut modeller: {', '.join(available_models)}")
                
                # Eğer model belirtilmemişse veya belirtilen model mevcut değilse
                if model_name is None or model_name not in available_models:
                    # Tercih sırasına göre modelleri dene
                    preferred_models = ["deepseek-coder:6.7b-instruct-q4_K_M", "llama3:8b"]
                    for model in preferred_models:
                        if model in available_models:
                            self.model_name = model
                            break
                    else:
                        # Hiçbir tercih edilen model bulunamazsa ilk mevcut modeli kullan
                        self.model_name = available_models[0] if available_models else "llama3:8b"
                else:
                    self.model_name = model_name
            else:
                self.logger.warning("Ollama API bağlantı hatası, varsayılan model kullanılıyor")
                self.model_name = "deepseek-coder:6.7b-instruct-q4_K_M" if model_name is None else model_name
        except Exception as e:
            self.logger.error(f"Ollama API bağlantı hatası: {str(e)}")
            self.model_name = "deepseek-coder:6.7b-instruct-q4_K_M" if model_name is None else model_name

        self.logger.info(f"CV analizci başlatıldı. Kullanılan model: {self.model_name}")
        self.max_retries = 2
        
    def analyze_cv(self, pdf_path, pos_data=None):
        """CV'yi analiz eder ve sonuçları döndürür"""
        try:
            # PDF metnini çıkar
            pdf_text = pdf_to_text(pdf_path)
            self.logger.info(f"PDF metin çıkarma başarılı: {len(pdf_text)} karakter")
            
            # Doğrudan CV parser'ı çalıştır
            try:
                from src.utils.cv_parser import CVParser
                self.logger.info("CV Parser kullanılıyor...")
                
                parser = CVParser(pdf_text)
                parser_result = parser.generate_cv_analysis()
                
                # Parser sonucu geçerli mi kontrol et
                if parser_result and isinstance(parser_result, dict) and len(parser_result) >= 5:
                    self.logger.info("CV Parser analizi başarılı! LLM kullanılmadan analiz tamamlandı.")
                    return parser_result
                else:
                    self.logger.warning("CV Parser analizi yetersiz, LLM analizi deneniyor...")
            except Exception as parser_err:
                self.logger.error(f"CV Parser hatası: {str(parser_err)}, LLM analizi deneniyor...")
            
            # Metni ön işle - uzunluk kontrolü yap
            processed_text = self._preprocess_cv_text(pdf_text)
            
            # LLM'e gönder
            for attempt in range(1, self.max_retries + 1):
                self.logger.info(f"'{self.model_name}' modeli ile CV analizi yapılıyor... (Deneme {attempt}/{self.max_retries})")
                
                if attempt > 1:
                    # İkinci denemede farklı bir prompt şablonu kullan
                    json_response = self._send_to_llm_simple_format(processed_text, pos_data)
                else:
                    # İlk denemede standart JSON prompt şablonu kullan
                    json_response = self._send_to_llm(processed_text, pos_data)
                
                # JSON çıktısını ayrıştır
                cv_data = self._extract_json(json_response)
                
                # Temel alanlar var mı kontrol et
                if self._is_valid_cv_data(cv_data):
                    return cv_data
                else:
                    self.logger.warning(f"CV verisi geçersiz, yeniden deneniyor (Deneme {attempt}/{self.max_retries})")
            
            # Tüm denemeler başarısız olduysa varsayılan yanıt oluştur
            return self._create_default_json_response("CV analizi başarısız oldu")
            
        except Exception as e:
            self.logger.error(f"CV analiz hatası: {str(e)}")
            return self._create_default_json_response(f"Hata: {str(e)}")
            
    def _preprocess_cv_text(self, text):
        """CV metnini ön işleme (uzun CV'leri işlemek için)"""
        # Metni temizle
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # CV çok uzunsa, önemli kısımları çıkar
        if len(text) > 12000:
            self.logger.warning(f"CV metni çok uzun ({len(text)} karakter), kısaltılıyor")
            
            # CV'yi bölümlere ayır
            sections = self._split_cv_into_sections(text)
            
            # Özet oluştur
            summary = ""
            
            # Kişisel bilgiler ve iletişim detayları (genellikle CV'nin başında)
            summary += text[:1500] + "\n\n"
            
            # Önemli bölümleri ekle
            important_sections = ["deneyim", "tecrübe", "experience", "eğitim", "education", 
                                 "beceri", "skills", "yetenek", "proje", "project"]
            
            for keyword in important_sections:
                for section_title, section_content in sections.items():
                    if keyword.lower() in section_title.lower() and section_content and len(section_content) > 50:
                        # Her önemli bölümden en fazla 1500 karakter al
                        summary += f"--- {section_title} ---\n{section_content[:1500]}\n\n"
            
            # Toplam metin maksimum 7500 karakter olsun
            if len(summary) > 7500:
                summary = summary[:7500]
                
            self.logger.info(f"CV metni {len(text)} karakterden {len(summary)} karaktere kısaltıldı")
            return summary
        
        return text
        
    def _split_cv_into_sections(self, text):
        """CV metnini bölümlere ayırır"""
        sections = {}
        
        # Muhtemel bölüm başlıkları için regex kalıpları
        section_patterns = [
            r'^(EĞİTİM|EDUCATION)[:\s]*$',
            r'^(DENEYİM|İŞ DENEYİMİ|TECRÜBE|EXPERIENCE)[:\s]*$',
            r'^(BECERİLER|YETENEKLER|SKILLS)[:\s]*$',
            r'^(PROJELER|PROJECTS)[:\s]*$',
            r'^(SERTİFİKALAR|CERTIFICATIONS)[:\s]*$',
            r'^(DİLLER|LANGUAGES)[:\s]*$',
            r'^(KİŞİSEL BİLGİLER|PERSONAL INFORMATION)[:\s]*$',
            r'^(REFERANSLAR|REFERENCES)[:\s]*$'
        ]
        
        # Metni satırlara böl
        lines = text.split('\n')
        current_section = "Giriş"
        sections[current_section] = ""
        
        for line in lines:
            # Bu satır bir bölüm başlığı mı kontrol et
            is_section_title = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    current_section = line.strip()
                    sections[current_section] = ""
                    is_section_title = True
                    break
            
            if not is_section_title:
                sections[current_section] += line + "\n"
        
        return sections
    
    def _send_to_llm(self, text, pos_data=None):
        """Metni LLM modeline gönderir ve JSON formatında yanıt alır"""
        position_context = ""
        if pos_data:
            position_context = f"""
            Aşağıdaki pozisyon için uygunluğu da değerlendir:
            Pozisyon: {pos_data}
            """
        
        # Prompt şablonu - daha güçlü JSON formatı vurgusu
        prompt = f"""
        # CV ANALİZ GÖREVİ
        
        Sen bir CV Analiz uzmanısın. Aşağıdaki CV metnini detaylı şekilde analiz edip sonuçları YALNIZCA aşağıda tanımlanan geçerli JSON formatında döndürmelisin.
        
        ## KURALLAR:
        1. JSON formatta MUTLAKA DİKKATLİ ve HATASIZ çıktı üretmelisin
        2. JSON formatına SIKICI bir şekilde bağlı kal - hiçbir açıklama ekleme, sadece JSON çıktı ver
        3. JSON formatını ASLA BOZMA - tüm süslü parantezleri ve çift tırnakları doğru kullan
        4. Tüm alanları MUTLAKA doldur, gerekirse "Belirtilmemiş" kullan
        5. JSON formatında sayısal değerler tırnak içinde OLMAMALI
        6. Kapatılmayan süslü parantez ({{}}) veya köşeli parantez ([]) OLMAMALI
        
        ## CV METNİ:
        {text}
        
        {position_context}
        
        ## İSTENEN ÇIKTI FORMATI (TAM OLARAK BU ŞABLONA UYGUN OLMALI):
        ```json
        {{
          "kisisel_bilgiler": {{
            "isim": "Kişinin tam adı",
            "email": "E-posta adresi veya Belirtilmemiş",
            "telefon": "Telefon numarası veya Belirtilmemiş",
            "lokasyon": "Şehir, Ülke veya Belirtilmemiş",
            "linkedin": "LinkedIn profil linki veya Belirtilmemiş"
          }},
          "cv_puanlama": {{
            "toplam_puan": 0-100 arası sayı,
            "egitim_puani": 0-100 arası sayı,
            "deneyim_puani": 0-100 arası sayı,
            "beceri_puani": 0-100 arası sayı,
            "proje_puani": 0-100 arası sayı
          }},
          "beceriler": {{
            "teknik_beceriler": ["Beceri 1", "Beceri 2"],
            "yazilim_dilleri": ["Dil 1", "Dil 2"],
            "diller": ["Dil 1 (Seviye)", "Dil 2 (Seviye)"],
            "soft_beceriler": ["Beceri 1", "Beceri 2"]
          }},
          "egitim_bilgileri": [
            {{
              "okul": "Üniversite/Okul adı",
              "bolum": "Bölüm",
              "derece": "Lisans/Yüksek Lisans/Doktora",
              "tarih": "2018-2022 veya benzeri tarih aralığı"
            }}
          ],
          "is_deneyimi": [
            {{
              "sirket": "Şirket adı",
              "pozisyon": "Pozisyon",
              "tarih": "2018-2022 veya benzeri tarih aralığı",
              "sorumluluklar": ["Sorumluluk 1", "Sorumluluk 2"]
            }}
          ],
          "projeler": [
            {{
              "proje_adi": "Proje adı",
              "aciklama": "Kısa açıklama",
              "kullanilan_teknolojiler": ["Teknoloji 1", "Teknoloji 2"]
            }}
          ],
          "guclu_yonler": ["Güçlü yön 1", "Güçlü yön 2"],
          "gelistirilmesi_gereken_yonler": ["Geliştirilmesi gereken yön 1", "Geliştirilmesi gereken yön 2"],
          "uygun_pozisyonlar": ["Pozisyon 1", "Pozisyon 2"],
          "yetenek_ozeti": "Kişinin yeteneklerini, deneyimlerini ve eğitimini özetleyen 3-5 cümle"
        }}
        ```
        
        ## ÖNEMLİ UYARILAR:
        - SADECE JSON formatında çıktı ver
        - JSON formatı bozuk olursa CV analizi BAŞARISIZ olacak
        - Her alan için veri bulunamazsa "Belirtilmemiş" veya boş dizi [] kullan
        
        JSON çıktını kontrol et ve eksik parantez olmadığından emin ol!
        """
        
        try:
            start_time = time.time()
            
            # LLM modeline istek gönder (Ollama API)
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,  # Daha düşük sıcaklık = daha deterministik
                    "num_predict": 4096, # Daha uzun yanıt
                    "stop": ["```"]      # JSON bloğu bitiminde dur
                }
            }
            
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                # Sadece metni al
                output = result.get("response", "")
                elapsed_time = time.time() - start_time
                self.logger.info(f"CV analizi tamamlandı - {elapsed_time:.2f} saniye")
                return output
            else:
                self.logger.error(f"LLM istek hatası: {response.status_code}")
                return f"LLM istek hatası: {response.status_code}"
        except Exception as e:
            self.logger.error(f"LLM istek hatası: {str(e)}")
            return f"LLM istek hatası: {str(e)}"
            
    def _send_to_llm_simple_format(self, text, pos_data=None):
        """Başarısız denemeden sonra daha basit formatta LLM isteği gönderir"""
        position_context = ""
        if pos_data:
            position_context = f"Pozisyon: {pos_data}"
        
        # Basitleştirilmiş prompt şablonu
        prompt = f"""
        # CV ANALİZ GÖREVİ - BASİTLEŞTİRİLMİŞ FORMAT
        
        Aşağıdaki CV metnini analiz et ve BASİT bir JSON formatında döndür. JSON sözdiziminin %100 doğru ve eksiksiz olması GEREKLİDİR.
        
        CV: {text}
        
        {position_context}
        
        Şu alanları içeren BASİT bir JSON çıktısı oluştur (tüm süslü ve köşeli parantezleri doğru kullan):
        
        ```json
        {{
          "kisisel_bilgiler": {{
            "isim": "",
            "email": "",
            "telefon": "",
            "lokasyon": ""
          }},
          "cv_puanlama": {{
            "toplam_puan": 75,
            "egitim_puani": 70,
            "deneyim_puani": 80,
            "beceri_puani": 75,
            "proje_puani": 70
          }},
          "beceriler": {{
            "teknik_beceriler": ["Beceri 1", "Beceri 2"],
            "yazilim_dilleri": ["Dil 1", "Dil 2"],
            "diller": ["Dil 1", "Dil 2"],
            "soft_beceriler": ["Beceri 1", "Beceri 2"]
          }},
          "egitim_bilgileri": [
            {{ "okul": "", "bolum": "", "derece": "", "tarih": "" }}
          ],
          "is_deneyimi": [
            {{ "sirket": "", "pozisyon": "", "tarih": "", "sorumluluklar": ["Sorumluluk 1"] }}
          ],
          "guclu_yonler": ["Yön 1", "Yön 2"],
          "gelistirilmesi_gereken_yonler": ["İyileştirme 1"],
          "uygun_pozisyonlar": ["Pozisyon 1", "Pozisyon 2"],
          "yetenek_ozeti": "Kısa özet"
        }}
        ```
        
        ÇOK ÖNEMLİ: JSON formatına SIKI şekilde bağlı kal. Tüm süslü parantezleri ve köşeli parantezleri doğru kapattığından emin ol!
        """
        
        try:
            start_time = time.time()
            
            # LLM modeline istek gönder (Ollama API) 
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Çok düşük sıcaklık
                    "num_predict": 4096,
                    "stop": ["```"]
                }
            }
            
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                output = result.get("response", "")
                elapsed_time = time.time() - start_time
                self.logger.info(f"Basit format CV analizi tamamlandı - {elapsed_time:.2f} saniye")
                return output
            else:
                self.logger.error(f"LLM istek hatası (basit format): {response.status_code}")
                return f"LLM istek hatası: {response.status_code}"
        except Exception as e:
            self.logger.error(f"LLM istek hatası (basit format): {str(e)}")
            return f"LLM istek hatası: {str(e)}"
            
    def _is_valid_cv_data(self, data):
        """Analiz sonucunun geçerli olup olmadığını kontrol eder"""
        if not isinstance(data, dict):
            return False
            
        # Temel alanların varlığını kontrol et
        required_fields = ["kisisel_bilgiler", "cv_puanlama", "beceriler", "yetenek_ozeti"]
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"CV verisinde '{field}' alanı eksik")
                return False
                
        # kisisel_bilgiler ve cv_puanlama içeriğini kontrol et
        if "kisisel_bilgiler" in data and "isim" in data["kisisel_bilgiler"]:
            if data["kisisel_bilgiler"]["isim"] == "Kişinin tam adı":
                self.logger.warning("CV verisinde geçerli bir isim yok, şablon değeri kullanılmış")
                return False
                
        return True

    def _init_logger(self):
        """Logger'ı yapılandırır"""
        self.logger = logging.getLogger('GelismisCVAnaliz')
        
    def _create_default_json_response(self, error_msg: str, raw_text: str = "") -> Dict[str, Any]:
        """
        Hata durumunda varsayılan bir JSON yanıtı oluşturur
        
        Args:
            error_msg (str): Hata mesajı
            raw_text (str, optional): Ham metin. Defaults to "".
            
        Returns:
            Dict[str, Any]: Varsayılan JSON yanıtı
        """
        self.logger.warning(f"Varsayılan JSON yanıtı oluşturuluyor: {error_msg}")
        
        return {
            "kisisel_bilgiler": {
                "isim": "CV'den isim çıkarılamadı",
                "email": "Belirtilmemiş",
                "telefon": "Belirtilmemiş",
                "lokasyon": "Belirtilmemiş",
                "linkedin": "Belirtilmemiş"
            },
            "egitim_bilgileri": [],
            "is_deneyimi": [],
            "projeler": [],
            "beceriler": {
                "teknik_beceriler": [],
                "yazilim_dilleri": [],
                "diller": [],
                "soft_beceriler": []
            },
            "cv_puanlama": {
                "toplam_puan": 50,
                "egitim_puani": 50,
                "deneyim_puani": 50,
                "beceri_puani": 50,
                "proje_puani": 50
            },
            "guclu_yonler": ["Bilgi yetersiz"],
            "gelistirilmesi_gereken_yonler": ["Bilgi yetersiz"],
            "uygun_pozisyonlar": ["Belirtilmemiş"],
            "yetenek_ozeti": f"CV analizi sırasında hata oluştu, yetenek özeti çıkarılamadı.",
            "_error": error_msg,
            "_raw_text": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
        }

def cv_analiz_sonucu_goster(analiz: Dict[str, Any], detayli_mi: bool = True) -> None:
    """
    CV analiz sonuçlarını terminalde gösterir
    
    Args:
        analiz (Dict[str, Any]): Analiz sonuçları
        detayli_mi (bool): Detaylı gösterim yapılsın mı
    """
    print("\n" + "="*70)
    print("                      CV ANALİZ SONUÇLARI")
    print("="*70)
    
    # Kişisel bilgiler
    print("\n📋 KİŞİSEL BİLGİLER:")
    kisisel = analiz.get("kisisel_bilgiler", {})
    print(f"  İsim: {kisisel.get('isim', 'Belirtilmemiş')}")
    print(f"  E-posta: {kisisel.get('email', 'Belirtilmemiş')}")
    print(f"  Telefon: {kisisel.get('telefon', 'Belirtilmemiş')}")
    print(f"  Lokasyon: {kisisel.get('lokasyon', 'Belirtilmemiş')}")
    
    if kisisel.get("linkedin"):
        print(f"  LinkedIn: {kisisel.get('linkedin')}")
    
    # Eğitim bilgileri
    print("\n🎓 EĞİTİM BİLGİLERİ:")
    for i, edu in enumerate(analiz.get("egitim_bilgileri", []), 1):
        print(f"  {i}. {edu.get('okul', 'Belirtilmemiş')}")
        print(f"     Bölüm: {edu.get('bolum', 'Belirtilmemiş')}")
        print(f"     Derece: {edu.get('derece', 'Belirtilmemiş')}")
        print(f"     Tarih: {edu.get('tarih', 'Belirtilmemiş')}")
        if edu.get("notlar"):
            print(f"     Notlar: {edu.get('notlar')}")
        print()
    
    # İş deneyimi
    print("\n💼 İŞ DENEYİMİ:")
    for i, job in enumerate(analiz.get("is_deneyimi", []), 1):
        print(f"  {i}. {job.get('sirket', 'Belirtilmemiş')} - {job.get('pozisyon', 'Belirtilmemiş')}")
        print(f"     Tarih: {job.get('tarih', 'Belirtilmemiş')}")
        print(f"     Lokasyon: {job.get('lokasyon', 'Belirtilmemiş')}")
        
        if detayli_mi:
            if job.get("aciklama"):
                print(f"     Açıklama: {job.get('aciklama')}")
            
            if job.get("sorumluluklar"):
                print("     Sorumluluklar:")
                for sorumluluk in job.get("sorumluluklar", []):
                    print(f"       • {sorumluluk}")
        print()
    
    # Projeler
    if analiz.get("projeler") and detayli_mi:
        print("\n🔨 PROJELER:")
        for i, proje in enumerate(analiz.get("projeler", []), 1):
            print(f"  {i}. {proje.get('proje_adi', 'Belirtilmemiş')}")
            if proje.get("tarih"):
                print(f"     Tarih: {proje.get('tarih')}")
            if proje.get("aciklama"):
                print(f"     Açıklama: {proje.get('aciklama')}")
            
            if proje.get("kullanilan_teknolojiler"):
                print("     Kullanılan Teknolojiler:")
                for tech in proje.get("kullanilan_teknolojiler", []):
                    print(f"       • {tech}")
            print()
    
    # Beceriler
    print("\n🛠️ BECERİLER:")
    beceriler = analiz.get("beceriler", {})
    
    if beceriler.get("teknik_beceriler"):
        print("  Teknik Beceriler:")
        for beceri in beceriler.get("teknik_beceriler", []):
            print(f"    • {beceri}")
    
    if beceriler.get("yazilim_dilleri"):
        print("  Yazılım Dilleri:")
        for dil in beceriler.get("yazilim_dilleri", []):
            print(f"    • {dil}")
    
    if beceriler.get("diller"):
        print("  Diller:")
        for dil in beceriler.get("diller", []):
            print(f"    • {dil}")
    
    if beceriler.get("soft_beceriler") and detayli_mi:
        print("  Soft Beceriler:")
        for beceri in beceriler.get("soft_beceriler", []):
            print(f"    • {beceri}")
    
    # Liderlik ve gönüllülük
    if analiz.get("guclu_yonler") and detayli_mi:
        print("\n👥 GÜÇLÜ YÖNLER:")
        for i, org in enumerate(analiz.get("guclu_yonler", []), 1):
            print(f"  {i}. {org}")
    
    # Sertifikalar
    if analiz.get("sertifikalar"):
        print("\n📜 SERTİFİKALAR:")
        for i, sert in enumerate(analiz.get("sertifikalar", []), 1):
            print(f"  {i}. {sert.get('ad', 'Belirtilmemiş')}")
            if sert.get("kurum"):
                print(f"     Kurum: {sert.get('kurum')}")
            if sert.get("tarih"):
                print(f"     Tarih: {sert.get('tarih')}")
            print()
    
    # CV puanlama
    print("\n📊 CV PUANLAMA:")
    puanlama = analiz.get("cv_puanlama", {})
    toplam_puan = puanlama.get("toplam_puan", 0)
    print(f"  Toplam Puan: {toplam_puan}/100")
    print(f"  Eğitim Puanı: {puanlama.get('egitim_puani', 0)}/100")
    print(f"  Deneyim Puanı: {puanlama.get('deneyim_puani', 0)}/100")
    print(f"  Beceri Puanı: {puanlama.get('beceri_puani', 0)}/100")
    print(f"  Proje Puanı: {puanlama.get('proje_puani', 0)}/100")
    
    # Güçlü ve geliştirilmesi gereken yönler
    print("\n💪 GÜÇLÜ YÖNLER:")
    for gucu in analiz.get("guclu_yonler", []):
        print(f"  • {gucu}")
    
    print("\n🔍 GELİŞTİRİLMESİ GEREKEN YÖNLER:")
    for zayif in analiz.get("gelistirilmesi_gereken_yonler", []):
        print(f"  • {zayif}")
    
    # Uygun pozisyonlar
    print("\n🎯 UYGUN POZİSYONLAR:")
    for pozisyon in analiz.get("uygun_pozisyonlar", []):
        print(f"  • {pozisyon}")
    
    # Yetenek özeti
    if analiz.get("yetenek_ozeti"):
        print("\n📝 YETENEK ÖZETİ:")
        print(f"  {analiz.get('yetenek_ozeti')}")
    
    print("\n" + "="*70)

def pozisyon_eslesme_sonucu_goster(eslesme: Dict[str, Any]) -> None:
    """
    Pozisyon eşleşme analiz sonuçlarını gösterir
    
    Args:
        eslesme (Dict[str, Any]): Eşleşme analiz sonuçları
    """
    print("\n" + "="*70)
    print(f"          POZİSYON UYUM ANALİZİ: {eslesme.get('pozisyon', 'Belirtilmemiş')}")
    print("="*70)
    
    # Uyumluluk puanı
    uyum_puani = eslesme.get("uyumluluk_puani", 0)
    print(f"\n📊 UYUMLULUK PUANI: {uyum_puani}/100")
    
    if uyum_puani >= 80:
        print("  ✅ Mükemmel uyum! Bu pozisyon için çok uygun bir aday.")
    elif uyum_puani >= 60:
        print("  ✅ İyi uyum. Bu pozisyon için uygun bir aday.")
    elif uyum_puani >= 40:
        print("  ⚠️ Orta düzeyde uyum. Bazı eksiklikler var ama geliştirilebilir.")
    else:
        print("  ❌ Düşük uyum. Bu pozisyon için yeterli deneyim ve beceriye sahip değil.")
    
    # Detaylı puanlama
    print("\n📈 DETAYLI PUANLAMA:")
    detayli = eslesme.get("detayli_puanlama", {})
    print(f"  Eğitim Uyumu: {detayli.get('egitim_uyumu', 0)}/100")
    print(f"  Deneyim Uyumu: {detayli.get('deneyim_uyumu', 0)}/100")
    print(f"  Beceri Uyumu: {detayli.get('beceri_uyumu', 0)}/100")
    print(f"  Proje Uyumu: {detayli.get('proje_uyumu', 0)}/100")
    
    # Eksik beceriler
    print("\n⚠️ EKSİK BECERİLER:")
    for beceri in eslesme.get("eksik_beceriler", []):
        print(f"  • {beceri}")
    
    # Güçlü yönler
    print("\n💪 GÜÇLÜ YÖNLER:")
    for gucu in eslesme.get("guclu_yonler", []):
        print(f"  • {gucu}")
    
    # Tavsiyeler
    print("\n💡 TAVSİYELER:")
    for tavsiye in eslesme.get("tavsiyeler", []):
        print(f"  • {tavsiye}")
    
    # Genel değerlendirme
    if eslesme.get("genel_degerlendirme"):
        print("\n📝 GENEL DEĞERLENDİRME:")
        print(f"  {eslesme.get('genel_degerlendirme')}")
    
    print("\n" + "="*70)

def main():
    """Ana program akışı"""
    parser = argparse.ArgumentParser(description="Gelişmiş CV Analiz Programı")
    parser.add_argument("dosya", help="CV dosyası (TXT, PDF)")
    parser.add_argument("-m", "--model", default="llama3:8b", help="Kullanılacak model adı (varsayılan: llama3:8b)")
    parser.add_argument("-p", "--pozisyon", help="Eşleştirme yapılacak pozisyon")
    parser.add_argument("-j", "--json", action="store_true", help="Sonuçları JSON dosyası olarak kaydet")
    parser.add_argument("-o", "--output", help="Çıktı dosyası adı (varsayılan: cv_analiz_sonuc.json)")
    parser.add_argument("-s", "--simple", action="store_true", help="Basit görünüm kullan (daha az detaylı)")
    
    args = parser.parse_args()
    
    try:
        # Dosya tipini kontrol et ve metni çıkar
        dosya_adi = args.dosya
        if dosya_adi.lower().endswith('.pdf'):
            try:
                print(f"PDF dosyası '{dosya_adi}' metne dönüştürülüyor...")
                cv_text = pdf_to_text(dosya_adi)
            except Exception as e:
                print(f"PDF dönüştürme hatası: {str(e)}")
                return
        else:
            try:
                with open(dosya_adi, 'r', encoding='utf-8') as f:
                    cv_text = f.read()
            except Exception as e:
                print(f"Dosya okuma hatası: {str(e)}")
                return
        
        print(f"CV dosyası okundu: {len(cv_text)} karakter")
        
        # Analiz et
        analizci = GelismisCVAnaliz(model_name=args.model)
        print(f"CV analizi yapılıyor (model: {analizci.model_name})...")
        analiz_sonuc = analizci.analyze_cv(cv_text)
        
        # Sonuçları göster
        cv_analiz_sonucu_goster(analiz_sonuc, detayli_mi=not args.simple)
        
        # Pozisyon eşleştirme istenirse
        if args.pozisyon:
            print(f"\n'{args.pozisyon}' pozisyonu için uyum analizi yapılıyor...")
            pozisyon_eslesme = analizci.pozisyon_eslesme_analizi(analiz_sonuc, args.pozisyon)
            pozisyon_eslesme_sonucu_goster(pozisyon_eslesme)
        
        # JSON olarak kaydet
        if args.json:
            output_file = args.output if args.output else "cv_analiz_sonuc.json"
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(analiz_sonuc, f, ensure_ascii=False, indent=2)
                print(f"Analiz sonuçları '{output_file}' dosyasına kaydedildi.")
            except Exception as e:
                print(f"Dosya yazma hatası: {str(e)}")
        
    except Exception as e:
        print(f"Program hatası: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main() 