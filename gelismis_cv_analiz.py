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

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('gelismis_cv_analiz')

class GelismisCVAnalizci:
    """Gelişmiş CV analizi yapan sınıf"""
    
    def __init__(self, model_name: str = "llama3:8b", base_url: str = "http://localhost:11434"):
        """
        Gelişmiş CV analiz sınıfını başlatır
        
        Args:
            model_name (str): Kullanılacak model adı
            base_url (str): Ollama API URL
        """
        self.base_url = base_url
        self.model_name = model_name
        self.available_models = []
        
        # API bağlantısını kontrol et
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                self.available_models = [model.get('name') for model in response.json().get('models', [])]
                logger.info(f"Ollama API bağlantısı başarılı! Mevcut modeller: {', '.join(self.available_models)}")
                
                # Model kontrolü
                if self.model_name not in self.available_models:
                    closest_match = next((m for m in self.available_models if self.model_name in m), None)
                    if closest_match:
                        logger.warning(f"Model '{self.model_name}' bulunamadı. Benzer model kullanılıyor: {closest_match}")
                        self.model_name = closest_match
                    elif self.available_models:
                        logger.warning(f"Model '{self.model_name}' bulunamadı. İlk model kullanılıyor: {self.available_models[0]}")
                        self.model_name = self.available_models[0]
                    else:
                        raise ValueError("Hiçbir model bulunamadı!")
            else:
                logger.error(f"Ollama API yanıt verdi ancak hata kodu döndürdü: {response.status_code}")
                raise ConnectionError(f"API bağlantı hatası: {response.status_code}")
        except Exception as e:
            logger.error(f"Ollama API'ye bağlanılamadı: {str(e)}")
            logger.error("Ollama yüklü ve çalışıyor mu? 'ollama serve' komutu çalıştırılmalı.")
            raise ConnectionError(f"Ollama API bağlantı hatası: {str(e)}")
            
        logger.info(f"CV analizci başlatıldı. Kullanılan model: {self.model_name}")
    
    def cv_analiz_et(self, cv_text: str) -> Dict[str, Any]:
        """
        CV metnini analiz eder ve detaylı bilgiler çıkarır
        
        Args:
            cv_text (str): CV metni
            
        Returns:
            Dict[str, Any]: Analiz sonuçları
        """
        if len(cv_text) > 8000:
            logger.warning(f"CV metni çok uzun ({len(cv_text)} karakter), kısaltılıyor...")
            cv_text = cv_text[:8000]
        
        prompt = f"""
        <GÖREV>
        Aşağıdaki CV'yi detaylı olarak analiz et ve belirtilen formatta yapılandırılmış bilgileri çıkar.
        
        ÖNEMLI NOT:
        - Cevabınız yalnızca JSON formatında olmalıdır, ek açıklama veya yorum içermemelidir
        - CV içerisinde bulunan tüm bilgilere dayanarak değerlendirme yap
        - İngilizce CV olsa bile açıklamaları Türkçe yap, sadece isimler ve teknik terimler orijinal kalabilir
        - Tüm alanlara uygun şekilde doldur, hiçbir alanı boş bırakma
        - Veriler gerçek bilgilere dayanmalıdır, uydurma bilgi ekleme
        - Eksik bilgi varsa, "Belirtilmemiş" olarak doldur
        </GÖREV>
        
        <CV>
        {cv_text}
        </CV>
        
        <FORMAT>
        ```json
        {{
          "kisisel_bilgiler": {{
            "isim": "Kişinin tam adı",
            "email": "Email adresi",
            "telefon": "Telefon numarası",
            "lokasyon": "Konum bilgisi",
            "linkedin": "LinkedIn bağlantısı varsa",
            "web_sitesi": "Kişisel web sitesi varsa"
          }},
          "egitim_bilgileri": [
            {{
              "okul": "Okul adı",
              "bolum": "Bölüm",
              "derece": "Lisans/Yüksek Lisans/Doktora",
              "tarih": "Eğitim dönemi",
              "notlar": "GPA veya notlar belirtilmişse"
            }}
          ],
          "is_deneyimi": [
            {{
              "sirket": "Şirket adı",
              "pozisyon": "Pozisyon",
              "tarih": "Çalışma dönemi",
              "lokasyon": "Çalışma yeri",
              "aciklama": "Pozisyondaki görevlerin özeti",
              "anahtar_basarilar": ["Başarı 1", "Başarı 2"]
            }}
          ],
          "projeler": [
            {{
              "ad": "Proje adı",
              "tarih": "Proje dönemi",
              "aciklama": "Proje açıklaması",
              "teknolojiler": ["Teknoloji 1", "Teknoloji 2"],
              "kazanimlar": ["Kazanım 1", "Kazanım 2"]
            }}
          ],
          "beceriler": {{
            "teknik_beceriler": ["Beceri 1", "Beceri 2"],
            "yazilim_dilleri": ["Dil 1", "Dil 2"],
            "diller": ["Dil ve seviye"],
            "soft_beceriler": ["Beceri 1", "Beceri 2"]
          }},
          "liderlik_ve_gönüllülük": [
            {{
              "organizasyon": "Organizasyon adı",
              "pozisyon": "Pozisyon",
              "tarih": "Dönem",
              "açıklama": "Yapılan faaliyetler"
            }}
          ],
          "sertifikalar": [
            {{
              "ad": "Sertifika adı",
              "kurum": "Veren kurum",
              "tarih": "Alınma tarihi",
              "gecerlilik": "Geçerlilik süresi varsa"
            }}
          ],
          "cv_puanlama": {{
            "toplam_puan": 0-100 arası puan,
            "egitim_puani": 0-100 arası puan,
            "deneyim_puani": 0-100 arası puan,
            "beceri_puani": 0-100 arası puan,
            "proje_puani": 0-100 arası puan
          }},
          "guclu_yonler": [
            "Güçlü yön 1",
            "Güçlü yön 2"
          ],
          "gelistirilmesi_gereken_yonler": [
            "Geliştirilmesi gereken yön 1",
            "Geliştirilmesi gereken yön 2"
          ],
          "uygun_pozisyonlar": [
            "Pozisyon 1",
            "Pozisyon 2",
            "Pozisyon 3"
          ],
          "yetenek_ozeti": "CV sahibinin yeteneklerinin ve kariyerinin kısa özeti"
        }}
        ```
        </FORMAT>

        Yukarıdaki formatı kesinlikle takip et ve sadece JSON formatında cevap ver. JSON dışında açıklama ekleme.
        """

        try:
            logger.info(f"'{self.model_name}' modeli ile CV analizi yapılıyor...")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': self.model_name,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.3,  # Daha tutarlı sonuçlar için düşük sıcaklık
                    'num_predict': 6000  # Uzun yanıt
                },
                timeout=180  # 3 dakika timeout
            )
            
            if response.status_code != 200:
                logger.error(f"API hatası: {response.status_code} - {response.text}")
                raise Exception(f"API hatası: {response.status_code}")
            
            response_text = response.json().get('response', '')
            elapsed_time = time.time() - start_time
            logger.info(f"CV analizi tamamlandı - {elapsed_time:.2f} saniye")
            
            # JSON çıkarma
            parsed_json = self._extract_json(response_text)
            return parsed_json
            
        except Exception as e:
            logger.error(f"CV analizi sırasında hata: {str(e)}")
            raise
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """JSON içeriğini metin içinden çıkarır"""
        logger.info(f"LLM yanıtını JSON'a dönüştürüyorum (Uzunluk: {len(text)} karakter)")
        
        # Markdown JSON bloğunu temizle
        text = text.replace('```json', '').replace('```', '')
        
        # JSON başlangıç ve bitiş konumlarını bul
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start == -1 or json_end <= json_start:
            logger.error(f"JSON yapısı bulunamadı: {text[:100]}...")
            # Varsayılan değer döndür
            return self._create_default_json_response("JSON yapısı bulunamadı", raw_text=text[:300])
        
        # JSON içeriğini çıkar
        json_content = text[json_start:json_end]
        logger.info(f"JSON içeriği çıkarıldı: {len(json_content)} karakter")
        
        try:
            # JSON ayrıştırma dene
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON ayrıştırma hatası, düzeltmeye çalışılıyor: {str(e)}")
            
            # Daha kapsamlı JSON düzeltme işlemi
            try:
                # 1. Tek tırnak yerine çift tırnak
                fixed_json = json_content.replace("'", '"')
                
                # 2. Gereksiz virgülleri temizle
                fixed_json = fixed_json.replace(",}", "}")
                fixed_json = fixed_json.replace(",]", "]")
                
                # 3. Boş değerleri temizle
                fixed_json = re.sub(r':\s*null', ': ""', fixed_json)
                fixed_json = re.sub(r':\s*undefined', ': ""', fixed_json)
                
                # 4. Tırnak işaretlerini tutarlı hale getir
                fixed_json = re.sub(r'(?<!\\)"', '"', fixed_json)
                
                # 5. Fazla JSON süslemelerini temizle ve sadece ilk geçerli JSON nesnesini al
                if json_start != -1 and json_end > json_start:
                    fixed_json = fixed_json[0:json_end-json_start]
                
                # Son çare: Özel karakter ve satır sonlarını temizle
                fixed_json = re.sub(r'[\r\n\t]', ' ', fixed_json)
                
                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError:
                    # Hala olmadıysa varsayılan bir yanıt döndür
                    return self._create_default_json_response(
                        error_msg=f"JSON ayrıştırılamadı: {str(e)}",
                        raw_text=json_content[:500]
                    )
            except Exception as ex:
                logger.error(f"JSON düzeltme başarısız oldu: {str(ex)}")
                return self._create_default_json_response(
                    error_msg="JSON formatı düzeltilemedi",
                    raw_text=json_content[:300]
                )
                
    def _create_default_json_response(self, error_msg="JSON hatası", raw_text="") -> Dict[str, Any]:
        """JSON ayrıştırma başarısız olduğunda varsayılan bir yanıt oluşturur"""
        logger.warning(f"Varsayılan JSON yanıtı oluşturuluyor: {error_msg}")
        
        return {
            "kisisel_bilgiler": {
                "isim": "CV'den isim çıkarılamadı",
                "email": "email@bulunamadi.com",
                "telefon": "Belirtilmemiş",
                "lokasyon": "Belirtilmemiş",
                "linkedin": "",
                "web_sitesi": ""
            },
            "egitim_bilgileri": [
                {
                    "okul": "Belirtilmemiş",
                    "bolum": "Belirtilmemiş",
                    "derece": "Belirtilmemiş",
                    "tarih": "Belirtilmemiş",
                    "notlar": ""
                }
            ],
            "is_deneyimi": [
                {
                    "sirket": "Belirtilmemiş",
                    "pozisyon": "Belirtilmemiş",
                    "tarih": "Belirtilmemiş",
                    "lokasyon": "Belirtilmemiş",
                    "aciklama": "Belirtilmemiş",
                    "anahtar_basarilar": []
                }
            ],
            "projeler": [],
            "beceriler": {
                "teknik_beceriler": [],
                "yazilim_dilleri": [],
                "diller": [],
                "soft_beceriler": []
            },
            "liderlik_ve_gönüllülük": [],
            "sertifikalar": [],
            "cv_puanlama": {
                "toplam_puan": 0,
                "egitim_puani": 0,
                "deneyim_puani": 0,
                "beceri_puani": 0,
                "proje_puani": 0
            },
            "guclu_yonler": [
                "Bilgi yetersiz"
            ],
            "gelistirilmesi_gereken_yonler": [
                "Bilgi yetersiz"
            ],
            "uygun_pozisyonlar": [
                "Belirtilmemiş"
            ],
            "yetenek_ozeti": "CV analizi sırasında hata oluştu, yetenek özeti çıkarılamadı.",
            "_hata": error_msg,
            "_raw_text": raw_text[:100] if raw_text else ""
        }
    
    def pozisyon_eslesme_analizi(self, cv_analiz: Dict[str, Any], pozisyon: str) -> Dict[str, Any]:
        """
        CV'nin belirli bir pozisyonla ne kadar uyumlu olduğunu analiz eder
        
        Args:
            cv_analiz (Dict[str, Any]): CV analiz sonuçları
            pozisyon (str): Değerlendirilecek pozisyon
            
        Returns:
            Dict[str, Any]: Uyumluluk analizi sonuçları
        """
        # CV metni ve pozisyon bilgisini birleştirerek bir prompt oluştur
        cv_json = json.dumps(cv_analiz, ensure_ascii=False)
        
        prompt = f"""
        <GÖREV>
        Aşağıda bir CV analizi ve bir pozisyon bilgisi verilmiştir. Bu CV'nin belirtilen pozisyon için 
        ne kadar uyumlu olduğunu detaylı olarak analiz et.
        </GÖREV>
        
        <CV_ANALİZ>
        {cv_json}
        </CV_ANALİZ>
        
        <POZİSYON>
        {pozisyon}
        </POZİSYON>
        
        <FORMAT>
        ```json
        {{
          "pozisyon": "Analiz edilen pozisyon",
          "uyumluluk_puani": 0-100 arası puan,
          "detayli_puanlama": {{
            "egitim_uyumu": 0-100 arası puan,
            "deneyim_uyumu": 0-100 arası puan,
            "beceri_uyumu": 0-100 arası puan,
            "proje_uyumu": 0-100 arası puan
          }},
          "eksik_beceriler": [
            "Eksik beceri 1",
            "Eksik beceri 2"
          ],
          "guclu_yonler": [
            "Pozisyon için güçlü yön 1",
            "Pozisyon için güçlü yön 2"
          ],
          "tavsiyeler": [
            "Pozisyon için geliştirme tavsiyesi 1",
            "Pozisyon için geliştirme tavsiyesi 2"
          ],
          "genel_degerlendirme": "Pozisyon uyumluluğu hakkında genel değerlendirme"
        }}
        ```
        </FORMAT>
        
        Sadece JSON formatında cevap ver, ek açıklama yapma.
        """
        
        try:
            logger.info(f"'{self.model_name}' modeli ile pozisyon uyum analizi yapılıyor: {pozisyon}")
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': self.model_name,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.4,  # Biraz daha çeşitlilik için
                    'num_predict': 4000
                },
                timeout=180
            )
            
            if response.status_code != 200:
                logger.error(f"API hatası: {response.status_code} - {response.text}")
                raise Exception(f"API hatası: {response.status_code}")
            
            response_text = response.json().get('response', '')
            elapsed_time = time.time() - start_time
            logger.info(f"Pozisyon uyum analizi tamamlandı - {elapsed_time:.2f} saniye")
            
            # JSON çıkarma
            parsed_json = self._extract_json(response_text)
            return parsed_json
            
        except Exception as e:
            logger.error(f"Pozisyon analizi sırasında hata: {str(e)}")
            raise

def pdf_to_text(pdf_path: str) -> str:
    """
    PDF dosyasını metne dönüştürür
    
    Args:
        pdf_path (str): PDF dosya yolu
        
    Returns:
        str: Çıkarılan metin
    """
    try:
        from io import StringIO
        from pdfminer.high_level import extract_text_to_fp
        from pdfminer.layout import LAParams
        
        output = StringIO()
        with open(pdf_path, 'rb') as fp:
            extract_text_to_fp(fp, output, laparams=LAParams())
        
        return output.getvalue()
    except ImportError:
        logger.error("pdfminer.six kütüphanesi bulunamadı. 'pip install pdfminer.six' komutu ile yükleyin.")
        raise
    except Exception as e:
        logger.error(f"PDF metin çıkarma hatası: {str(e)}")
        raise

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
    if kisisel.get("web_sitesi"):
        print(f"  Web Sitesi: {kisisel.get('web_sitesi')}")
    
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
            
            if job.get("anahtar_basarilar"):
                print("     Anahtar Başarılar:")
                for basari in job.get("anahtar_basarilar", []):
                    print(f"       • {basari}")
        print()
    
    # Projeler
    if analiz.get("projeler") and detayli_mi:
        print("\n🔨 PROJELER:")
        for i, proje in enumerate(analiz.get("projeler", []), 1):
            print(f"  {i}. {proje.get('ad', 'Belirtilmemiş')}")
            if proje.get("tarih"):
                print(f"     Tarih: {proje.get('tarih')}")
            if proje.get("aciklama"):
                print(f"     Açıklama: {proje.get('aciklama')}")
            
            if proje.get("teknolojiler"):
                print("     Kullanılan Teknolojiler:")
                for tech in proje.get("teknolojiler", []):
                    print(f"       • {tech}")
            
            if proje.get("kazanimlar"):
                print("     Kazanımlar:")
                for kazanim in proje.get("kazanimlar", []):
                    print(f"       • {kazanim}")
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
    if analiz.get("liderlik_ve_gönüllülük") and detayli_mi:
        print("\n👥 LİDERLİK VE GÖNÜLLÜLÜK:")
        for i, org in enumerate(analiz.get("liderlik_ve_gönüllülük", []), 1):
            print(f"  {i}. {org.get('organizasyon', 'Belirtilmemiş')} - {org.get('pozisyon', 'Belirtilmemiş')}")
            if org.get("tarih"):
                print(f"     Tarih: {org.get('tarih')}")
            if org.get("açıklama"):
                print(f"     Açıklama: {org.get('açıklama')}")
            print()
    
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
        analizci = GelismisCVAnalizci(model_name=args.model)
        print(f"CV analizi yapılıyor (model: {analizci.model_name})...")
        analiz_sonuc = analizci.cv_analiz_et(cv_text)
        
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