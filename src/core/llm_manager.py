from typing import Optional, Dict, Any, List
import os
from pathlib import Path
import json
import logging
from tqdm import tqdm
import importlib.util
import re

logger = logging.getLogger(__name__)

# CTransformers kütüphanesinin yüklü olup olmadığını kontrol et
CTRANSFORMERS_AVAILABLE = importlib.util.find_spec("ctransformers") is not None

if CTRANSFORMERS_AVAILABLE:
    from ctransformers import AutoModelForCausalLM
else:
    logger.warning("ctransformers kütüphanesi bulunamadı. Yalnızca önceden işlenmiş analiz kullanılabilir.")
    AutoModelForCausalLM = None

class LLMManager:
    def __init__(self, model_path: Optional[str] = None, model_type: str = None, force_phi: bool = False):
        """
        LLM yönetici sınıfı
        
        Args:
            model_path (str): Model dosyasının yolu (None ise otomatik seçilir)
            model_type (str): Model tipi (varsayılan: None, otomatik belirlenecek)
            force_phi (bool): Phi-2 modelini zorla kullan (varsayılan: False)
        """
        self.force_phi = force_phi
        self.model_path = self._select_best_model() if model_path is None else Path(model_path)
        
        # Model tipini belirle - phi modelini öncelikle kullan
        if model_type is None:
            model_name = str(self.model_path).lower()
            
            # Phi modelini kullanırken doğrudan model_type belirle
            if "phi" in model_name or self.force_phi:
                self.model_type = "gptj"  # Phi için "gpt_neox" yerine "gptj" kullanıyoruz
            elif "llama-3" in model_name or "meta-llama-3" in model_name:
                self.model_type = "llama"
            elif "tiny" in model_name or "llama" in model_name:
                self.model_type = "llama"
            elif "mistral" in model_name:
                self.model_type = "mistral"
            else:
                # Bilinmeyen model için varsayılan tip
                self.model_type = "gpt_neox"  # Çoğu model için çalışan genel bir tip
        else:
            self.model_type = model_type
            
        self.model = None
        self._ensure_model_directory()
        
        logger.info(f"Model yolu: {self.model_path}, Model tipi: {self.model_type}")
        
    def _ensure_model_directory(self):
        """Model dizininin varlığını kontrol eder ve yoksa oluşturur."""
        model_dir = os.path.dirname(self.model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
    def _select_best_model(self) -> Path:
        """Sistemdeki en iyi modeli seçer - TinyLlama modelini öncelikli olarak dene"""
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        
        # Model dosyalarını bul
        model_files = []
        for file in os.listdir(models_dir):
            if file.endswith(".gguf"):
                model_path = os.path.join(models_dir, file)
                model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB cinsinden
                # 0 boyutlu dosyaları atla
                if model_size > 1:  
                    model_files.append((model_path, model_size, file))
        
        if not model_files:
            raise ValueError("Hiçbir model dosyası bulunamadı. Lütfen models/ dizinine bir GGUF modeli ekleyin.")
        
        # TinyLlama modelini öncelikli olarak tercih et (daha iyi çalışıyor)
        preferred_models = sorted([m for m in model_files if "tiny" in m[2].lower()],
                                key=lambda x: x[1], reverse=True)
                                
        # TinyLlama yoksa, Phi-2 dene (Phi-2 force_phi=True olduğunda çalışır)
        if not preferred_models and self.force_phi:
            preferred_models = sorted([m for m in model_files if "phi-2" in m[2].lower()],
                                  key=lambda x: x[1], reverse=True)
        
        # Yukarıdaki modeller yoksa, Llama 2 dene
        if not preferred_models:
            preferred_models = sorted([m for m in model_files if "llama-2" in m[2].lower()],
                                    key=lambda x: x[1], reverse=True)
        
        # Yukarıdaki modeller yoksa mevcut modeller içinde en küçüğü seç
        if preferred_models:
            selected_model = preferred_models[0]
        else:
            # En küçük ama 0 olmayan modeli seç (1GB'dan küçük olanı tercih et)
            smaller_models = [m for m in model_files if 0 < m[1] < 1000]  # 1GB'dan küçük
            if smaller_models:
                selected_model = sorted(smaller_models, key=lambda x: x[1])[0]
            else:
                # Küçük model yoksa herhangi birini seç
                selected_model = sorted(model_files, key=lambda x: x[1])[0]
            
        logger.info(f"Seçilen model: {selected_model[2]} ({selected_model[1]:.1f} MB)")
        return Path(selected_model[0])
        
    def load_model(self, context_length: int = 16384, max_new_tokens: int = 4096) -> None:
        """Modeli yükler"""
        if not CTRANSFORMERS_AVAILABLE:
            logger.error("ctransformers kütüphanesi bulunamadı. Yüklenemedi.")
            raise ImportError("ctransformers kütüphanesi bulunamadı. 'pip install ctransformers' ile yükleyin.")
        
        if not os.path.exists(self.model_path):
            raise ValueError(f"Model dosyası bulunamadı: {self.model_path}")
        
        try:
            logger.info(f"Model '{self.model_type}' tipi olarak yükleniyor: {self.model_path}")
            self.model = AutoModelForCausalLM.from_pretrained(
                str(self.model_path),
                model_type=self.model_type,
                context_length=context_length,
                max_new_tokens=max_new_tokens,
                threads=os.cpu_count() or 4
            )
            logger.info(f"Model başarıyla yüklendi! Tip: {self.model_type}")
            
        except Exception as e:
            error_msg = f"Model yüklenirken hata: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
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
        if self.model is None:
            raise RuntimeError("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            
        logger.info(f"Metin üretme başlatılıyor (temp={temperature}, tokens={max_new_tokens})")
        try:
            # Önce prompt uzunluğunu kontrol et
            if len(prompt) > 16000:
                logger.warning(f"Prompt çok uzun ({len(prompt)} karakter), kısaltılıyor...")
                prompt = prompt[:16000]  # Maksimum 16000 karakter ile sınırla
            
            response = self.model(
                prompt,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                max_new_tokens=max_new_tokens
            )
            
            # Boş yanıt kontrolü
            if not response or len(response) < 10:
                logger.warning("Model boş veya çok kısa yanıt döndü, tekrar deneniyor...")
                # Daha yüksek temperature ile tekrar dene
                response = self.model(
                    prompt,
                    temperature=0.8,  # Daha yüksek yaratıcılık
                    top_p=0.95,
                    top_k=60,
                    repetition_penalty=1.0,  # Tekrar cezası yok
                    max_new_tokens=max_new_tokens
                )
            
            logger.info(f"Metin üretildi, uzunluk: {len(response)}")
            return response
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
        if self.model is None:
            logger.error("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            return {"error": "Model yüklenemedi", "raw_response": "Lütfen tekrar deneyin."}
            
        # Daha basit ve daha kısa bir prompt, daha uzun CV metni
        prompt = f"""
Lütfen bu CV metnini analiz et:

{cv_text[:7000]}

Yanıtını aşağıdaki JSON formatında ver:

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

ÖNEMLİ: Sadece JSON formatında yanıt ver, başka hiçbir şey yazma.
"""
        
        try:
            logger.info(f"CV metni uzunluğu: {len(cv_text)}, analiz başlıyor...")
            
            try:
                # Response üretme denemesi - daha yüksek token limiti ve sıcaklık
                response = self.generate(
                    prompt, 
                    temperature=0.4,     # Daha yüksek sıcaklık
                    max_new_tokens=4096, # Çok daha fazla token
                    top_p=0.9,          # Daha çeşitli çıktı
                    repetition_penalty=1.03  # Çok az ceza
                )
                logger.info(f"Model yanıtı alındı, yanıt uzunluğu: {len(response)}")
                
                # Log the first 500 characters of the response for debugging
                logger.info(f"Yanıt başlangıcı: {response[:min(500, len(response))]}...")
                
                # Yanıt boş veya çok kısa ise varsayılan yanıta dön
                if len(response) < 50:  # 50 karakterden kısa ise anlamsız yanıt kabul et
                    logger.warning(f"Model çok kısa yanıt döndü ({len(response)} karakter), varsayılan işleme moduna geçiliyor")
                    return self._create_default_cv_response(cv_text=cv_text, error_msg="Model yanıtı çok kısa", raw_response=response)
                
            except Exception as gen_err:
                logger.error(f"Model yanıt üretemedi: {str(gen_err)}")
                return self._create_default_cv_response(error_msg=f"Model yanıt üretemedi: {str(gen_err)}")
                
            # Tüm metinden sadece JSON kısmını çıkarma
            json_content = None
            
            # XML/HTML benzeri etiketleri çıkar
            clean_response = re.sub(r'<[^>]+>', '', response)
            
            # JSON bracket algılama
            json_start = clean_response.find('{')
            json_end = clean_response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_content = clean_response[json_start:json_end]
                logger.info(f"JSON içeriği bulundu, uzunluk: {len(json_content)}")
            else:
                logger.warning(f"JSON formatı bulunamadı! Yanıt: {clean_response[:200]}")
                # CV'den temel bilgileri çıkararak varsayılan yanıt oluştur
                return self._create_default_cv_response(cv_text=cv_text, error_msg="JSON formatı bulunamadı", raw_response=response[:500])
                
            try:
                # JSON stringini düzeltmeye çalış
                json_str = json_content.strip()
                
                # Model çıktısında en yaygın görülen sorunları temizle
                # 1. Tırnak işaretleri
                json_str = re.sub(r'(?<!\\)"', '"', json_str)  # Yanlış tırnak işaretlerini düzelt
                json_str = json_str.replace("'", '"')  # Tek tırnak yerine çift tırnak kullan
                
                # 2. Fazladan yazı veya açıklamaları temizle
                json_str = re.sub(r'```json\s*', '', json_str)  # Markdown json başlangıcını temizle
                json_str = re.sub(r'\s*```', '', json_str)      # Markdown kapanışını temizle
                
                # 3. Virgül sorunlarını düzelt
                json_str = json_str.replace(",\n}", "\n}")
                json_str = json_str.replace(",\n]", "\n]")
                json_str = json_str.replace(",}", "}")
                json_str = json_str.replace(",]", "]")
                
                # 4. JSON yapısını doğru olduğundan emin ol
                if not json_str.startswith('{'): json_str = '{' + json_str.split('{', 1)[1] if '{' in json_str else '{}'
                if not json_str.endswith('}'): json_str = json_str.rsplit('}', 1)[0] + '}' if '}' in json_str else '{}'
                
                # 5. Boş, null ve undefined değerleri temizle
                json_str = re.sub(r':\s*null', ': ""', json_str)  
                json_str = re.sub(r':\s*undefined', ': ""', json_str)
                json_str = re.sub(r':\s*"null"', ': ""', json_str)
                json_str = re.sub(r':\s*"undefined"', ': ""', json_str)
                
                # Fazladan veriyi temizle - line 23 column 1 (char 483) hatasını çözmek için
                # İlk açılan { ile son kapanan } arasındaki kısmı al
                first_brace = json_str.find('{')
                last_brace = json_str.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_str = json_str[first_brace:last_brace+1]
                
                # JSON ayrıştır
                try:
                    # Önce geçerli JSON mu diye kontrol et
                    try:
                        result = json.loads(json_str)
                        logger.info(f"JSON başarıyla ayrıştırıldı, alanlar: {', '.join(result.keys())}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"İlk JSON ayrıştırma denemesi başarısız: {e}")
                        
                        # En son çare - eğer JSON düzeltme başarısız olursa basit şablon oluştur
                        if "kisisel_bilgiler" not in json_str or len(json_str) < 50:
                            logger.warning("JSON içeriği oluşturulamadı, varsayılan işlemeye geçiliyor")
                            return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON formatı oluşturulamadı: {str(e)}")
                        
                        # JSON düzeltmeyi tekrar dene - json_repair kütüphanesi yoksa basit düzeltme yap
                        try:
                            # Çift tırnak sorunu olmadığından emin ol 
                            clean_json = json_str.replace('"', '"').replace('"', '"')
                            result = json.loads(clean_json)
                            logger.info("JSON temizleme sonrası başarıyla ayrıştırıldı")
                            return result
                        except:
                            logger.error("JSON temizleme sonrası da ayrıştırılamadı")
                            return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON ayrıştırma hatası: {str(e)}", raw_response=response[:300])
                except Exception as e:
                    logger.error(f"JSON düzeltme hatası: {str(e)}")
                    return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON düzeltme hatası: {str(e)}", raw_response=response[:300])
            except Exception as e:
                logger.error(f"JSON düzeltme hatası: {str(e)}")
                return self._create_default_cv_response(cv_text=cv_text, error_msg=f"JSON düzeltme hatası: {str(e)}", raw_response=response[:300])
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
        
    def match_cv_with_position(self, cv_data: Dict[str, Any], position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        CV'yi iş pozisyonuyla eşleştirir
        
        Args:
            cv_data (Dict[str, Any]): CV verisi
            position_data (Dict[str, Any]): İş pozisyonu verisi
            
        Returns:
            Dict[str, Any]: Eşleştirme sonuçları
        """
        if self.model is None:
            raise RuntimeError("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            
        # Prompt oluştur
        prompt = self._create_matching_prompt(cv_data, position_data)
        
        # Model yanıtını al
        response = self.generate(prompt, max_new_tokens=1000)
        
        # Yanıtı işle
        return self._parse_matching_response(response)
        
    def _create_matching_prompt(self, cv_data: Dict[str, Any], position_data: Dict[str, Any]) -> str:
        """Eşleştirme promptu oluşturur"""
        cv_json = json.dumps(cv_data, indent=2, ensure_ascii=False)
        position_json = json.dumps(position_data, indent=2, ensure_ascii=False)
        
        return f"""
        # Görev: CV-Pozisyon Eşleştirme
        
        Aşağıdaki CV verisini ve iş pozisyonu verisini karşılaştır ve eşleşme skorunu belirle.
        
        ## CV Verisi:
        ```json
        {cv_json}
        ```
        
        ## Pozisyon Verisi:
        ```json
        {position_json}
        ```
        
        Aşağıdaki kriterlere göre değerlendirme yap:
        - Beceri eşleşmesi
        - Deneyim süresi ve türü
        - Eğitim seviyesi ve alanı
        - Dil becerileri
        - Sertifikalar
        
        0 ile 1 arasında bir eşleşme skoru belirle ve gerekçelerini açıkla.
        
        JSON formatında yanıt ver:
        ```json
        {
          "match_score": 0.85,
          "category_scores": {
            "skills": 0.9,
            "experience": 0.8,
            "education": 0.85,
            "languages": 0.7,
            "certifications": 0.75
          },
          "strengths": ["Beceri 1", "Beceri 2"],
          "weaknesses": ["Zayıf alan 1", "Zayıf alan 2"],
          "recommendations": ["Öneri 1", "Öneri 2"]
        }
        ```
        """
        
    def _parse_matching_response(self, response: str) -> Dict[str, Any]:
        """Eşleştirme yanıtını ayrıştırır"""
        try:
            # JSON yanıtını ayıkla
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response[json_start:json_end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Tek tırnaklı değerleri çift tırnaklı yap
                    corrected_json = json_str.replace("'", '"')
                    # Virgül düzeltmeleri
                    corrected_json = corrected_json.replace(",\n}", "\n}")
                    corrected_json = corrected_json.replace(",\n]", "\n]")
                    return json.loads(corrected_json)
                    
            return {"error": "JSON yanıtı bulunamadı", "raw_response": response}
        except Exception as e:
            return {"error": str(e), "raw_response": response}
        
    def __del__(self):
        """Kaynakları temizler"""
        if self.model is not None:
            del self.model 