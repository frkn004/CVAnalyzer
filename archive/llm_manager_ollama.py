#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Any, List
import os
from pathlib import Path
import json
import logging
import time
import re
import requests

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Ollama API kullanarak LLM yönetimi yapan sınıf.
    Orijinal LLMManager sınıfı ile aynı arayüze sahip,
    eski kodunuzu değiştirmeden kullanabilirsiniz.
    """
    
    def __init__(self, model_path: Optional[str] = None, model_type: str = None, force_phi: bool = False):
        """
        LLM yönetici sınıfı
        
        Args:
            model_path (str): Model ismi veya dosya yolu (None ise otomatik seçilir)
            model_type (str): Model tipi - Ollama için kullanılmıyor
            force_phi (bool): Phi modeli zorlaması - Ollama için kullanılmıyor
        """
        self.base_url = "http://localhost:11434"
        self.available_models = []
        
        # Ollama API'nin çalışıp çalışmadığını kontrol et
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                self.available_models = [model.get('name') for model in response.json().get('models', [])]
                logger.info(f"Ollama API bağlantısı başarılı! Mevcut modeller: {', '.join(self.available_models)}")
            else:
                logger.error(f"Ollama API yanıt verdi ancak hata kodu döndürdü: {response.status_code}")
        except Exception as e:
            logger.error(f"Ollama API'ye bağlanılamadı: {str(e)}")
            logger.error("Ollama yüklü ve çalışıyor mu? 'ollama serve' komutu çalıştırılmalı.")
        
        # Model yolu veya adı verilmişse, bunu kullan
        if model_path:
            # Dosya yolu verilmişse model adını çıkar
            if os.path.exists(model_path):
                self.model_name = os.path.basename(model_path).split('.')[0]
            else:
                # Doğrudan model adı verilmiş olabilir
                self.model_name = model_path
        else:
            # Otomatik model seçimi - öncelik sırası: llama3 > phi > llama > mistral > diğerleri
            self.model_name = self._select_best_model()
            
        logger.info(f"Seçilen model: {self.model_name}")
        self.model = None  # Model yüklendikten sonra True olarak ayarlanacak
        
    def _select_best_model(self) -> str:
        """En uygun modeli seç"""
        if not self.available_models:
            return ""
            
        # Model seçim önceliği 
        for model_pattern in ["llama3:8b", "phi", "llama", "mistral"]:
            for model in self.available_models:
                if model_pattern in model.lower():
                    return model
        
        # Hiçbiri bulunamazsa ilk modeli kullan
        return self.available_models[0]
        
    def load_model(self, context_length: int = 16384, max_new_tokens: int = 4096) -> None:
        """Modeli yükler"""
        if not self.model_name:
            raise ValueError("Model adı belirtilmedi!")
            
        if not self.available_models:
            raise ValueError("Hiçbir model bulunamadı! Ollama çalışıyor mu?")
            
        # Modelin mevcut olup olmadığını kontrol et
        if self.model_name not in self.available_models:
            closest_match = next((m for m in self.available_models if self.model_name in m), None)
            
            if closest_match:
                logger.warning(f"Tam eşleşen model bulunamadı. Benzer model kullanılıyor: {closest_match}")
                self.model_name = closest_match
            else:
                # Eşleşen model yoksa ilk modeli kullan
                logger.warning(f"Model '{self.model_name}' bulunamadı! İlk mevcut model kullanılıyor: {self.available_models[0]}")
                self.model_name = self.available_models[0]
        
        # Modeli ön belleğe almak için küçük bir istek gönder
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    'model': self.model_name,
                    'prompt': 'Merhaba',
                    'stream': False
                }
            )
            
            if response.status_code == 200:
                self.model = True  # Model başarıyla yüklendi
                logger.info(f"Model başarıyla yüklendi: {self.model_name}")
            else:
                logger.error(f"Model yüklenemedi: {response.status_code} - {response.text}")
                raise RuntimeError(f"Model yüklenemedi: {response.text}")
                
        except Exception as e:
            logger.error(f"Model yükleme hatası: {str(e)}")
            raise RuntimeError(f"Model yükleme hatası: {str(e)}")
        
    def generate(self, prompt: str, temperature: float = 0.1, top_p: float = 0.95, 
                top_k: int = 40, repetition_penalty: float = 1.1, 
                max_new_tokens: int = 4096) -> str:
        """
        Verilen prompt için metin üretir
        
        Args:
            prompt (str): Giriş metni
            temperature (float): Yaratıcılık seviyesi (düşük = daha tutarlı)
            top_p (float): Nucleus sampling parametresi
            top_k (int): Top-k sampling parametresi
            repetition_penalty (float): Tekrar cezası
            max_new_tokens (int): Üretilecek maksimum token sayısı
            
        Returns:
            str: Üretilen metin
        """
        if not self.model:
            raise RuntimeError("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            
        logger.info(f"Metin üretme başlatılıyor (temp={temperature}, tokens={max_new_tokens})")
        
        try:
            # Prompt uzunluğunu kontrol et
            if len(prompt) > 16000:
                logger.warning(f"Prompt çok uzun ({len(prompt)} karakter), kısaltılıyor...")
                prompt = prompt[:16000]  # Maksimum 16000 karakter ile sınırla
            
            start_time = time.time()
            
            # Ollama API parametreleri
            params = {
                'model': self.model_name,
                'prompt': prompt,
                'stream': False,
                'temperature': temperature,
                'num_predict': max_new_tokens,
                'top_p': top_p,
                'top_k': top_k,
                'repeat_penalty': repetition_penalty
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate", 
                json=params,
                timeout=180  # 3 dakika timeout
            )
            
            if response.status_code != 200:
                logger.error(f"API hatası: {response.status_code} - {response.text}")
                return f"Metin üretme hatası: API yanıt hatası: {response.status_code}"
            
            result = response.json().get('response', '')
            
            elapsed_time = time.time() - start_time
            logger.info(f"Metin üretildi! Uzunluk: {len(result)}, Süre: {elapsed_time:.1f}s")
            
            # Boş yanıt kontrolü
            if not result or len(result) < 10:
                logger.warning("Model boş veya çok kısa yanıt döndü, tekrar deneniyor...")
                # Daha yüksek temperature ile tekrar dene
                params['temperature'] = 0.8  # Daha yüksek yaratıcılık
                params['top_k'] = 60
                params['repeat_penalty'] = 1.0  # Tekrar cezası yok
                
                response = requests.post(
                    f"{self.base_url}/api/generate", 
                    json=params,
                    timeout=180
                )
                
                result = response.json().get('response', '')
                logger.info(f"İkinci deneme sonucu: {len(result)} karakter")
            
            return result
            
        except Exception as e:
            logger.error(f"Metin üretme hatası: {str(e)}")
            return f"Metin üretme hatası: {str(e)}"
        
    def analyze_cv(self, cv_text: str) -> Dict[str, Any]:
        """
        CV metnini analiz eder
        
        Args:
            cv_text (str): CV metni
            
        Returns:
            Dict[str, Any]: Analiz sonuçları (Bilgiler, eğitim, deneyim, vb.)
        """
        if not self.model:
            logger.error("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            return {"error": "Model yüklenemedi", "raw_response": "Lütfen tekrar deneyin."}
            
        # Daha temiz ve daha kısa bir prompt
        prompt = f"""
        <KONU>CV ANALİZİ</KONU>
        
        <CV>
        {cv_text[:7000]}
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
            logger.info(f"CV metni uzunluğu: {len(cv_text)}, analiz başlıyor...")
            
            try:
                # Ollama API parametreleri - daha yüksek sıcaklık kullan
                params = {
                    'model': self.model_name,
                    'prompt': prompt,
                    'stream': False,
                    'temperature': 0.3,
                    'num_predict': 4000
                }
                
                response = requests.post(
                    f"{self.base_url}/api/generate", 
                    json=params,
                    timeout=180  # 3 dakika timeout
                )
                
                if response.status_code != 200:
                    logger.error(f"API hatası: {response.status_code} - {response.text}")
                    return self._create_default_cv_response(cv_text=cv_text, error_msg=f"API hatası: {response.status_code}")
                
                response_text = response.json().get('response', '')
                logger.info(f"Model yanıtı alındı, yanıt uzunluğu: {len(response_text)}")
                
                # Yanıt boş veya çok kısa ise varsayılan yanıta dön
                if len(response_text) < 50:  # 50 karakterden kısa ise anlamsız yanıt kabul et
                    logger.warning(f"Model çok kısa yanıt döndü ({len(response_text)} karakter), varsayılan işleme moduna geçiliyor")
                    return self._create_default_cv_response(cv_text=cv_text, error_msg="Model yanıtı çok kısa", raw_response=response_text)
                
            except Exception as gen_err:
                logger.error(f"Model yanıt üretemedi: {str(gen_err)}")
                return self._create_default_cv_response(error_msg=f"Model yanıt üretemedi: {str(gen_err)}")
            
            # JSON çıkarma işlemi
            json_content = None
            
            # XML/HTML benzeri etiketleri çıkar
            clean_response = re.sub(r'<[^>]+>', '', response_text)
            
            # JSON bloğunu temizle
            clean_response = clean_response.replace('```json', '').replace('```', '')
            
            # JSON bracket algılama
            json_start = clean_response.find('{')
            json_end = clean_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = clean_response[json_start:json_end]
                logger.info(f"JSON içeriği bulundu, uzunluk: {len(json_content)}")
            else:
                logger.warning(f"JSON formatı bulunamadı! Yanıt: {clean_response[:200]}")
                return self._create_default_cv_response(cv_text=cv_text, error_msg="JSON formatı bulunamadı", raw_response=response_text[:500])
            
            try:
                # JSON düzeltme denemeleri
                json_str = json_content.strip()
                
                # Model çıktısında sorun olabilecek yerleri düzelt
                json_str = json_str.replace("'", '"')  # Tek tırnak yerine çift tırnak
                json_str = json_str.replace(",}", "}")  # Gereksiz virgül
                json_str = json_str.replace(",]", "]")  # Gereksiz virgül
                
                # Boş değerleri temizle
                json_str = re.sub(r':\s*null', ': ""', json_str)
                json_str = re.sub(r':\s*undefined', ': ""', json_str)
                
                # JSON ayrıştır
                try:
                    result = json.loads(json_str)
                    logger.info(f"JSON başarıyla ayrıştırıldı, alanlar: {', '.join(result.keys())}")
                    return result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON ayrıştırma denemesi başarısız: {e}")
                    
                    # En son çare - regex tabanlı işleme
                    return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON formatı oluşturulamadı: {str(e)}")
                    
            except Exception as e:
                logger.error(f"JSON düzeltme hatası: {str(e)}")
                return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON düzeltme hatası: {str(e)}", raw_response=response_text[:300])
                
        except Exception as e:
            logger.error(f"CV analizi sırasında beklenmeyen hata: {str(e)}")
            import traceback
            logger.error(f"Hata detayları: {traceback.format_exc()}")
            return self._create_default_cv_response(cv_text=cv_text, error_msg=f"CV analizi hatası: {str(e)}")
    
    def _create_default_cv_response(self, cv_text="", error_msg="Bilinmeyen hata", raw_response=""):
        """CV için regex tabanlı gelişmiş bilgi çıkarma (hata durumunda veya doğrudan kullanım için)"""
        try:
            # CV metnini alt ve üst satırlara böl (analiz için)
            lines = cv_text.split('\n')
            clean_lines = [line.strip() for line in lines if line.strip()]
            
            # Çıkarılacak veriler
            extracted = {
                "kisisel_bilgiler": {
                    "isim": "",
                    "email": "",
                    "telefon": "",
                    "adres": "",
                    "linkedin": ""
                },
                "egitim": [],
                "is_deneyimi": [],
                "beceriler": [],
                "diller": [],
                "sertifikalar": []
            }
            
            # İsim çıkarma (ilk satırlar genellikle isim içerir)
            name_patterns = [
                r"([A-Z][a-zçğıöşü]+\s+[A-Z][a-zçğıöşü]+)",  # Ad Soyad formatı
                r"([A-Z][a-zçğıöşü]+ [A-Z][a-zçğıöşü]+ [A-Z][a-zçğıöşü]+)",  # Ad İkinci Soyad
                r"^([A-Z][A-ZÇĞİÖŞÜ\s]+)$"  # BÜYÜK HARFLE YAZILMIŞ İSİM
            ]
            
            # İlk 5 satıra bakarak isim bul
            for i in range(min(5, len(clean_lines))):
                for pattern in name_patterns:
                    name_match = re.search(pattern, clean_lines[i])
                    if name_match:
                        extracted["kisisel_bilgiler"]["isim"] = name_match.group(1)
                        break
                if extracted["kisisel_bilgiler"]["isim"]:
                    break
            
            # E-posta çıkarma
            email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", cv_text)
            if email_match:
                extracted["kisisel_bilgiler"]["email"] = email_match.group(0)
                
            # Telefon çıkarma (çeşitli formatlar için)
            phone_patterns = [
                r"(?:\+90|0)?[ ]?(?:\(?\d{3}\)?[\s.-]?){1,2}\d{3}[\s.-]?\d{2}[\s.-]?\d{2}",  # Türk telefon
                r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",  # (123) 456-7890 veya 123-456-7890
                r"\+\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}"  # Uluslararası formatlar
            ]
            
            for pattern in phone_patterns:
                phone_match = re.search(pattern, cv_text)
                if phone_match:
                    extracted["kisisel_bilgiler"]["telefon"] = phone_match.group(0)
                    break
            
            # LinkedIn çıkarma
            linkedin_pattern = r"linkedin\.com/in/[\w-]+"
            linkedin_match = re.search(linkedin_pattern, cv_text.lower())
            if linkedin_match:
                extracted["kisisel_bilgiler"]["linkedin"] = linkedin_match.group(0)
            
            # Adres çıkarma (basitçe: içinde sokak, cadde, mahalle geçen satırlar)
            address_keywords = ["sokak", "cadde", "mahalle", "mah.", "sok.", "cad.", "apt", "daire", "kat", "no:", "no :", "no "]
            for line in clean_lines:
                if any(keyword in line.lower() for keyword in address_keywords):
                    extracted["kisisel_bilgiler"]["adres"] = line.strip()
                    break
            
            # Eğitim kurumları için yaygın kelimeler
            education_keywords = ["üniversite", "university", "fakülte", "faculty", "okul", "school", 
                                "kolej", "college", "yüksek", "lisans", "bachelor", "master", "doktora", 
                                "phd", "mba", "eğitim", "education", "mezun", "graduate"]
            
            # Eğitim bilgileri çıkarma
            education_sections = []
            current_section = []
            in_education_section = False
            
            # Eğitim bölümünü belirleme
            for i, line in enumerate(clean_lines):
                # Eğitim bölümü başlangıcını tespit et
                if any(keyword.lower() in line.lower() for keyword in ["EĞİTİM", "EDUCATION", "AKADEMİK"]) and len(line) < 30:
                    in_education_section = True
                    continue
                
                # Eğitim bölümünün bittiğini belirle (yeni bir bölüm başlıyor)
                if in_education_section and len(line) < 30 and line.isupper() and not any(edu_kw in line.lower() for edu_kw in education_keywords):
                    in_education_section = False
                
                # Eğitim bölümü içinde, eğitim kurumu içeren satırları topla
                if in_education_section or any(keyword in line.lower() for keyword in education_keywords):
                    current_section.append(line)
                elif current_section:
                    education_sections.append(current_section)
                    current_section = []
            
            if current_section:
                education_sections.append(current_section)
            
            # Her eğitim girdisini işle
            for section in education_sections:
                if not section:
                    continue
                    
                edu_entry = {"okul": "", "bolum": "", "tarih": ""}
                
                # Okul adını bul (genellikle ilk satırdır)
                for line in section:
                    if any(keyword in line.lower() for keyword in education_keywords):
                        edu_entry["okul"] = line
                        break
                
                # Tarih bilgisini bul (genellikle 4 rakam içerir, örnek: 2018-2022)
                date_match = re.search(r"((?:19|20)\d{2})(?:\s*[-–—]\s*)((?:19|20)\d{2}|devam|present|current|halen|günümüze|şimdi)", " ".join(section), re.IGNORECASE)
                if date_match:
                    edu_entry["tarih"] = f"{date_match.group(1)}-{date_match.group(2)}"
                else:
                    # Tek yıl (mezuniyet)
                    year_match = re.search(r"(?:19|20)\d{2}", " ".join(section))
                    if year_match:
                        edu_entry["tarih"] = year_match.group(0)
                
                # Bölüm bilgisini bul
                department_keywords = ["bölüm", "department", "program", "dalı", "alanı", "field"]
                for line in section:
                    if any(keyword in line.lower() for keyword in department_keywords) and line != edu_entry["okul"]:
                        edu_entry["bolum"] = line
                        break
                
                # Eğer bölüm bulunamadıysa, okul olmayan ve tarih olmayan ilk satırı dene
                if not edu_entry["bolum"]:
                    for line in section:
                        if line != edu_entry["okul"] and not re.search(r"(?:19|20)\d{2}", line):
                            edu_entry["bolum"] = line
                            break
                
                # Sadece okul varsa ekle
                if edu_entry["okul"]:
                    extracted["egitim"].append(edu_entry)
            
            # Deneyim bölümü için anahtar kelimeler
            experience_keywords = ["deneyim", "experience", "iş", "work", "çalış", "professional", 
                                "career", "kariyer", "pozisyon", "position", "görev", "role", "staj", "intern"]
            
            # İş deneyimi bilgileri çıkarma
            experience_sections = []
            current_section = []
            in_experience_section = False
            
            # Deneyim bölümünü belirleme
            for i, line in enumerate(clean_lines):
                # Deneyim bölümü başlangıcını tespit et
                if any(keyword.lower() in line.lower() for keyword in ["DENEYİM", "EXPERIENCE", "İŞ", "WORK"]) and len(line) < 30:
                    in_experience_section = True
                    continue
                
                # Deneyim bölümünün bittiğini belirle
                if in_experience_section and len(line) < 30 and line.isupper() and not any(exp_kw in line.lower() for exp_kw in experience_keywords):
                    in_experience_section = False
                
                # Deneyim bölümü içindeki satırları topla
                if in_experience_section or any(keyword in line.lower() for keyword in experience_keywords):
                    current_section.append(line)
                elif current_section:
                    experience_sections.append(current_section)
                    current_section = []
            
            if current_section:
                experience_sections.append(current_section)
            
            # Her deneyim girdisini işle
            for section in experience_sections:
                if not section:
                    continue
                    
                exp_entry = {"sirket": "", "pozisyon": "", "tarih": ""}
                
                # Şirket adını bul (genellikle ilk satırda işyeri/şirket adı geçer)
                company_keywords = ["şirket", "company", "inc", "ltd", "a.ş.", "limited", "holding", "gmbh", "corporation"]
                for line in section:
                    if any(keyword in line.lower() for keyword in company_keywords):
                        exp_entry["sirket"] = line
                        break
                
                # Eğer şirket adı bulunamadıysa, ilk satırı dene
                if not exp_entry["sirket"] and section:
                    exp_entry["sirket"] = section[0]
                
                # Pozisyon bilgisini bul
                position_keywords = ["pozisyon", "position", "görev", "role", "title", "olarak", "as a", "ünvan"]
                for line in section:
                    if any(keyword in line.lower() for keyword in position_keywords) and line != exp_entry["sirket"]:
                        exp_entry["pozisyon"] = line
                        break
                
                # Eğer pozisyon bulunamadıysa ve en az 2 satır varsa, ikinci satırı dene
                if not exp_entry["pozisyon"] and len(section) > 1:
                    exp_entry["pozisyon"] = section[1]
                
                # Tarih bilgisini bul (genellikle 4 rakam içerir, örnek: 2018-2022)
                date_match = re.search(r"((?:19|20)\d{2})(?:\s*[-–—]\s*)((?:19|20)\d{2}|present|current|devam|halen|günümüze|şimdi)", " ".join(section), re.IGNORECASE)
                if date_match:
                    exp_entry["tarih"] = f"{date_match.group(1)}-{date_match.group(2)}"
                else:
                    # Tek yıl
                    year_match = re.search(r"(?:19|20)\d{2}", " ".join(section))
                    if year_match:
                        exp_entry["tarih"] = year_match.group(0)
                
                # Sadece şirket varsa ekle
                if exp_entry["sirket"]:
                    extracted["is_deneyimi"].append(exp_entry)
            
            # Beceriler bölümü için anahtar kelimeler
            skill_section_keywords = ["beceri", "skill", "yetenek", "ability", "competenc", "technical", "teknik"]
            
            # Becerileri çıkarma
            skills_section = []
            in_skills_section = False
            
            # Beceri bölümünü belirleme
            for i, line in enumerate(clean_lines):
                if any(keyword.lower() in line.lower() for keyword in skill_section_keywords) and len(line) < 30:
                    in_skills_section = True
                    continue
                    
                if in_skills_section and len(line) < 30 and line.isupper():
                    in_skills_section = False
                    
                if in_skills_section:
                    skills_section.append(line)
            
            # Yaygın teknoloji/beceri listesi
            common_tech_skills = [
                # Programlama Dilleri
                "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "PHP", "Ruby", "Swift", "Kotlin", 
                "Go", "Rust", "Scala", "Perl", "R", "MATLAB", "Dart", "Objective-C", "Shell", "PowerShell",
                
                # Web Teknolojileri
                "HTML", "CSS", "React", "Angular", "Vue", "Node.js", "Express", "Django", "Flask", "Laravel",
                "Spring", "ASP.NET", "Ruby on Rails", "jQuery", "Bootstrap", "Sass", "Less", "Redux", "Next.js",
                "Gatsby", "GraphQL", "REST API", "SOAP", "XML", "JSON", "WebSockets",
                
                # Veritabanları
                "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "Microsoft SQL Server", "Redis",
                "Cassandra", "Elasticsearch", "DynamoDB", "Firebase", "MariaDB", "Neo4j", "CouchDB",
                
                # Bulut Hizmetleri
                "AWS", "Azure", "Google Cloud", "Heroku", "DigitalOcean", "Kubernetes", "Docker", "Terraform",
                "CloudFormation", "Lambda", "S3", "EC2", "RDS", "DynamoDB", "Firebase", "Netlify", "Vercel",
                
                # Araçlar ve Diğer
                "Git", "GitHub", "GitLab", "Bitbucket", "JIRA", "Confluence", "Trello", "Slack", "Jenkins",
                "Travis CI", "CircleCI", "Ansible", "Puppet", "Chef", "Selenium", "JUnit", "PyTest", "Mocha",
                "Jasmine", "Webpack", "Babel", "ESLint", "Prettier", "npm", "Yarn",
                
                # Ofis Becerileri
                "Microsoft Office", "Excel", "Word", "PowerPoint", "Outlook", "Google Docs", "Google Sheets",
                "Google Slides", "Visio", "Project", "Access", "OneNote",
                
                # Tasarım
                "Photoshop", "Illustrator", "InDesign", "Figma", "Sketch", "Adobe XD", "After Effects",
                "Premiere Pro", "UI/UX", "Responsive Design", "Wireframing", "Prototyping",
                
                # Diller (İngilizce ve Türkçe dışında)
                "Fransızca", "Almanca", "İspanyolca", "İtalyanca", "Rusça", "Çince", "Japonca", "Korece",
                "Arapça", "Portekizce", "Hollandaca",
                
                # Yapay Zeka / Makine Öğrenimi
                "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras", "Scikit-learn",
                "NLP", "Computer Vision", "OpenAI", "BERT", "GPT",
                
                # Veri Bilimi
                "Data Science", "Data Analysis", "Data Visualization", "Pandas", "NumPy", "Matplotlib",
                "Seaborn", "Tableau", "Power BI", "D3.js", "Jupyter", "Big Data", "Hadoop", "Spark"
            ]
            
            # CV metninde geçen becerileri bul
            found_skills = set()
            for skill in common_tech_skills:
                skill_pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(skill_pattern, cv_text, re.IGNORECASE):
                    found_skills.add(skill)
            
            # Beceri bölümünden virgül veya madde işareti ile ayrılmış becerileri ayıkla
            if skills_section:
                skills_text = ' '.join(skills_section)
                # Virgülle ayrılmış beceriler
                comma_separated = re.split(r'[,،|•⋅⦁\-●·]', skills_text)
                for item in comma_separated:
                    item = item.strip()
                    if item and len(item) > 1 and item.lower() not in ["ve", "and", "skills", "beceriler"]:
                        found_skills.add(item)
            
            # Becerileri ekle
            extracted["beceriler"] = list(found_skills)
            
            # Dil becerileri
            language_keywords = ["ingilizce", "english", "türkçe", "turkish", "almanca", "german", "fransızca", 
                                "french", "ispanyolca", "spanish", "italyanca", "italian", "rusça", "russian", 
                                "arapça", "arabic", "çince", "chinese", "japonca", "japanese"]
            
            language_levels = ["native", "anadil", "akıcı", "fluent", "çok iyi", "very good", "advanced", 
                             "ileri", "intermediate", "orta", "pre-intermediate", "başlangıç", "beginner", 
                             "elementary", "a1", "a2", "b1", "b2", "c1", "c2"]
            
            # Dil bölümü
            language_section = []
            in_language_section = False
            
            for i, line in enumerate(clean_lines):
                if any(keyword in line.lower() for keyword in ["dil", "language", "foreign", "yabancı"]) and len(line) < 30:
                    in_language_section = True
                    continue
                    
                if in_language_section and len(line) < 30 and line.isupper():
                    in_language_section = False
                    
                if in_language_section:
                    language_section.append(line)
            
            # Metin içinde dil seviyelerini ara
            found_languages = []
            
            if language_section:
                languages_text = ' '.join(language_section)
                for lang in language_keywords:
                    if lang in languages_text.lower():
                        # Dil seviyesini bulmaya çalış
                        for level in language_levels:
                            level_pattern = r'\b' + re.escape(lang) + r'.*?\b' + re.escape(level) + r'\b'
                            alt_pattern = r'\b' + re.escape(level) + r'.*?\b' + re.escape(lang) + r'\b'
                            
                            level_match = re.search(level_pattern, languages_text, re.IGNORECASE)
                            alt_match = re.search(alt_pattern, languages_text, re.IGNORECASE)
                            
                            if level_match or alt_match:
                                found_languages.append(f"{lang.capitalize()} ({level.capitalize()})")
                                break
                        else:
                            found_languages.append(lang.capitalize())
            
            # Genel metinde dilleri ara (eğer dil bölümü bulunamadıysa)
            if not found_languages:
                for lang in language_keywords:
                    if lang in cv_text.lower():
                        found_languages.append(lang.capitalize())
            
            extracted["diller"] = found_languages
            
            # Sertifikalar
            certificate_keywords = ["sertifika", "certificate", "certification", "certified", "credential",
                                 "diploma", "lisans", "license", "accreditation", "course", "eğitim", "training"]
            
            certificate_section = []
            in_certificate_section = False
            
            for i, line in enumerate(clean_lines):
                if any(keyword in line.lower() for keyword in certificate_keywords) and len(line) < 30:
                    in_certificate_section = True
                    continue
                    
                if in_certificate_section and len(line) < 30 and line.isupper():
                    in_certificate_section = False
                    
                if in_certificate_section:
                    certificate_section.append(line)
            
            # Sertifikaları ayıkla
            found_certificates = []
            
            if certificate_section:
                cert_text = ' '.join(certificate_section)
                # Virgülle veya yeni satırlarla ayrılmış sertifikalar
                cert_items = re.split(r'[,،|•⋅⦁\-●·\n]', cert_text)
                for item in cert_items:
                    item = item.strip()
                    if item and len(item) > 10 and not any(kw in item.lower() for kw in ["sertifika", "certificate", "sertifikalar", "certificates"]):
                        found_certificates.append(item)
            
            extracted["sertifikalar"] = found_certificates
            
            # Sonuç oluştur
            result = {
                "kisisel_bilgiler": {
                    "isim": extracted["kisisel_bilgiler"]["isim"] or "CV'den İsim Alınamadı",
                    "email": extracted["kisisel_bilgiler"]["email"] or "email@bulunamadi.com",
                    "telefon": extracted["kisisel_bilgiler"]["telefon"] or "N/A"
                },
                "beceriler": extracted["beceriler"] or ["CV'den beceriler alınamadı"],
                "is_deneyimi": extracted["is_deneyimi"] or [{"sirket": "N/A", "pozisyon": "N/A", "tarih": "N/A"}],
                "egitim": extracted["egitim"] or [{"okul": "N/A", "bolum": "N/A", "tarih": "N/A"}],
                "diller": extracted["diller"] or ["Dil bilgisi bulunamadı"],
                "sertifikalar": extracted["sertifikalar"] or []
            }
            
            # Eğer adres ve LinkedIn varsa ekle
            if extracted["kisisel_bilgiler"]["adres"]:
                result["kisisel_bilgiler"]["adres"] = extracted["kisisel_bilgiler"]["adres"]
                
            if extracted["kisisel_bilgiler"]["linkedin"]:
                result["kisisel_bilgiler"]["linkedin"] = extracted["kisisel_bilgiler"]["linkedin"]
            
            # Hata bilgisini ekle (isteğe bağlı alanlar)
            if error_msg:
                result["_hata_bilgisi"] = error_msg
                
            if raw_response:
                result["_ham_yanit"] = raw_response[:200] if raw_response else ""
                
            return result
            
        except Exception as e:
            logger.error(f"Varsayılan yanıt oluşturulurken hata: {str(e)}")
            import traceback
            logger.error(f"Hata ayrıntıları: {traceback.format_exc()}")
            
            # En basit yanıt
            return {
                "kisisel_bilgiler": {"isim": "Yanıt Üretilemedi", "email": "N/A", "telefon": "N/A"},
                "beceriler": ["CV analizi başarısız"],
                "is_deneyimi": [{"sirket": "N/A", "pozisyon": "N/A", "tarih": "N/A"}],
                "egitim": [{"okul": "N/A", "bolum": "N/A", "tarih": "N/A"}],
                "error": error_msg
            }


if __name__ == "__main__":
    # Test kodu
    logging.basicConfig(level=logging.INFO)
    print("Ollama entegrasyonlu LLMManager testi başlıyor...")
    
    # Ollama API'sini kontrol et
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("✅ Ollama API bağlantısı başarılı!")
            models = [model.get('name') for model in response.json().get('models', [])]
            print(f"Mevcut modeller: {', '.join(models)}")
            
            # LLMManager'ı başlat
            manager = LLMManager()
            
            # Modeli yükle
            manager.load_model()
            
            # Test dosyası yolunu al
            import sys
            if len(sys.argv) > 1:
                test_file = sys.argv[1]
            else:
                test_file = input("Test edilecek CV dosyasının yolunu girin (varsayılan: cv_ornek.txt): ") or "cv_ornek.txt"
            
            # Dosyayı oku
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    cv_text = f.read()
                    
                print(f"CV dosyası okundu: {len(cv_text)} karakter")
                
                # CV analizi yap
                print("CV analizi yapılıyor...")
                result = manager.analyze_cv(cv_text)
                
                # Analiz sonucunu göster
                print("\n=== CV ANALİZ SONUÇLARI ===")
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
            except Exception as e:
                print(f"❌ Dosya okuma hatası: {str(e)}")
            
        else:
            print(f"❌ Ollama API yanıt verdi ancak hata kodu döndürdü: {response.status_code}")
    except Exception as e:
        print(f"❌ Ollama API'ye bağlanılamadı: {str(e)}")
        print("Ollama yüklü ve çalışıyor mu? 'ollama serve' komutunu çalıştırın.") 