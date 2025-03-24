#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import logging
import os
import sys
from typing import Dict, Any, List, Optional
import datetime
import json

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('cv_parser')

# OllamaConnector'a erişebilmek için ana klasörü Python yoluna ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from ollama_connector import OllamaConnector
except ImportError:
    logger.warning("OllamaConnector import edilemedi, AI analizi devre dışı")
    OllamaConnector = None

class CVParser:
    """CV'den önemli bilgileri ayıklar ve ön analiz yapar"""
    
    def __init__(self, cv_text: str):
        """
        CV Parser sınıfını başlatır
        
        Args:
            cv_text (str): CV metni
        """
        self.cv_text = cv_text
        self.lines = cv_text.split('\n')
        self.clean_lines = [line.strip() for line in self.lines if line.strip()]
        self.text_blocks = self._create_text_blocks()
        self.ollama = self._initialize_ollama()
        logger.info(f"CV Parser başlatıldı: {len(self.clean_lines)} satır, {len(self.text_blocks)} blok")
    
    def _initialize_ollama(self) -> Optional[OllamaConnector]:
        """Ollama bağlantısını başlatır"""
        # OllamaConnector sınıfı mevcut değilse
        if OllamaConnector is None:
            logger.warning("OllamaConnector sınıfı yüklenemedi, AI analizi devre dışı bırakıldı")
            return None
            
        try:
            # Doğrudan llama3:8b modelini kullanalım
            connector = OllamaConnector(default_model="llama3:8b")
            if connector.is_available():
                if connector.load_model():
                    logger.info(f"Ollama bağlantısı başarılı, model: {connector.default_model}")
                    return connector
                    
            # Eğer llama3:8b yüklenemezse diğer modeli deneyelim
            alt_model = "deepseek-coder:6.7b-instruct-q4_K_M"
            logger.info(f"'{alt_model}' modeli deneniyor...")
            connector = OllamaConnector(default_model=alt_model)
            if connector.is_available() and connector.load_model():
                logger.info(f"Ollama alternatif model yüklendi: {alt_model}")
                return connector
            
            # Hiçbir model çalışmazsa
            logger.warning("Hiçbir model yüklenemedi, geleneksel CV analizi kullanılacak")
            return None
        except Exception as e:
            logger.error(f"Ollama bağlantısı sırasında hata: {str(e)}")
            return None
    
    def _create_text_blocks(self) -> List[str]:
        """Metin bloklarını oluşturur (ardışık boş olmayan satırlar)"""
        blocks = []
        current_block = []
        
        for line in self.lines:
            if line.strip():
                current_block.append(line.strip())
            elif current_block:
                blocks.append(" ".join(current_block))
                current_block = []
        
        # Son bloğu ekle
        if current_block:
            blocks.append(" ".join(current_block))
        
        return blocks
    
    def extract_personal_info(self) -> Dict[str, str]:
        """Kişisel bilgileri ayıklar"""
        personal_info = {
            "isim": "Belirtilmemiş",
            "email": "Belirtilmemiş",
            "telefon": "Belirtilmemiş",
            "lokasyon": "Belirtilmemiş",
            "linkedin": "Belirtilmemiş",
            "website": "Belirtilmemiş"
        }
        
        # İsim için regex
        # CV'nin en başında veya başlık bölümünde geçen büyük harfle başlayan kelimeler (1-3 kelime) isim olabilir
        # İsim tipik olarak CV'nin başında tek başına bir satırda veya başlıkta yer alır
        name_pattern = r'^\s*([A-Z][a-zçğıöşüÇĞİÖŞÜ]+(?:\s+[A-Z][a-zçğıöşüÇĞİÖŞÜ]+){0,2})\s*$'
        name_matches = re.findall(name_pattern, self.cv_text, re.MULTILINE)
        
        if name_matches:
            # İlk eşleşmeyi al
            personal_info["isim"] = name_matches[0].strip()
        else:
            # İkinci bir deneme: Başlık bölümünde veya ilk birkaç satırda isim aramaya çalış
            first_lines = "\n".join(self.clean_lines[:10])  # İlk 10 satıra bak
            name_pattern2 = r'\b([A-Z][a-zçğıöşüÇĞİÖŞÜ]+(?:\s+[A-Z][a-zçğıöşüÇĞİÖŞÜ]+){1,2})\b'
            name_matches2 = re.findall(name_pattern2, first_lines)
            
            if name_matches2:
                # En uzun eşleşmeyi seç (daha çok kelimeden oluşan isimler öncelikli)
                sorted_names = sorted(name_matches2, key=len, reverse=True)
                
                # İsim olması olası olmayan kelimeleri filtreleme
                filtered_names = [n for n in sorted_names if n.lower() not in [
                    "curriculum vitae", "resume", "cv", "özgeçmiş", "profile", "profil", 
                    "personal information", "kişisel bilgiler", "contact", "iletişim"
                ]]
                
                if filtered_names:
                    personal_info["isim"] = filtered_names[0].strip()
                
        # Email için regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, self.cv_text)
        if email_matches:
            personal_info["email"] = email_matches[0].lower()
        
        # Telefon numarası için regex
        phone_patterns = [
            # Uluslararası formatlar: +90 555 123 4567, +905551234567
            r'(?:\+\d{1,3}[-\.\s]?)?(?:\(?\d{3}\)?[-\.\s]?)?(?:\d{3}[-\.\s]?)(?:\d{2}[-\.\s]?)(?:\d{2})',
            # Türkiye formatı: 0555 123 45 67, 0555-123-4567
            r'0\s*\d{3}\s*[-\s]?\d{3}\s*[-\s]?\d{2}\s*[-\s]?\d{2}',
            # Diğer formatlar: 555 123 45 67, 5551234567
            r'\b\d{3}\s*[-\s]?\d{3}\s*[-\s]?\d{2}\s*[-\s]?\d{2}\b'
        ]
        
        for pattern in phone_patterns:
            phone_matches = re.findall(pattern, self.cv_text)
            if phone_matches:
                # Boşlukları temizle ve telefon numarasını düzenle
                phone = phone_matches[0]
                # Sadece sayıları ve artı işaretini koru
                clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
                
                # Düzgün formatlama için
                if clean_phone.startswith('+'):
                    # Uluslararası format
                    if len(clean_phone) >= 10:
                        personal_info["telefon"] = clean_phone
                        break
                elif clean_phone.startswith('0'):
                    # Türkiye formatı
                    if len(clean_phone) >= 11:
                        personal_info["telefon"] = clean_phone
                        break
                else:
                    # Kısa format, muhtemelen alan kodu olmadan
                    if len(clean_phone) >= 10:
                        personal_info["telefon"] = clean_phone
                        break
        
        # Konum/Lokasyon için regex
        # Genellikle şehir isimleri veya "Location: City" formatında
        location_patterns = [
            r'(?:lokasyon|location|address|adres|city|şehir|country|ülke)[:\s]+([^\n,\.;]{3,40})',
            # Şehir ve ülke isimleri
            r'\b(İstanbul|Ankara|İzmir|Bursa|Antalya|Adana|Turkey|Türkiye|United States|USA|England|UK|Germany|France)\b'
        ]
        
        for pattern in location_patterns:
            location_matches = re.findall(pattern, self.cv_text, re.IGNORECASE)
            if location_matches:
                location = location_matches[0].strip()
                # Anlamsız kelimeler veya çok kısa/uzun konumları filtrele
                if (len(location) > 3 and len(location) < 40 and not any(x in location.lower() for x in 
                                                                       ["email", "phone", "telefon", "@", "www", "http", "position", "role"])):
                    personal_info["lokasyon"] = location
                    break
        
        # LinkedIn profili için regex
        linkedin_patterns = [
            r'(?:linkedin\.com/in/|linkedin:)([a-zA-Z0-9_-]+)',
            r'(?:linkedin|in)[\s:/]+([^\s/]+)'
        ]
        
        for pattern in linkedin_patterns:
            linkedin_matches = re.findall(pattern, self.cv_text, re.IGNORECASE)
            if linkedin_matches:
                profile = linkedin_matches[0].strip("/@: ")
                if len(profile) > 3:  # Çok kısa eşleşmeleri filtrele
                    personal_info["linkedin"] = profile
                    break
        
        # Kişisel web sitesi için regex
        website_patterns = [
            r'(?:website|site|web|www)[:\s]+([a-zA-Z0-9][a-zA-Z0-9-]*\.(?:[a-zA-Z0-9-]+\.)*[a-zA-Z]{2,})',
            r'\b(?:https?://)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]*\.(?:[a-zA-Z0-9-]+\.)*[a-zA-Z]{2,})'
        ]
        
        for pattern in website_patterns:
            website_matches = re.findall(pattern, self.cv_text, re.IGNORECASE)
            if website_matches:
                website = website_matches[0].strip()
                # linkedin ve yaygın paylaşım sitelerini hariç tut
                if (len(website) > 5 and not any(x in website.lower() for x in 
                                             ["linkedin", "github", "twitter", "facebook", "instagram"])):
                    personal_info["website"] = website
                    break
        
        return personal_info
    
    def extract_skills(self) -> Dict[str, List[str]]:
        """Becerileri ayıklar: teknik beceriler, yazılım dilleri, diller, soft beceriler"""
        skills = {
            "teknik_beceriler": [],
            "yazilim_dilleri": [],
            "diller": [],
            "soft_beceriler": []
        }
        
        # Beceriler bölümünü bul
        skill_section_patterns = [
            r'(?:SKILLS|TECHNICAL SKILLS|BECERİLER|TEKNİK BECERİLER)[\s:]*([^#]*?)(?:(?:#|\n\s*\n\s*[A-Z]{2,}|\Z))',
            r'(?:PROGRAMMING LANGUAGES|YAZILIM DİLLERİ)[\s:]*([^#]*?)(?:(?:#|\n\s*\n\s*[A-Z]{2,}|\Z))',
            r'(?:LANGUAGES|DİLLER|YABANCI DİLLER)[\s:]*([^#]*?)(?:(?:#|\n\s*\n\s*[A-Z]{2,}|\Z))'
        ]
        
        skill_texts = []
        for pattern in skill_section_patterns:
            skill_match = re.search(pattern, self.cv_text, re.IGNORECASE | re.DOTALL)
            if skill_match:
                skill_texts.append(skill_match.group(1).strip())
        
        # Yaygın programlama dilleri listesi
        programming_languages = [
            'Python', 'Java', 'C', 'C++', 'C#', 'JavaScript', 'TypeScript', 'PHP', 'Ruby', 'Swift', 'Kotlin',
            'Go', 'Rust', 'Scala', 'Perl', 'R', 'MATLAB', 'Dart', 'Assembly', 'SQL', 'HTML', 'CSS', 'XML',
            'Shell', 'Bash', 'PowerShell', 'Haskell', 'Julia', 'Fortran', 'COBOL', 'Lua', 'VBA', 'Delphi'
        ]
        
        # Yaygın frameworkler ve teknolojiler
        technologies = [
            'Django', 'Flask', 'Spring', 'React', 'Angular', 'Vue', 'Laravel', 'ASP.NET', 'Express', 'Node.js',
            'TensorFlow', 'PyTorch', 'Keras', 'Pandas', 'NumPy', 'scikit-learn', 'Docker', 'Kubernetes', 'AWS',
            'Azure', 'GCP', 'Git', 'REST', 'GraphQL', 'Microservices', 'CI/CD', 'Jenkins', 'Travis CI',
            'Bootstrap', 'jQuery', 'Redux', 'Next.js', 'Gatsby', 'FastAPI', 'Symfony', 'Rails', 'Unity', 'Xamarin',
            'Flutter', 'React Native', 'MongoDB', 'MySQL', 'PostgreSQL', 'SQLite', 'Oracle', 'Firebase', 'Redis',
            'Kafka', 'RabbitMQ', 'gRPC', 'WebSocket', 'WebRTC', 'OAuth', 'JWT', 'SAML', 'OpenCV'
        ]
        
        # AI ve ML alanında yaygın teknolojiler
        ai_ml_technologies = [
            'AI', 'Artificial Intelligence', 'Yapay Zeka', 'Machine Learning', 'Makine Öğrenmesi',
            'Deep Learning', 'Derin Öğrenme', 'Computer Vision', 'Görüntü İşleme', 'NLP', 
            'Natural Language Processing', 'Doğal Dil İşleme', 'Neural Networks', 'Sinir Ağları',
            'Reinforcement Learning', 'Pekiştirmeli Öğrenme', 'Data Science', 'Veri Bilimi',
            'Big Data', 'Büyük Veri', 'Analytics', 'Analitik', 'Predictive Modeling', 'Tahminleme',
            'Classification', 'Sınıflandırma', 'Regression', 'Regresyon', 'Clustering', 'Kümeleme',
            'Data Mining', 'Veri Madenciliği', 'ETL', 'Data Warehousing', 'Veri Ambarı',
            'Feature Engineering', 'Öznitelik Mühendisliği', 'Time Series Analysis', 'Zaman Serisi Analizi',
            'Recommender Systems', 'Öneri Sistemleri', 'Pattern Recognition', 'Örüntü Tanıma',
            'Statistical Analysis', 'İstatistiksel Analiz', 'Data Visualization', 'Veri Görselleştirme'
        ]
        
        # Teknolojiler listesine AI/ML teknolojilerini ekle
        technologies.extend(ai_ml_technologies)
        
        # Yaygın diller
        languages = [
            'İngilizce', 'English', 'Almanca', 'German', 'Deutsch', 'Fransızca', 'French', 'Français',
            'İspanyolca', 'Spanish', 'Español', 'İtalyanca', 'Italian', 'Italiano', 'Rusça', 'Russian',
            'Japonca', 'Japanese', 'Çince', 'Chinese', 'Arapça', 'Arabic', 'Portekizce', 'Portuguese',
            'Türkçe', 'Turkish', 'Korece', 'Korean', 'Hintçe', 'Hindi', 'Lehçe', 'Polish'
        ]
        
        # Yumuşak beceriler
        soft_skills = [
            'iletişim', 'communication', 'takım çalışması', 'team work', 'liderlik', 'leadership',
            'analitik', 'analytical', 'problem çözme', 'problem solving', 'yaratıcılık', 'creativity',
            'uyum', 'adaptability', 'zaman yönetimi', 'time management', 'eleştirel düşünce',
            'critical thinking', 'detay odaklı', 'detail-oriented', 'müzakere', 'negotiation',
            'multitasking', 'çok yönlü çalışma', 'sunum', 'presentation', 'raporlama', 'reporting',
            'stratejik düşünme', 'strategic thinking', 'proje yönetimi', 'project management',
            'risk yönetimi', 'risk management', 'karar verme', 'decision making'
        ]
        
        # Dil ve seviye kalıpları
        language_level_pattern = f"({'|'.join(languages)})\\s*[-:]?\\s*(A1|A2|B1|B2|C1|C2|başlangıç|orta|ileri|akıcı|native|ana dil|Advanced|Intermediate|Beginner|Fluent)"
        
        # Beceri bölümlerini filtrelemek için bilinen başlıklar
        known_section_headers = [
            'skills', 'beceriler', 'interests', 'references', 'education', 'experience', 
            'contact', 'profile', 'projects', 'certificates', 'summary'
        ]
        
        # Önce beceri bölümlerini işle
        for skill_text in skill_texts:
            # Satırlara ayır ve her bir satırı işle
            skill_lines = skill_text.split('\n')
            for line in skill_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Dil seviyesini kontrol et
                lang_level_matches = re.findall(language_level_pattern, line, re.IGNORECASE)
                if lang_level_matches:
                    for lang, level in lang_level_matches:
                        language_with_level = f"{lang} ({level})"
                        if language_with_level not in skills["diller"]:
                            skills["diller"].append(language_with_level)
                    continue
                
                # Başlıkları beceri olarak saymayı engellemek için kontrol
                is_section_header = False
                for header in known_section_headers:
                    if header.lower() in line.lower():
                        is_section_header = True
                        break
                
                if is_section_header:
                    continue
                
                # Yazılım dili veya teknoloji mi?
                added_to_a_category = False
                for prog_lang in programming_languages:
                    if re.search(r'\b' + re.escape(prog_lang) + r'\b', line, re.IGNORECASE):
                        # Case'i düzelt (Python -> Python, python -> Python)
                        correct_case = prog_lang
                        if correct_case not in skills["yazilim_dilleri"]:
                            skills["yazilim_dilleri"].append(correct_case)
                            added_to_a_category = True
                
                for tech in technologies:
                    if re.search(r'\b' + re.escape(tech) + r'\b', line, re.IGNORECASE):
                        # Case'i düzelt
                        correct_case = tech
                        if correct_case not in skills["teknik_beceriler"]:
                            skills["teknik_beceriler"].append(correct_case)
                            added_to_a_category = True
                
                # Soft beceriler
                for soft_skill in soft_skills:
                    if re.search(r'\b' + re.escape(soft_skill) + r'\b', line, re.IGNORECASE):
                        # İlk harfi büyük yap
                        capitalized = soft_skill.capitalize()
                        if capitalized not in skills["soft_beceriler"]:
                            skills["soft_beceriler"].append(capitalized)
                            added_to_a_category = True
                
                # Eğer hiçbir kategoriye eklenmemiş ve çok uzun değilse, teknik beceri olabilir
                if not added_to_a_category and len(line) < 50:
                    # Virgülle ayrılmış beceriler olabilir
                    skills_in_line = [skill.strip() for skill in line.split(',')]
                    for skill_item in skills_in_line:
                        # Çok kısa veya uzun becerileri filtrele
                        if 2 <= len(skill_item) <= 30 and skill_item not in skills["teknik_beceriler"]:
                            # Başlık olabilecek ifadeleri filtrele
                            is_header = any(header.lower() in skill_item.lower() for header in known_section_headers)
                            if not is_header:
                                skills["teknik_beceriler"].append(skill_item)
        
        # Eğer beceri bölümü bulunamadıysa, tüm metin içinde ara
        if not any(skills.values()):
            # Programlama dilleri
            for prog_lang in programming_languages:
                matches = re.findall(r'\b' + re.escape(prog_lang) + r'\b', self.cv_text, re.IGNORECASE)
                if matches:
                    if prog_lang not in skills["yazilim_dilleri"]:
                        skills["yazilim_dilleri"].append(prog_lang)
            
            # Teknolojiler
            for tech in technologies:
                matches = re.findall(r'\b' + re.escape(tech) + r'\b', self.cv_text, re.IGNORECASE)
                if matches:
                    if tech not in skills["teknik_beceriler"]:
                        skills["teknik_beceriler"].append(tech)
            
            # Dil seviyeleri
            language_level_matches = re.findall(language_level_pattern, self.cv_text, re.IGNORECASE)
            for lang, level in language_level_matches:
                language_with_level = f"{lang} ({level})"
                if language_with_level not in skills["diller"]:
                    skills["diller"].append(language_with_level)
            
            # Soft beceriler
            for soft_skill in soft_skills:
                matches = re.findall(r'\b' + re.escape(soft_skill) + r'\b', self.cv_text, re.IGNORECASE)
                if matches:
                    capitalized_skill = soft_skill.capitalize()
                    if capitalized_skill not in skills["soft_beceriler"]:
                        skills["soft_beceriler"].append(capitalized_skill)
        
        # Projelerden ve deneyimlerden beceri çıkarımı
        self._extract_skills_from_projects_and_experience(skills)
        
        return skills
        
    def _extract_skills_from_projects_and_experience(self, skills: Dict[str, List[str]]) -> None:
        """Proje açıklamaları ve deneyimlerden beceri ve teknoloji çıkarımı yapar"""
        # Yaygın AI ve yazılım geliştirme terimleri
        ai_terms = [
            'artificial intelligence', 'yapay zeka', 'machine learning', 'makine öğrenmesi',
            'deep learning', 'neural network', 'computer vision', 'görüntü işleme',
            'nlp', 'natural language processing', 'doğal dil işleme', 'object detection',
            'nesne tanıma', 'classification', 'sınıflandırma', 'regression', 'regresyon',
            'data science', 'veri bilimi', 'analytics', 'analitik', 'algorithm', 'algoritma',
            'sentiment analysis', 'duygu analizi', 'automation', 'otomasyon'
        ]
        
        # Yaygın programlama dilleri
        programming_terms = [
            'python', 'java', 'javascript', 'c++', 'c#', 'typescript', 'php', 'ruby', 'go',
            'swift', 'kotlin', 'scala', 'perl', 'sql', 'html', 'css'
        ]
        
        # Metni analiz et
        all_text = self.cv_text.lower()
        
        # AI terimleri için
        for term in ai_terms:
            if term in all_text:
                # İlk harfleri büyüt
                capitalized_term = ' '.join(word.capitalize() for word in term.split())
                if capitalized_term not in skills["teknik_beceriler"]:
                    skills["teknik_beceriler"].append(capitalized_term)
        
        # Programlama dilleri için
        for term in programming_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', all_text):
                # Python -> Python, python -> Python, vs.
                capitalized_term = term.capitalize()
                if capitalized_term not in skills["yazilim_dilleri"]:
                    skills["yazilim_dilleri"].append(capitalized_term)
    
    def extract_education(self) -> List[Dict[str, str]]:
        """Eğitim bilgilerini ayıklar"""
        education_list = []
        
        # Eğitim bölümünü bul
        education_section_pattern = r'(?:EDUCATION|E[ĞG]İTİM|EDUCATIONAL BACKGROUND)[\s:]*([^#]*?)(?:(?:#|\n\s*\n\s*[A-Z]{2,}|\Z))'
        education_section_match = re.search(education_section_pattern, self.cv_text, re.IGNORECASE | re.DOTALL)
        
        education_text = ""
        if education_section_match:
            education_text = education_section_match.group(1).strip()
        
        # Eğitim bilgilerini ayıkla
        if education_text:
            # İlk önce paragraf veya madde işaretleriyle ayrılmış blokları ayır
            education_blocks = re.split(r'\n\s*[-•]\s+|\n\n+', education_text)
            
            for block in education_blocks:
                if len(block.strip()) < 10:  # Çok kısa blokları atla
                    continue
                
                # Üniversite/okul ismi için kalıplar
                university_patterns = [
                    r'((?:üniversite|university|college|school|institut|akademi|academy)[^\n,.;]*)',
                    r'([^\n,.;]*(?:üniversitesi|üniversite|university|college|school|institute|academy))'
                ]
                
                # Bölüm ve derece için kalıplar
                degree_patterns = [
                    r'((?:lisans|bachelor|master|phd|doktora|mba|m\.sc|b\.sc|yüksek lisans|undergraduate|graduate|degree|diploma|certificate)[^\n,.;]*)',
                    r'([^\n,.;]*(?:mühendisliği|engineering|science|bilim|bölümü|department|program))'
                ]
                
                # Mezuniyet tarihi için kalıplar
                graduation_pattern = r'(\d{4}\s*(?:-|–|to)\s*(?:\d{4}|present|günümüz|devam|current|ongoing|now))'
                
                # Üç bilgi için de ayrı kayıtlar tut
                uni_name = "Belirtilmemiş"
                degree_name = "Belirtilmemiş"
                graduation_date = "Belirtilmemiş"
                
                # Üniversite
                for pattern in university_patterns:
                    uni_match = re.search(pattern, block, re.IGNORECASE)
                    if uni_match:
                        uni_name = uni_match.group(1).strip()
                        break
                
                # Derece/Bölüm
                for pattern in degree_patterns:
                    degree_match = re.search(pattern, block, re.IGNORECASE)
                    if degree_match:
                        degree_name = degree_match.group(1).strip()
                        break
                
                # Mezuniyet tarihi
                grad_match = re.search(graduation_pattern, block)
                if grad_match:
                    graduation_date = grad_match.group(1).strip()
                
                # Üniversite veya bölüm bilgisinden en az biri varsa ekle
                if uni_name != "Belirtilmemiş" or degree_name != "Belirtilmemiş":
                    education_list.append({
                        "okul": uni_name,
                        "bolum": degree_name,
                        "mezuniyet": graduation_date
                    })
        
        # Eğer eğitim bölümü bulunamadıysa, tüm metni kontrol et
        if not education_list:
            # Üniversite/okul isimleri için daha geniş bir liste
            university_keywords = [
                "üniversite", "university", "college", "school", "institut", "akademi", "academy", 
                "lisesi", "high school", "fakülte", "faculty", "yüksekokul"
            ]
            
            # Kapsamlı bir arama için yeni bir yaklaşım
            # Tüm metindeki olası eğitim kurumlarını kontrol et
            for block in self.text_blocks:
                # Bu blok bir eğitim kurumu içeriyor olabilir mi?
                contains_university = False
                for keyword in university_keywords:
                    if keyword.lower() in block.lower():
                        contains_university = True
                        break
                
                if not contains_university:
                    continue
                
                lines = block.split('\n')
                edu_entry = {
                    "okul": "Belirtilmemiş",
                    "bolum": "Belirtilmemiş",
                    "mezuniyet": "Belirtilmemiş"
                }
                
                # Üniversite ismi için genel kalıp
                uni_pattern = r'([A-Za-z\sıüğşçö]+(?:University|Üniversitesi|College|Institute|Academy|Akademi|School))'
                uni_match = re.search(uni_pattern, block, re.IGNORECASE)
                if uni_match:
                    edu_entry["okul"] = uni_match.group(1).strip()
                
                # Mezuniyet tarihi
                grad_pattern = r'(\d{4}\s*(?:-|–|to)\s*(?:\d{4}|present|günümüz|devam|current|ongoing|now))'
                grad_match = re.search(grad_pattern, block)
                if grad_match:
                    edu_entry["mezuniyet"] = grad_match.group(1).strip()
                
                # Bölüm/Derece - eğer içinde "engineering", "science", "mühendislik", "bilim" gibi kelimeler geçiyorsa
                degree_pattern = r'((?:Bachelor|Master|PhD|Lisans|Undergraduate|Graduate|Doktora|Yüksek Lisans)[^\n,\.;]*)'
                department_pattern = r'([^\n,\.;]*(?:Engineering|Mühendisliği|Science|Bilim|Computer|Bilgisayar|Economics|Ekonomi)[^\n,\.;]*)'
                
                # Derece
                degree_match = re.search(degree_pattern, block, re.IGNORECASE)
                if degree_match:
                    edu_entry["bolum"] = degree_match.group(1).strip()
                else:
                    # Bölüm
                    dept_match = re.search(department_pattern, block, re.IGNORECASE)
                    if dept_match:
                        edu_entry["bolum"] = dept_match.group(1).strip()
                
                # Eğer en azından okul bilgisi elde edilmişse listeye ekle
                if edu_entry["okul"] != "Belirtilmemiş":
                    education_list.append(edu_entry)
        
        # Sonuçları temizle - çok kısa veya anlamsız değerleri düzelt
        for entry in education_list:
            # Çok kısa alanları "Belirtilmemiş" olarak işaretle
            for key in ["okul", "bolum"]:
                if len(entry[key]) < 3 or entry[key] in ["of", "in", "at", "ve", "and"]:
                    entry[key] = "Belirtilmemiş"
        
        # Eğitim bilgileri için kalıplar
        university_pattern = r'((?:üniversite|university|college|okul|school|institute)[^\n,.;]*)'
        department_pattern = r'((?:bölüm|department|faculty|fakülte)[^\n,.;]*)'
        degree_pattern = r'((?:lisans|yüksek lisans|doktora|bachelor|master|phd|bs|ba|ms|ma)[^\n,.;]*)'
        years_pattern = r'(\d{4}\s*(?:-|–|to)\s*(?:\d{4}|present|günümüz|devam|current|ongoing|now)|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})'
        
        # Metin bloğunda üniversite adı geçiyorsa
        if "university" in education_text.lower() or "üniversite" in education_text.lower():
            # Blok içindeki satırları ayır
            edu_lines = education_text.split('\n')
            current_edu = {
                "okul": "Belirtilmemiş",
                "bolum": "Belirtilmemiş",
                "derece": "Belirtilmemiş",
                "tarih": "Belirtilmemiş"
            }
            
            # Satırları dolaş
            for line in edu_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Üniversite adı
                uni_match = re.search(university_pattern, line, re.IGNORECASE)
                if uni_match or "university" in line.lower() or "üniversite" in line.lower():
                    # Yeni eğitim girişi başlat
                    if current_edu["okul"] != "Belirtilmemiş" and (current_edu["tarih"] != "Belirtilmemiş" or current_edu["bolum"] != "Belirtilmemiş"):
                        education_list.append(current_edu)
                        current_edu = {
                            "okul": "Belirtilmemiş",
                            "bolum": "Belirtilmemiş",
                            "derece": "Belirtilmemiş",
                            "tarih": "Belirtilmemiş"
                        }
                    
                    # Bu satırı üniversite adı olarak al
                    if uni_match:
                        current_edu["okul"] = uni_match.group(1).strip()
                    else:
                        # Üniversite kelimesi içeren satır
                        current_edu["okul"] = line
                
                # Bölüm adı
                dept_match = re.search(department_pattern, line, re.IGNORECASE)
                if dept_match or "department" in line.lower() or "bölüm" in line.lower():
                    current_edu["bolum"] = dept_match.group(1).strip() if dept_match else line
                
                # Derece/seviye
                deg_match = re.search(degree_pattern, line, re.IGNORECASE)
                if deg_match or any(degree in line.lower() for degree in ["bachelor", "master", "phd", "lisans", "doktora"]):
                    current_edu["derece"] = deg_match.group(1).strip()
                
                # Tarih aralığı
                year_match = re.search(years_pattern, line)
                if year_match:
                    current_edu["tarih"] = year_match.group(1).strip()
            
            # Son giriş eklenmemiş olabilir
            if current_edu["okul"] != "Belirtilmemiş" and (current_edu["tarih"] != "Belirtilmemiş" or current_edu["bolum"] != "Belirtilmemiş"):
                education_list.append(current_edu)
        
        # Eğer doğrudan eğitim bölümü bulunamadıysa, metin bloklarına bak
        if not education_list:
            for block in self.text_blocks:
                # Üniversite veya okul adı geçiyor mu?
                uni_match = re.search(university_pattern, block, re.IGNORECASE)
                year_match = re.search(years_pattern, block)
                
                if (uni_match or "university" in block.lower() or "üniversite" in block.lower()) and year_match:
                    edu_entry = {
                        "okul": "Belirtilmemiş",
                        "bolum": "Belirtilmemiş",
                        "derece": "Belirtilmemiş",
                        "tarih": "Belirtilmemiş"
                    }
                    
                    # Üniversite adı
                    if uni_match:
                        edu_entry["okul"] = uni_match.group(1).strip()
                    else:
                        # Üniversite kelimesi içeren blok - ilgili satırı bul
                        lines = block.split('\n')
                        for line in lines:
                            if "university" in line.lower() or "üniversite" in line.lower():
                                edu_entry["okul"] = line.strip()
                                break
                    
                    # Bölüm adı
                    dept_match = re.search(department_pattern, block, re.IGNORECASE)
                    if dept_match:
                        edu_entry["bolum"] = dept_match.group(1).strip()
                    
                    # Derece/seviye
                    deg_match = re.search(degree_pattern, block, re.IGNORECASE)
                    if deg_match:
                        edu_entry["derece"] = deg_match.group(1).strip()
                    
                    # Tarih aralığı
                    if year_match:
                        edu_entry["tarih"] = year_match.group(1).strip()
                    
                    # Eğer en az okul ve tarih bilgisi varsa listeye ekle
                    if edu_entry["okul"] != "Belirtilmemiş" and edu_entry["tarih"] != "Belirtilmemiş":
                        education_list.append(edu_entry)
        
        return education_list
    
    def extract_experience(self) -> List[Dict[str, Any]]:
        """İş deneyimlerini ayıklar"""
        experience_list = []
        
        # İş deneyimi bölümünü bul
        experience_section_pattern = r'(?:WORK EXPERIENCE|İŞ DENEYİMİ|DENEYİM|TECRÜBE|EXPERIENCE)[\s:]*([^#]*?)(?:(?:#|\n\s*\n\s*[A-Z]{2,}|\Z))'
        experience_section_match = re.search(experience_section_pattern, self.cv_text, re.IGNORECASE | re.DOTALL)
        
        experience_text = ""
        if experience_section_match:
            experience_text = experience_section_match.group(1).strip()
        
        # İş bilgileri için kalıplar
        company_pattern = r'((?:şirket|company|firma|corporation|inc\.|ltd\.|limited|a\.ş\.|gmbh)[^\n,.;]*)'
        position_pattern = r'((?:pozisyon|position|role|görev|title|engineer|developer|manager|director|consultant)[^\n,.;]*)'
        years_pattern = r'(\d{4}\s*(?:-|–|to)\s*(?:\d{4}|present|günümüz|devam|current|ongoing|now|Present)|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}(?:\s*-\s*(?:Present|Current|Now|Ongoing|[A-Z][a-z]+\s+\d{4}))?)'
        
        # AI ve yazılım pozisyonları için kalıplar
        ai_positions = [
            r'(?:AI|Artificial Intelligence)\s*(?:Engineer|Developer|Specialist|Expert)',
            r'(?:Machine Learning|ML)\s*(?:Engineer|Developer|Specialist|Expert)',
            r'(?:Data|NLP)\s*(?:Scientist|Engineer|Analyst)',
            r'(?:Software|Backend|Frontend|Full Stack)\s*(?:Engineer|Developer)',
            r'(?:Computer Vision|CV)\s*(?:Engineer|Developer|Specialist)',
            r'(?:Yapay Zeka|YZ)\s*(?:Mühendisi|Uzmanı|Geliştiricisi)',
            r'(?:Veri|Bilgi)\s*(?:Bilimci|Mühendisi|Analisti)'
        ]
        
        # Metin bloğunda şirket adı geçiyorsa
        if experience_text:
            # İlk önce çizgi veya noktalı çizgi ile ayrılmış blokları ayır
            experience_blocks = re.split(r'\n\s*[-•]\s+|\n\n+', experience_text)
            
            for block in experience_blocks:
                if len(block.strip()) < 10:  # Çok kısa blokları atla
                    continue
                    
                lines = block.split('\n')
                exp_entry = {
                    "sirket": "Belirtilmemiş",
                    "pozisyon": "Belirtilmemiş",
                    "tarih": "Belirtilmemiş",
                    "sorumluluklar": []
                }
                
                # Şirket adı ve pozisyon tipik olarak ilk iki satırdadır
                for i, line in enumerate(lines[:4]):  # İlk 4 satıra bak
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Tarih aralığı
                    year_match = re.search(years_pattern, line)
                    if year_match and exp_entry["tarih"] == "Belirtilmemiş":
                        exp_entry["tarih"] = year_match.group(1).strip()
                        # Satırdaki tarih kısmını kaldır ve kalan metni şirket/pozisyon olarak değerlendir
                        remaining_text = line.replace(year_match.group(1), "").strip()
                        if remaining_text and exp_entry["sirket"] == "Belirtilmemiş":
                            # Tarih çıkarıldıktan sonra kalan metin varsa şirket adı olabilir
                            exp_entry["sirket"] = remaining_text.strip(" -|•")
                        continue
                        
                    # Şirket adı
                    company_match = re.search(company_pattern, line, re.IGNORECASE)
                    
                    # Tipik olarak ilk satır şirket, ikinci satır pozisyon olabilir
                    if i == 0 and exp_entry["sirket"] == "Belirtilmemiş":
                        if company_match:
                            exp_entry["sirket"] = company_match.group(1).strip()
                        else:
                            # Pattern uymadıysa, ilk satırı şirket kabul et
                            exp_entry["sirket"] = line
                    elif i == 1 and exp_entry["pozisyon"] == "Belirtilmemiş":
                        position_match = re.search(position_pattern, line, re.IGNORECASE)
                        if position_match:
                            exp_entry["pozisyon"] = position_match.group(1).strip()
                        else:
                            exp_entry["pozisyon"] = line
                
                # Pozisyon için AI ve yazılım pozisyonlarını kontrol et
                if exp_entry["pozisyon"] == "Belirtilmemiş":
                    for pos_pattern in ai_positions:
                        pos_match = re.search(pos_pattern, block, re.IGNORECASE)
                        if pos_match:
                            exp_entry["pozisyon"] = pos_match.group(0).strip()
                            break
                
                # Sorumluluklar listesi
                responsibilities = []
                # Bullet points işaretlerini ara
                bullet_points = re.findall(r'[•\-]\s+(.*?)(?:$|\n)', block)
                if bullet_points:
                    responsibilities = [bp.strip() for bp in bullet_points]
                else:
                    # Madde işareti yoksa, cümleleri al
                    sentences = re.split(r'(?<=[.!?])\s+', block)
                    if len(sentences) > 2:
                        # İlk iki cümleden sonrakileri sorumluluk olarak ekle
                        responsibilities = [s.strip() for s in sentences[2:] if len(s.strip()) > 20]
                
                exp_entry["sorumluluklar"] = responsibilities[:5]  # En fazla 5 sorumluluk
                
                # Şirket veya pozisyon bilgisi varsa listeye ekle
                if exp_entry["sirket"] != "Belirtilmemiş" or exp_entry["pozisyon"] != "Belirtilmemiş":
                    # Sadece pozisyon bilgisi varsa, pozisyonu şirket olarak ekle
                    if exp_entry["sirket"] == "Belirtilmemiş" and exp_entry["pozisyon"] != "Belirtilmemiş":
                        exp_entry["sirket"] = exp_entry["pozisyon"]
                    experience_list.append(exp_entry)
        
        # Eğer doğrudan deneyim bölümü bulunamadıysa veya pozisyon bilgisi eksikse, proje açıklamalarına bak
        if not experience_list or any(exp["pozisyon"] == "Belirtilmemiş" for exp in experience_list):
            self._extract_position_from_projects(experience_list)
        
        return experience_list
    
    def _extract_position_from_projects(self, experience_list: List[Dict[str, Any]]) -> None:
        """Proje açıklamalarından pozisyon bilgisi çıkarır"""
        # AI ve yazılım pozisyonları için anahtar kelimeler
        ai_position_terms = [
            ('AI Engineer', ['ai', 'artificial intelligence', 'machine learning', 'model', 'algorithm']),
            ('Machine Learning Engineer', ['machine learning', 'ml', 'model', 'algorithm', 'prediction']),
            ('Computer Vision Engineer', ['computer vision', 'görüntü işleme', 'object detection', 'recognition']),
            ('Data Scientist', ['data', 'veri', 'analysis', 'analytics', 'visualization']),
            ('NLP Engineer', ['nlp', 'natural language', 'doğal dil', 'text', 'speech']),
            ('Software Engineer', ['software', 'yazılım', 'development', 'coding', 'programming']),
            ('Web Developer', ['web', 'frontend', 'backend', 'fullstack', 'site', 'application']),
            ('DevOps Engineer', ['devops', 'deployment', 'ci/cd', 'infrastructure', 'cloud']),
            ('Project Manager', ['project', 'proje', 'management', 'yönetim', 'plan', 'schedule'])
        ]
        
        # Metni küçük harfe çevir
        all_text = self.cv_text.lower()
        
        # Her deneyim için pozisyon bilgisi çıkar
        for exp in experience_list:
            if exp["pozisyon"] == "Belirtilmemiş":
                # En yüksek eşleşmeyi tutacak değişkenler
                best_position = ""
                highest_score = 0
                
                # Her pozisyon için anahtar kelime eşleşmesini ölç
                for position, keywords in ai_position_terms:
                    score = 0
                    for keyword in keywords:
                        if keyword in all_text:
                            score += 1
                    
                    # Eğer mevcut en yüksek puandan daha iyiyse, güncelle
                    if score > highest_score:
                        highest_score = score
                        best_position = position
                
                # Eğer yeterli eşleşme varsa pozisyonu güncelle
                if highest_score >= 2:  # En az 2 anahtar kelime eşleşmesi
                    exp["pozisyon"] = best_position
        
        # Eğer experience_list boşsa, en iyi pozisyon tahminiyle yeni bir giriş oluştur
        if not experience_list:
            # En yüksek eşleşmeyi bul
            best_position = ""
            highest_score = 0
            best_company = ""
            
            # Metin içinde "company" veya "şirket" kelimelerinin geçtiği yerleri ara
            company_matches = re.findall(r'([A-Za-z\s]+)(?:\s+(?:Company|Inc|Ltd|GmbH|A\.Ş\.|şirket|firma))', self.cv_text, re.IGNORECASE)
            if company_matches:
                best_company = company_matches[0].strip()
            
            # Her pozisyon için anahtar kelime eşleşmesini ölç
            for position, keywords in ai_position_terms:
                score = 0
                for keyword in keywords:
                    if keyword in all_text:
                        score += 1
                
                # Eğer mevcut en yüksek puandan daha iyiyse, güncelle
                if score > highest_score:
                    highest_score = score
                    best_position = position
            
            # Eğer şirket bilgisi veya pozisyon tahmini varsa yeni giriş oluştur
            if best_company or (highest_score >= 2 and best_position):
                new_entry = {
                    "sirket": best_company if best_company else "Belirtilmemiş",
                    "pozisyon": best_position if highest_score >= 2 else "Belirtilmemiş",
                    "tarih": "Belirtilmemiş",
                    "sorumluluklar": []
                }
                experience_list.append(new_entry)
    
    def extract_projects(self) -> List[Dict[str, Any]]:
        """Projeleri ayıklar"""
        project_list = []
        
        # Proje bölümünü bul
        project_section_pattern = r'(?:projeler|proje|projects|project)(?:[:\s]+)(.*?)(?:(?:\n\s*\n)|$)'
        project_section_match = re.search(project_section_pattern, self.cv_text, re.IGNORECASE | re.DOTALL)
        
        # Proje bilgileri için kalıplar
        project_name_pattern = r'((?:proje|project|uygulama|application|sistem|system)[^\n,.;]*)'
        tech_pattern = r'(?:teknoloji|technology|tool|araç)(?:[:\s]+)(.*?)(?:(?:\n)|$)'
        
        # Yaygın proje eylem fiilleri
        project_action_verbs = [
            'developed', 'created', 'implemented', 'designed', 'built', 'managed', 'led',
            'architected', 'engineered', 'deployed', 'maintained', 'optimized', 'improved',
            'automated', 'integrated', 'analyzed', 'researched', 'published', 'geliştirdi',
            'oluşturdu', 'tasarladı', 'inşa etti', 'yönetti', 'entegre etti', 'analiz etti'
        ]
        
        # Proje açıklaması içinde olabilecek teknoloji anahtar kelimeleri
        tech_keywords = [
            'using', 'kullanarak', 'with', 'ile', 'via', 'aracılığıyla', 'through', 'üzerinden',
            'based on', 'dayanarak', 'built with', 'powered by', 'technologies', 'teknolojiler'
        ]
        
        # Proje bölümünden projeleri ayıkla
        projects_from_section = []
        if project_section_match:
            project_text = project_section_match.group(1).strip()
            # Paragraf veya noktalı listelerle ayrılmış blokları ayır
            project_blocks = re.split(r'\n\s*[-•]\s+|\n\n+', project_text)
            
            for block in project_blocks:
                if len(block.strip()) < 20:  # Çok kısa blokları atla
                    continue
                
                proj_entry = {
                    "proje_adi": "Belirtilmemiş",
                    "aciklama": block.strip(),
                    "kullanilan_teknolojiler": []
                }
                
                # Proje adı
                project_match = re.search(project_name_pattern, block, re.IGNORECASE)
                if project_match:
                    proj_entry["proje_adi"] = project_match.group(1).strip()
                
                # GitHub repo adı
                github_match = re.search(r'github\.com/[^/]+/([^/\s]+)', block, re.IGNORECASE)
                if github_match and proj_entry["proje_adi"] == "Belirtilmemiş":
                    proj_entry["proje_adi"] = github_match.group(1).strip()
                
                # Proje adı hala bulunamadıysa, ilk cümleyi analiz et
                if proj_entry["proje_adi"] == "Belirtilmemiş":
                    sentences = re.split(r'(?<=[.!?])\s+', block)
                    if sentences:
                        first_sentence = sentences[0].strip()
                        # İlk cümlede eylem fiili var mı kontrol et
                        for verb in project_action_verbs:
                            if verb.lower() in first_sentence.lower():
                                # Fiilden sonraki metni proje adı olarak kullan
                                verb_pos = first_sentence.lower().find(verb.lower())
                                after_verb = first_sentence[verb_pos + len(verb):].strip()
                                
                                # "a", "an", "the" gibi article'ları temizle
                                after_verb = re.sub(r'^(?:a|an|the|bir)\s+', '', after_verb, flags=re.IGNORECASE)
                                
                                if after_verb and len(after_verb) > 3 and len(after_verb) < 50:
                                    # Virgül veya diğer ayırıcılarla sınırla
                                    project_title = re.split(r'[,;:]', after_verb)[0].strip()
                                    proj_entry["proje_adi"] = project_title
                                    break
                
                # Teknolojileri çıkar
                for keyword in tech_keywords:
                    tech_match = re.search(f'{keyword}\\s+([^.,;]+)', block, re.IGNORECASE)
                    if tech_match:
                        tech_text = tech_match.group(1).strip()
                        # Virgülle ayrılmış teknolojileri ayır
                        techs = [t.strip() for t in re.split(r'[,&]', tech_text)]
                        for tech in techs:
                            if tech and tech not in proj_entry["kullanilan_teknolojiler"]:
                                proj_entry["kullanilan_teknolojiler"].append(tech)
                
                # Eğer teknoloji bulunamadıysa, yaygın teknoloji isimlerini ara
                if not proj_entry["kullanilan_teknolojiler"]:
                    common_techs = [
                        'Python', 'Java', 'JavaScript', 'TypeScript', 'React', 'Angular', 'Vue',
                        'Node.js', 'Express', 'Django', 'Flask', 'Spring', 'Laravel', 'ASP.NET',
                        'TensorFlow', 'PyTorch', 'Keras', 'Pandas', 'NumPy', 'scikit-learn',
                        'AI', 'ML', 'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
                        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Git', 'CI/CD'
                    ]
                    
                    for tech in common_techs:
                        if re.search(r'\b' + re.escape(tech) + r'\b', block, re.IGNORECASE):
                            if tech not in proj_entry["kullanilan_teknolojiler"]:
                                proj_entry["kullanilan_teknolojiler"].append(tech)
                
                projects_from_section.append(proj_entry)
        
        # Tüm metin içinde proje açıklamalarını ara
        # Özellikle deneyim bölümlerinde veya tecrübe kısmında olabilir
        projects_from_experience = self._extract_projects_from_experience()
        
        # İki proje listesini birleştir, ancak tekrarları önle
        seen_projects = set()
        for project in projects_from_section + projects_from_experience:
            # Proje adı ve açıklamasının ilk 50 karakterini birleştirerek bir ID oluştur
            project_id = (project["proje_adi"] + project["aciklama"][:50]).lower()
            if project_id not in seen_projects:
                seen_projects.add(project_id)
                project_list.append(project)
        
        return project_list
    
    def _extract_projects_from_experience(self) -> List[Dict[str, Any]]:
        """Deneyim bölümünden proje bilgilerini çıkarır"""
        projects = []
        
        # Yaygın proje başlangıç kalıpları
        project_starters = [
            r'([^.!?]*(?:developed|created|built|designed|implemented|launched)[^.!?]*(?:project|system|application|platform|solution|tool|website|app)[^.!?]*\.)',
            r'([^.!?]*(?:geliştirdi|oluşturdu|tasarladı|uyguladı|kurdu)[^.!?]*(?:proje|sistem|uygulama|platform|çözüm|araç|web sitesi|app)[^.!?]*\.)'
        ]
        
        # Metindeki tüm paragrafları kontrol et
        for block in self.text_blocks:
            # Proje başlangıç kalıplarını ara
            for pattern in project_starters:
                project_matches = re.findall(pattern, block, re.IGNORECASE)
                for match in project_matches:
                    project_text = match.strip()
                    if len(project_text) < 20:  # Çok kısa metinleri atla
                        continue
                    
                    # Cümleyi analiz et
                    sentence_parts = re.split(r'(?:developed|created|built|designed|implemented|launched|geliştirdi|oluşturdu|tasarladı|uyguladı|kurdu)', project_text, 1, re.IGNORECASE)
                    
                    project_name = "Belirtilmemiş"
                    project_desc = project_text
                    
                    if len(sentence_parts) > 1:
                        # Fiilden sonraki kısmı proje adı olarak kullan
                        after_verb = sentence_parts[1].strip()
                        # İlk birkaç kelimeyi proje adı olarak al
                        words = re.split(r'\s+', after_verb)
                        if len(words) >= 3:
                            project_name = ' '.join(words[:3])
                            # Virgül veya nokta ile sınırla
                            project_name = re.split(r'[,.]', project_name)[0].strip()
                    
                    # Teknolojileri çıkar
                    tech_keywords = ['using', 'with', 'via', 'based on', 'built with', 'technologies']
                    technologies = []
                    
                    for keyword in tech_keywords:
                        tech_match = re.search(f'{keyword}\\s+([^.,;]+)', project_text, re.IGNORECASE)
                        if tech_match:
                            tech_text = tech_match.group(1).strip()
                            # Teknolojileri listele
                            techs = [t.strip() for t in re.split(r'[,&]', tech_text)]
                            for tech in techs:
                                if tech and tech not in technologies:
                                    technologies.append(tech)
                    
                    project = {
                        "proje_adi": project_name,
                        "aciklama": project_desc,
                        "kullanilan_teknolojiler": technologies
                    }
                    
                    projects.append(project)
        
        return projects
    
    def detect_strengths(self) -> List[str]:
        """CV'den güçlü yönleri tespit eder"""
        strengths = []
        
        # Güçlü yönler için kalıplar
        strength_patterns = [
            r'(?:güçlü|güçlü yön|kuvvetli|strong|strength)(?:[:\s]+)(.*?)(?:(?:\n)|$)',
            r'(?:öne çıkan|belirgin|avantaj|advantage|notable)(?:[:\s]+)(.*?)(?:(?:\n)|$)'
        ]
        
        # Tipik güçlü yönler (en yaygın olanlar)
        typical_strengths = [
            'Analitik düşünce', 'Problem çözme', 'Takım çalışması', 'İletişim becerileri',
            'Organizasyon yeteneği', 'Detay odaklı', 'Çözüm odaklı', 'Öğrenmeye açık',
            'Yaratıcı düşünce', 'Adaptasyon yeteneği', 'Stres yönetimi', 'İnovasyon',
            'Liderlik', 'Karar alma yeteneği', 'Zaman yönetimi'
        ]
        
        # Kalıplara dayalı tespit
        for pattern in strength_patterns:
            matches = re.findall(pattern, self.cv_text, re.IGNORECASE)
            for match in matches:
                strengths.append(match.strip())
        
        # Tipik güçlü yönleri ara
        for strength in typical_strengths:
            if re.search(r'\b' + re.escape(strength) + r'\b', self.cv_text, re.IGNORECASE):
                strengths.append(strength)
        
        # Tekrarları kaldır ve en fazla 5 güçlü yön döndür
        unique_strengths = list(set(strengths))
        if not unique_strengths:
            # CV analizinden diğer alanlarla ilgili çıkarımlar yap
            if self.extract_education():
                unique_strengths.append("Eğitim odaklı")
            
            skills = self.extract_skills()
            if skills["teknik_beceriler"] or skills["yazilim_dilleri"]:
                unique_strengths.append("Teknik yetkinlikler")
            
            if skills["diller"] and len(skills["diller"]) > 1:
                unique_strengths.append("Çoklu dil yetkinliği")
            
            if skills["soft_beceriler"]:
                unique_strengths.append("Kişilerarası iletişim becerileri")
        
        return unique_strengths[:5]
    
    def detect_improvement_areas(self) -> List[str]:
        """CV'den geliştirilmesi gereken yönleri tespit eder"""
        improvements = []
        
        # Geliştirilmesi gereken yönler için kalıplar
        improvement_patterns = [
            r'(?:geliştirilmesi gereken|geliştirme|zayıf|weakness|improvement)(?:[:\s]+)(.*?)(?:(?:\n)|$)'
        ]
        
        # Kalıplara dayalı tespit
        for pattern in improvement_patterns:
            matches = re.findall(pattern, self.cv_text, re.IGNORECASE)
            for match in matches:
                improvements.append(match.strip())
        
        # Eğer hiçbir şey bulunamadıysa, CV'nin genel bir değerlendirmesine dayalı öneriler
        if not improvements:
            # Eksik bölümleri kontrol et
            missing_sections = []
            
            if not self.extract_personal_info().get("linkedin", ""):
                missing_sections.append("LinkedIn profili eklenebilir")
            
            if not self.extract_projects():
                missing_sections.append("Proje detayları genişletilebilir")
            
            skills = self.extract_skills()
            if not skills["soft_beceriler"]:
                missing_sections.append("Yumuşak beceriler (soft skills) vurgulanabilir")
            
            if not self.extract_education():
                missing_sections.append("Eğitim bilgileri detaylandırılabilir")
            
            improvements = missing_sections[:3]  # En fazla 3 öneri
        
        return improvements
    
    def suggest_positions(self) -> List[str]:
        """CV'ye dayalı olarak uygun pozisyonlar önerir"""
        positions = []
        
        # Beceri ve deneyimlere dayalı pozisyon önerileri
        skills = self.extract_skills()
        experiences = self.extract_experience()
        
        # Yazılım dilleri ve teknolojilerden pozisyon belirleme
        programming_skills = skills["yazilim_dilleri"]
        technical_skills = skills["teknik_beceriler"]
        
        # Yazılım geliştirme ile ilgili
        if any(lang in programming_skills for lang in ["Python", "Java", "C#", "C++"]):
            if "backend" in " ".join(technical_skills).lower() or any(tech in technical_skills for tech in ["Django", "Spring", "ASP.NET", "Flask"]):
                positions.append("Backend Geliştirici")
            else:
                positions.append("Yazılım Geliştirici")
        
        if any(lang in programming_skills for lang in ["JavaScript", "TypeScript", "HTML", "CSS"]):
            if any(tech in technical_skills for tech in ["React", "Angular", "Vue"]):
                positions.append("Frontend Geliştirici")
            else:
                positions.append("Web Geliştirici")
        
        # Veri bilimi ile ilgili
        if "Python" in programming_skills and any(tech in technical_skills for tech in ["TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy"]):
            positions.append("Veri Bilimci")
            positions.append("Makine Öğrenmesi Mühendisi")
        
        # DevOps ile ilgili
        if any(tech in technical_skills for tech in ["Docker", "Kubernetes", "AWS", "Azure", "CI/CD", "Jenkins"]):
            positions.append("DevOps Mühendisi")
            positions.append("Cloud Mühendisi")
        
        # İş deneyimlerinden çıkarım
        position_titles = []
        for exp in experiences:
            position = exp.get("pozisyon", "").lower()
            if position and position != "belirtilmemiş":
                position_titles.append(position)
        
        # Deneyimlerden son pozisyonu öner
        if position_titles:
            last_position = position_titles[0]
            positions.append(f"Kıdemli {last_position.title()}")
        
        # Eğer hiçbir şey bulunamadıysa, genel bir öneri yap
        if not positions:
            positions = ["Yazılım Mühendisi", "Bilgisayar Mühendisi", "IT Uzmanı"]
        
        return list(set(positions))[:5]  # Benzersiz ve en fazla 5 pozisyon
    
    def create_talent_summary(self) -> str:
        """CV'nin yetenek özetini oluşturur"""
        # Kişisel bilgiler, beceriler, eğitim ve deneyimleri al
        personal_info = self.extract_personal_info()
        skills = self.extract_skills()
        education = self.extract_education()
        experience = self.extract_experience()
        
        # Özet oluştur
        summary_parts = []
        
        # İsim ve eğitim bilgisi
        name = personal_info.get("isim", "").strip()
        if name and name != "Belirtilmemiş":
            education_info = ""
            if education:
                edu = education[0]
                if edu.get("derece") != "Belirtilmemiş":
                    education_info = f"{edu.get('derece')} "
                if edu.get("bolum") != "Belirtilmemiş":
                    education_info += f"{edu.get('bolum')} bölümü "
                if edu.get("okul") != "Belirtilmemiş":
                    education_info += f"{edu.get('okul')} "
                education_info = education_info.strip()
            
            if education_info:
                summary_parts.append(f"{name}, {education_info} mezunudur.")
            else:
                summary_parts.append(f"{name}, ")
        
        # Deneyim bilgisi
        experience_years = 0
        experience_areas = []
        
        for exp in experience:
            # Deneyim süresini hesapla
            years_match = re.search(r'(\d{4})\s*(?:-|–)\s*(\d{4}|present|günümüz|devam)', exp.get("tarih", ""))
            if years_match:
                start_year = int(years_match.group(1))
                end_year_str = years_match.group(2)
                
                if end_year_str.isdigit():
                    end_year = int(end_year_str)
                else:  # "present", "günümüz", "devam" gibi
                    import datetime
                    end_year = datetime.datetime.now().year
                
                experience_years += (end_year - start_year)
            
            # Çalışma alanlarını topla
            position = exp.get("pozisyon", "").strip()
            if position and position != "Belirtilmemiş" and position not in experience_areas:
                experience_areas.append(position)
        
        if experience_years > 0:
            summary_parts.append(f"Yaklaşık {experience_years} yıllık deneyime sahiptir.")
        
        if experience_areas:
            areas_text = ", ".join(experience_areas[:3])  # En fazla 3 alan
            summary_parts.append(f"{areas_text} alanlarında çalışmıştır.")
        
        # Beceri bilgisi
        tech_skills = skills["teknik_beceriler"]
        prog_skills = skills["yazilim_dilleri"]
        lang_skills = skills["diller"]
        
        if tech_skills or prog_skills:
            technical_text = ""
            if prog_skills:
                technical_text = f"{', '.join(prog_skills[:3])} "
                if tech_skills:
                    technical_text += "ve "
            
            if tech_skills:
                technical_text += f"{', '.join(tech_skills[:3])} "
            
            technical_text = technical_text.strip()
            if technical_text:
                summary_parts.append(f"Teknik yetkinlikleri arasında {technical_text} bulunmaktadır.")
        
        if lang_skills:
            langs_text = ", ".join(lang_skills[:2])  # En fazla 2 dil
            summary_parts.append(f"Yabancı dil olarak {langs_text} bilmektedir.")
        
        # Güçlü yönler
        strengths = self.detect_strengths()
        if strengths:
            strengths_text = " ve ".join(strengths[:2])  # En fazla 2 güçlü yön
            summary_parts.append(f"Güçlü yönleri arasında {strengths_text} bulunmaktadır.")
        
        # Özeti birleştir
        if summary_parts:
            return " ".join(summary_parts)
        else:
            return "CV'den yeterli bilgi çıkarılamadı."
    
    def score_cv(self) -> Dict[str, int]:
        """CV'yi puanlar"""
        scores = {
            "toplam_puan": 0,
            "egitim_puani": 0,
            "deneyim_puani": 0,
            "beceri_puani": 0,
            "proje_puani": 0
        }
        
        # Eğitimi puanla
        education = self.extract_education()
        if education:
            scores["egitim_puani"] = min(100, len(education) * 25)  # Her eğitim 25 puan, maksimum 100
            
            # Dereceleri için ekstra puanlar
            for edu in education:
                degree = edu.get("derece", "").lower()
                if "doktora" in degree or "phd" in degree:
                    scores["egitim_puani"] = 100  # Doktora varsa tam puan
                    break
                elif "yüksek" in degree or "master" in degree:
                    scores["egitim_puani"] = max(scores["egitim_puani"], 85)  # Yüksek lisans varsa en az 85
                elif "lisans" in degree or "bachelor" in degree:
                    scores["egitim_puani"] = max(scores["egitim_puani"], 75)  # Lisans varsa en az 75
        
        # Deneyimi puanla
        experience = self.extract_experience()
        if experience:
            # Her deneyim 20 puan, maksimum 100
            scores["deneyim_puani"] = min(100, len(experience) * 20)
            
            # Sorumluluklar için ekstra puanlar
            responsibility_count = sum(len(exp.get("sorumluluklar", [])) for exp in experience)
            scores["deneyim_puani"] = min(100, scores["deneyim_puani"] + responsibility_count * 5)
        
        # Becerileri puanla
        skills = self.extract_skills()
        skill_count = len(skills["teknik_beceriler"]) + len(skills["yazilim_dilleri"]) + len(skills["diller"]) + len(skills["soft_beceriler"])
        scores["beceri_puani"] = min(100, skill_count * 10)  # Her beceri 10 puan, maksimum 100
        
        # Projeleri puanla
        projects = self.extract_projects()
        if projects:
            scores["proje_puani"] = min(100, len(projects) * 25)  # Her proje 25 puan, maksimum 100
            
            # Kullanılan teknolojiler için ekstra puanlar
            tech_count = sum(len(proj.get("kullanilan_teknolojiler", [])) for proj in projects)
            scores["proje_puani"] = min(100, scores["proje_puani"] + tech_count * 5)
        
        # Toplam puanı hesapla (ağırlıklı ortalama)
        weights = {
            "egitim_puani": 0.25,
            "deneyim_puani": 0.35,
            "beceri_puani": 0.25,
            "proje_puani": 0.15
        }
        
        scores["toplam_puan"] = int(sum(score * weights[key] for key, score in scores.items() if key != "toplam_puan"))
        
        return scores
    
    def generate_cv_analysis(self) -> Dict[str, Any]:
        """Tam CV analizi oluşturur"""
        analysis = {
            "kisisel_bilgiler": self.extract_personal_info(),
            "cv_puanlama": self.score_cv(),
            "beceriler": self.extract_skills(),
            "egitim_bilgileri": self.extract_education(),
            "is_deneyimi": self.extract_experience(),
            "projeler": self.extract_projects(),
            "guclu_yonler": self.detect_strengths(),
            "gelistirilmesi_gereken_yonler": self.detect_improvement_areas(),
            "uygun_pozisyonlar": self.suggest_positions(),
            "yetenek_ozeti": self.create_talent_summary()
        }
        
        return analysis

    def extract_keywords(self, limit: int = 20) -> List[str]:
        """CV'den anahtar kelimeleri çıkarır"""
        # Sık kullanılan kelimeler - filtrelenecek
        common_words = set([
            "ve", "veya", "ile", "ya", "the", "a", "an", "and", "or", "in", "on", "at", "to", "of", "for",
            "bu", "şu", "o", "bir", "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
            "our", "their", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "shall", "will", "should", "would", "may", "might", "must", "can", "could",
            "ben", "sen", "o", "biz", "siz", "onlar", "benim", "senin", "onun", "bizim", "sizin", "onların",
            "idi", "imiş", "iken", "ki", "de", "da", "mi", "mu", "mı", "mü", "ama", "fakat", "lakin", "ancak",
            "from", "by", "as", "tarafından", "kadar", "gibi", "about", "hakkında", "between", "arasında",
            "into", "through", "during", "boyunca", "süresince", "before", "önce", "after", "sonra", "above",
            "over", "üstünde", "yukarısında", "below", "under", "altında", "aşağısında"
        ])
        
        # Noktalama işaretleri ve rakamları temizle
        cleaned_text = re.sub(r'[^\w\s]', ' ', self.cv_text.lower())  # Noktalama işaretlerini kaldır
        cleaned_text = re.sub(r'\d+', ' ', cleaned_text)  # Rakamları kaldır
        
        # Kelimeleri ayır
        words = cleaned_text.split()
        
        # Sık kullanılan kelimeleri ve çok kısa kelimeleri filtrele
        filtered_words = [word for word in words if word not in common_words and len(word) > 2]
        
        # Kelimelerin sıklığını hesapla
        word_freq = {}
        for word in filtered_words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # En sık kullanılan kelimeleri sırala (sıklık, ardından alfabetik)
        sorted_words = sorted(word_freq.items(), key=lambda x: (-x[1], x[0]))
        
        # İlk N kelimeyi döndür
        keywords = [word for word, freq in sorted_words[:limit]]
        
        return keywords
        
    def get_cv_summary(self) -> Dict[str, Any]:
        """CV'nin özet bilgilerini döndürür"""
        summary = {
            "kisisel_bilgiler": self.extract_personal_info(),
            "egitim": self.extract_education(),
            "deneyim": self.extract_experience(),
            "beceriler": self.extract_skills(),
            "anahtar_kelimeler": self.extract_keywords(10),
            "analiz_tarihi": datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        }
        
        if hasattr(self, "file_path"):
            summary["dosya_adi"] = self.file_path
        
        # Özgeçmişin genel kalitesini hesapla
        quality_score = self._calculate_cv_quality(summary)
        summary["kalite_skoru"] = quality_score
        
        return summary
    
    def _calculate_cv_quality(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """CV'nin kalitesini hesaplar ve eksikleri belirler"""
        quality = {
            "genel_skor": 0,
            "eksikler": [],
            "oneriler": []
        }
        
        total_points = 0
        max_points = 100
        
        # Kişisel bilgilerin tam olup olmadığını kontrol et
        personal_info = summary["kisisel_bilgiler"]
        if personal_info["isim"] == "Belirtilmemiş":
            quality["eksikler"].append("İsim bilgisi eksik veya tanımlanamadı")
        else:
            total_points += 10
        
        if personal_info["email"] == "Belirtilmemiş":
            quality["eksikler"].append("Email adresi eksik")
        else:
            total_points += 10
        
        if personal_info["telefon"] == "Belirtilmemiş":
            quality["eksikler"].append("Telefon numarası eksik")
        else:
            total_points += 5
        
        if personal_info["lokasyon"] == "Belirtilmemiş":
            quality["eksikler"].append("Lokasyon bilgisi eksik")
        else:
            total_points += 5
        
        if personal_info.get("linkedin", "Belirtilmemiş") == "Belirtilmemiş":
            quality["eksikler"].append("LinkedIn profili eksik")
            quality["oneriler"].append("LinkedIn profil bağlantınızı ekleyin")
        else:
            total_points += 5
        
        # Eğitim bilgileri
        if not summary["egitim"]:
            quality["eksikler"].append("Eğitim bilgileri eksik veya tanımlanamadı")
        else:
            edu_points = min(len(summary["egitim"]) * 5, 15)  # Maksimum 15 puan
            total_points += edu_points
            
            # Eğitim detaylarını kontrol et
            for edu in summary["egitim"]:
                if edu.get("okul", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir eğitim kaydında okul/üniversite bilgisi eksik")
                if edu.get("bolum", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir eğitim kaydında bölüm/derece bilgisi eksik")
                if edu.get("mezuniyet", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir eğitim kaydında mezuniyet tarihi eksik")
        
        # İş deneyimi
        if not summary["deneyim"]:
            quality["eksikler"].append("İş deneyimi bilgileri eksik veya tanımlanamadı")
        else:
            exp_points = min(len(summary["deneyim"]) * 5, 15)  # Maksimum 15 puan
            total_points += exp_points
            
            # Deneyim detaylarını kontrol et
            for exp in summary["deneyim"]:
                if exp.get("sirket", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir deneyim kaydında şirket bilgisi eksik")
                if exp.get("pozisyon", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir deneyim kaydında pozisyon bilgisi eksik")
                if exp.get("tarih", "Belirtilmemiş") == "Belirtilmemiş":
                    quality["eksikler"].append("Bir deneyim kaydında tarih bilgisi eksik")
                if not exp.get("sorumluluklar", []):
                    quality["eksikler"].append("İş deneyiminde sorumluluklar/başarılar detaylandırılmamış")
                    quality["oneriler"].append("Her iş deneyimi için somut başarılar ve sorumluluklar ekleyin")
        
        # Beceriler
        skills = summary["beceriler"]
        skill_categories = [skills.get("teknik_beceriler", []), skills.get("yazilim_dilleri", []), 
                            skills.get("diller", []), skills.get("soft_beceriler", [])]
        
        if not any(skill_categories):
            quality["eksikler"].append("Beceriler bölümü eksik veya tanımlanamadı")
        else:
            # Her bir kategori için puan ver
            for category, max_cat_points in zip(skill_categories, [10, 10, 5, 5]):
                if category:
                    cat_points = min(len(category), max_cat_points)
                    total_points += cat_points
            
            # Beceri önerileri
            if not skills.get("teknik_beceriler", []) and not skills.get("yazilim_dilleri", []):
                quality["oneriler"].append("Teknik becerilerinizi ve bildiğiniz programlama dillerini ekleyin")
            if not skills.get("diller", []):
                quality["oneriler"].append("Bildiğiniz yabancı dilleri ve seviyelerini ekleyin")
            if not skills.get("soft_beceriler", []):
                quality["oneriler"].append("İletişim, takım çalışması gibi soft becerilerinizi ekleyin")
        
        # Genel kontroller
        if summary.get("anahtar_kelimeler", []) and len(summary["anahtar_kelimeler"]) < 5:
            quality["oneriler"].append("CV'nize alanınıza özel daha fazla anahtar kelime ekleyin")
        
        # Son skoru hesapla
        quality["genel_skor"] = min(int(total_points / max_points * 100), 100)
        
        # Skor bazlı genel öneriler
        if quality["genel_skor"] < 50:
            quality["oneriler"].append("CV'niz temel eksiklikler içeriyor, yukarıdaki önerileri dikkate alarak güncelleyin")
        elif quality["genel_skor"] < 70:
            quality["oneriler"].append("CV'nizi geliştirmek için eksik alanları tamamlayın")
        elif quality["genel_skor"] < 90:
            quality["oneriler"].append("CV'niz iyi durumda, küçük iyileştirmelerle mükemmel hale getirebilirsiniz")
        
        return quality
    
    def analyze_cv_with_ai(self) -> Dict[str, Any]:
        """CV'yi AI kullanarak analiz eder"""
        if not self.ollama:
            logger.warning("Ollama bağlantısı yok, AI analizi yapılamıyor. Geleneksel analize yönlendiriliyor.")
            return self.get_cv_summary()  # Yedek olarak geleneksel analizi kullan
        
        prompt = """
        <KONU>CV ANALİZİ</KONU>
        
        <CV>
        """ + self.cv_text[:8000] + """  
        </CV>
        
        <GÖREV>
        Yukarıdaki CV'yi kapsamlı bir şekilde analiz et ve aşağıdaki JSON formatında bilgileri çıkar.
        Cevabında SADECE JSON döndür, başka açıklama yapma.
        </GÖREV>
        
        ```json
        {
          "kisisel_bilgiler": {
            "isim": "",
            "email": "",
            "telefon": "",
            "lokasyon": "",
            "linkedin": "",
            "website": ""
          },
          "egitim": [
            {
              "okul": "",
              "bolum": "",
              "mezuniyet": "",
              "detaylar": ""
            }
          ],
          "deneyim": [
            {
              "sirket": "",
              "pozisyon": "",
              "tarih": "",
              "sorumluluklar": ["",""]
            }
          ],
          "beceriler": {
            "teknik_beceriler": [""],
            "yazilim_dilleri": [""],
            "diller": [""],
            "soft_beceriler": [""]
          },
          "projeler": [
            {
              "proje_adi": "",
              "aciklama": "",
              "kullanilan_teknolojiler": [""]
            }
          ],
          "anahtar_kelimeler": [""],
          "guclu_yonler": [""],
          "gelistirilmesi_gereken_yonler": [""],
          "uygun_pozisyonlar": [""],
          "kalite_analizi": {
            "genel_skor": 0,
            "eksikler": [""],
            "oneriler": [""]
          }
        }
        ```
        """
        
        try:
            # AI modelini kullanarak analiz yap
            result = self.ollama.generate(prompt=prompt)
            
            # JSON içeriğini çıkar
            json_data = self._extract_json_from_response(result)
            
            if json_data:
                # Analiz tarihini ekle
                json_data["analiz_tarihi"] = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                
                # Dosya adını ekle (eğer varsa)
                if hasattr(self, "file_path"):
                    json_data["dosya_adi"] = self.file_path
                    
                logger.info("CV AI analizi başarıyla tamamlandı")
                return json_data
            else:
                logger.error("AI analizi sonucu JSON çıkarılamadı")
                # Yedek olarak geleneksel analizi kullan
                return self.get_cv_summary()
                
        except Exception as e:
            logger.error(f"AI analizi sırasında hata: {str(e)}")
            # Hata durumunda geleneksel analizi kullan
            return self.get_cv_summary()
    
    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """AI yanıtından JSON verisi çıkarır"""
        try:
            # JSON bloklarını bul
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # Eğer kod bloğu formatında değilse, düz JSON arama
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # JSON bulunamadı
            return {}
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON çözümleme hatası: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"JSON çıkarma hatası: {str(e)}")
            return {}
            
    def get_cv_summary_ai(self) -> Dict[str, Any]:
        """CV'nin özet bilgilerini AI ile analiz ederek döndürür"""
        # AI analizi yap
        analysis = self.analyze_cv_with_ai()
        
        # Eğer AI analizi başarısız olduysa, geleneksel analizi kullan
        if not analysis or "error" in analysis:
            logger.warning("AI analizi başarısız oldu, geleneksel analiz kullanılıyor")
            return self.get_cv_summary()
            
        # AI analizini döndür
        return analysis

    @staticmethod
    def create_example_cv() -> str:
        """Test amaçlı örnek bir CV metni oluşturur"""
        example_cv = """
Ahmet Yılmaz
İstanbul, Türkiye | ahmet.yilmaz@email.com | +90 555 123 4567 | linkedin.com/in/ahmetyilmaz | github.com/ahmetyilmaz

PROFİL
Makine öğrenmesi ve yapay zeka konularında 3+ yıl deneyime sahip yazılım mühendisi. Büyük veri analizi ve doğal dil işleme projelerinde uzmanlık. Fintech ve e-ticaret sektörlerinde müşteri odaklı çözümler geliştirme konusunda kanıtlanmış başarı.

EĞİTİM
Boğaziçi Üniversitesi, İstanbul
Bilgisayar Mühendisliği Bölümü, Lisans
Eylül 2015 - Haziran 2019
• GPA: 3.65/4.00
• Onur öğrencisi
• Bitirme Projesi: "Derin Öğrenme ile Türkçe Metin Sınıflandırma"

İŞ DENEYİMİ
ABC Teknoloji, İstanbul
Kıdemli Veri Bilimcisi
Ocak 2022 - Günümüz
• Finansal sahtekarlık tespiti için makine öğrenmesi modelleri geliştirdim, sahte işlem tespitinde %30 artış sağladım
• Müşteri davranış analizi için NLP tabanlı bir öneri sistemi tasarladım ve uyguladım
• 5 kişilik veri bilimi ekibini yönettim ve yeni ekip üyelerinin eğitimini sağladım
• Python, TensorFlow ve PyTorch kullanarak derin öğrenme modelleri geliştirdim

XYZ Yazılım, Ankara
Yapay Zeka Mühendisi
Temmuz 2019 - Aralık 2021
• E-ticaret platformu için ürün öneri algoritmasını geliştirdim, tıklama oranlarında %25 artış sağladı
• Kullanıcı yorumlarından duygu analizi yapan bir sistem tasarladım ve uyguladım
• Docker ve Kubernetes kullanarak ML modellerinin dağıtımını otomatikleştirdim
• 3 başarılı AI projesinin liderliğini yaptım ve müşteri memnuniyetini artırdım

PROJELER
Duygu Analizi API'si
• Python ve FastAPI kullanarak açık kaynaklı bir duygu analizi API'si geliştirdim
• 10.000+ günlük istek işleme kapasitesine sahip, %95 doğruluk oranı
• GitHub'da 200+ yıldız aldı

Görüntü Tanıma Uygulaması
• TensorFlow ve React Native kullanarak mobil görüntü tanıma uygulaması geliştirdim
• YOLO algoritması ile gerçek zamanlı nesne tanıma uygulaması
• 10.000+ indirme, 4.7/5 kullanıcı puanı

BECERİLER
Programlama Dilleri: Python, JavaScript, Java, SQL, R
Teknolojiler & Araçlar: TensorFlow, PyTorch, Scikit-learn, Pandas, NumPy, Docker, Kubernetes, Git, AWS, Azure ML
Veri Tabanları: PostgreSQL, MongoDB, Redis, Elasticsearch
Diller: Türkçe (Anadil), İngilizce (İleri Seviye), Almanca (Orta Seviye)
Soft Skills: Takım Liderliği, Proje Yönetimi, Problem Çözme, İletişim, Sunum Becerileri

SERTİFİKALAR
• Deep Learning Specialization - Coursera (Andrew Ng)
• TensorFlow Developer Certificate - Google
• AWS Certified Machine Learning - Specialty
• Scrum Master Certification

GÖNÜLLÜ ÇALIŞMALAR
Kod Vakfı, İstanbul
Eğitmen - Ocak 2020 - Günümüz
• Dezavantajlı gençlere programlama ve yapay zeka eğitimleri veriyorum
• 100+ öğrenciye mentorluk yaptım

KONFERANSLAR & YAYINLAR
• "Türkçe NLP Uygulamaları" - AI Summit İstanbul 2022 (Konuşmacı)
• "Fintech Sektöründe Makine Öğrenmesi" - IEEE Conference 2021 (Makale)
"""
        return example_cv
        
    @classmethod
    def run_ai_test(cls) -> Dict[str, Any]:
        """Örnek CV üzerinde AI tabanlı analiz testi yapar"""
        # Örnek CV oluştur
        example_cv = cls.create_example_cv()
        
        # Analiz için parser oluştur
        parser = cls(example_cv)
        
        # Sonuçları karşılaştır
        ai_results = parser.get_cv_summary_ai()
        traditional_results = parser.get_cv_summary()
        
        # Sonuçları döndür
        return {
            "ai_analysis": ai_results,
            "traditional_analysis": traditional_results,
            "example_cv": example_cv
        }

if __name__ == "__main__":
    import sys
    import json
    
    # Komut satırı parametresi kontrolü
    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  python cv_parser.py <cv_metin_dosyası>       -> Geleneksel analiz")
        print("  python cv_parser.py --ai <cv_metin_dosyası>  -> AI analizi")
        print("  python cv_parser.py --test                   -> Örnek CV ile test")
        sys.exit(1)
    
    # Örnek CV testi
    if sys.argv[1] == "--test":
        print("Örnek CV ile AI analizi test ediliyor...")
        test_results = CVParser.run_ai_test()
        
        # Sonuçları dosyaya kaydet
        output_file = "cv_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, ensure_ascii=False, indent=2)
        
        print(f"Test sonuçları '{output_file}' dosyasına kaydedildi.")
        sys.exit(0)
        
    # AI analizi
    use_ai = False
    if sys.argv[1] == "--ai":
        use_ai = True
        if len(sys.argv) < 3:
            print("Hata: AI analizi için CV dosyası belirtilmedi")
            sys.exit(1)
        cv_file = sys.argv[2]
    else:
        cv_file = sys.argv[1]
    
    # Metin dosyasını oku
    try:
        with open(cv_file, 'r', encoding='utf-8') as f:
            cv_text = f.read()
    except Exception as e:
        print(f"Hata: Dosya okunamadı - {str(e)}")
        sys.exit(1)
    
    # CV'yi analiz et
    parser = CVParser(cv_text)
    parser.file_path = cv_file  # Dosya adını kaydet
    
    if use_ai:
        analysis = parser.get_cv_summary_ai()
        print("AI tabanlı CV analizi tamamlandı!")
    else:
        analysis = parser.get_cv_summary()
        print("Geleneksel CV analizi tamamlandı!")
    
    # Sonuçları ekrana yazdır
    print(json.dumps(analysis, ensure_ascii=False, indent=2)) 