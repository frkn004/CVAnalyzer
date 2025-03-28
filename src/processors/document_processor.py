from typing import Optional, Dict, Any, List
from pathlib import Path
import PyPDF2
import fitz  # PyMuPDF
from docx import Document
import os
import re
from datetime import date
from functools import lru_cache
from ..models.cv_models import CV, PersonalInfo, Education, Experience
import json
import logging

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        """Belge işleme sınıfı"""
        self.supported_formats = ['.txt', '.pdf', '.docx']
        self._text_cache = {}
        self._analysis_cache = {}
        
    @lru_cache(maxsize=100)
    def extract_text(self, file_path: str) -> str:
        """
        Dosyadan metin çıkarır
        
        Args:
            file_path (str): Dosya yolu
            
        Returns:
            str: Çıkarılan metin
            
        Raises:
            ValueError: Desteklenmeyen dosya formatı veya geçersiz dosya
        """
        logger.info(f"Dosyadan metin çıkarılıyor: {file_path}")
        file_path = Path(file_path)
        if not file_path.exists():
            raise ValueError(f"Dosya bulunamadı: {file_path}")
            
        if file_path.suffix not in self.supported_formats:
            raise ValueError(f"Desteklenmeyen dosya formatı: {file_path.suffix}")
            
        # Önbellekte varsa döndür
        cache_key = str(file_path.absolute())
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]
            
        try:
            if file_path.suffix == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    
            elif file_path.suffix == '.pdf':
                # PyMuPDF ile PDF'i işle (daha iyi metin çıkarımı için)
                text = self._extract_text_from_pdf_with_layout(file_path)
                    
            elif file_path.suffix == '.docx':
                doc = Document(file_path)
                text = ' '.join([paragraph.text for paragraph in doc.paragraphs])
                
            # Metni temizle - belirli formatlamalar ve gereksiz boşlukları kaldır
            text = self._clean_text(text)
                
            # Önbelleğe kaydet
            self._text_cache[cache_key] = text
            logger.info(f"Metin başarıyla çıkarıldı, {len(text)} karakter")
            return text
                
        except Exception as e:
            logger.error(f"Dosya okuma hatası: {str(e)}")
            raise ValueError(f"Dosya okuma hatası: {str(e)}")
    
    def _extract_text_from_pdf_with_layout(self, file_path: str) -> str:
        """PyMuPDF kullanarak PDF'ten metin çıkarır ve sayfa düzenini korur"""
        try:
            # PyMuPDF ile PDF'i aç
            doc = fitz.open(file_path)
            full_text = []
            
            for page_num, page in enumerate(doc):
                # Sayfadaki metni çıkar (HTML formatında da çıkarabilir)
                text = page.get_text("text")  # Alternatif olarak: "html" veya "dict" kullanılabilir
                full_text.append(text)
                
                # Bölüm başlıklarının bulunduğu tüm blokları işaretle
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            if "spans" in line:
                                for span in line["spans"]:
                                    # Eğer metin büyük harfle başlıyor ve font boyutu büyükse,
                                    # muhtemelen bir başlıktır
                                    text = span["text"]
                                    if text and text.isupper() and len(text) > 2:
                                        font_size = span["size"]
                                        # Başlıkları belirginleştirmek için yeni satır ekle
                                        if font_size > 10:  # Font büyüklüğü eşiği
                                            logger.info(f"PDF'de başlık tespit edildi: '{text}', font boyutu: {font_size}")
                                            # Bu satırı iki yeni satır ile çevrele
                                            full_text.append(f"\n\n{text}\n\n")
            
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"PyMuPDF ile PDF işleme hatası: {str(e)}")
            # Hata durumunda PyPDF2 ile devam et
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return ' '.join([page.extract_text() for page in reader.pages if page.extract_text()])
    
    def _clean_text(self, text: str) -> str:
        """Metni temizler ve normalleştirir"""
        if not text:
            return ""
            
        # Çoklu boşlukları tek boşluğa indir (yeni satırları koru)
        text = re.sub(r' +', ' ', text)
        
        # PDF artefaktlarını kaldır
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        # Gereksiz yeni satırları kaldır, ama birden fazla yeni satırı koru (başlıklar için gerekli)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # En yaygın CV bölüm başlıklarını büyük harfle ve yeni satırlarda belirgin hale getir
        for header in ['EDUCATION', 'WORK EXPERIENCE', 'SKILLS', 'LANGUAGES', 'PROJECTS', 'EXPERIENCE', 
                      'CERTIFICATIONS', 'REFERENCES', 'LEADERSHIP', 'PROFILE', 'SUMMARY']:
            pattern = rf'(?i)(\b{header}\b)'
            text = re.sub(pattern, f'\n\n{header}\n\n', text)
        
        return text.strip()
            
    @lru_cache(maxsize=100)
    def analyze_cv(self, text: str) -> Dict[str, Any]:
        """
        CV metnini analiz eder
        
        Args:
            text (str): CV metni
            
        Returns:
            Dict[str, Any]: Analiz sonuçları
        """
        logger.info(f"CV analizi başlatılıyor, {len(text)} karakter")
        
        # Önbellekte varsa döndür
        cache_key = hash(text)
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
            
        try:
            # CV'den tüm becerileri çıkar (bölüm ayırma bile olmazsa bulunsun diye)
            all_skills = self._extract_all_skills_from_cv(text)
            logger.info(f"CV'den çıkarılan tüm beceriler: {all_skills}")
            
            # Metni bölümlere ayır
            sections = self._extract_sections(text)
            
            # CV'yi analiz etmeden önce metni ön işle (eksik bölümleri tespit et ve tamamla)
            self._preprocess_sections(sections, text)
        
        # Kişisel bilgileri çıkar
            personal_info = self._extract_personal_info(text, sections.get('kişisel bilgiler', ''))
        
        # Eğitim bilgilerini çıkar
            education = self._extract_education(sections.get('eğitim', ''))
        
        # İş deneyimlerini çıkar
            experience = self._extract_experience(sections.get('deneyim', ''))
        
        # Becerileri çıkar
            skills = self._extract_skills(sections.get('beceriler', ''))
            
            # Eğer beceriler boşsa, önceden çıkarılan tüm becerileri kullan
            if not skills and all_skills:
                skills = all_skills
        
        # Dil bilgilerini çıkar
            languages = self._extract_languages(sections.get('diller', ''))
        
        # Sertifikaları çıkar
            certifications = self._extract_certifications(sections.get('sertifikalar', ''))
        
            # Özeti çıkar
            summary = self._extract_summary(sections.get('özet', ''))
        
        # CV nesnesini oluştur
            cv_data = {
                'personal_info': personal_info,
                'education': education,
                'experience': experience,
                'skills': skills,
                'languages': languages,
                'certifications': certifications,
                'summary': summary,
                'match_score': None  # Eşleştirme yapıldığında doldurulacak
            }
            
            # Önbelleğe kaydet
            self._analysis_cache[cache_key] = cv_data
            
            logger.info(f"CV analizi tamamlandı: {personal_info.get('name', 'İsimsiz')}")
            return cv_data
            
        except Exception as e:
            logger.error(f"CV analiz hatası: {str(e)}")
            # Basit bir analiz hatası durumunda, temel bir CV modeli döndür
            return {
                'personal_info': {'name': 'Çözümlenemedi'},
                'education': [],
                'experience': [],
                'skills': [],
                'languages': [],
                'certifications': [],
                'summary': f"CV analizi sırasında hata oluştu: {str(e)}",
                'match_score': None
            }
    
    def _extract_all_skills_from_cv(self, text: str) -> List[str]:
        """Tüm CV metninden becerileri çıkarır"""
        # Yaygın yazılım, teknoloji ve araçlar
        common_tech_skills = [
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node', 'express', 
            'sql', 'mysql', 'postgresql', 'mongodb', 'nosql', 'redis', 'html', 'css', 'scss', 'sass',
            'php', 'laravel', 'django', 'flask', 'ruby', 'rails', 'go', 'golang', 'rust', 'c#', 'c++', 'c',
            'swift', 'kotlin', 'objective-c', 'flutter', 'react native', 'xamarin',
            'aws', 'azure', 'gcp', 'firebase', 'heroku', 'digitalocean', 'docker', 'kubernetes', 'jenkins',
            'ci/cd', 'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'trello',
            'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'data science',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'jupyter',
            'tableau', 'power bi', 'excel', 'word', 'powerpoint', 'photoshop', 'illustrator', 'figma', 'sketch',
            'office', 'microsoft office', 'microsoft'
        ]
        
        # CV metnindeki tüm satırları tara
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_tech_skills:
            if skill in text_lower:
                # Büyük harfle başlat (örn. "python" -> "Python")
                capitalized_skill = skill.title() if skill.lower() != "c++" else "C++"
                found_skills.append(capitalized_skill)
        
        # Microsoft Office ürünlerini özel işle
        office_products = {
            'excel': 'Microsoft Excel',
            'word': 'Microsoft Word',
            'powerpoint': 'Microsoft PowerPoint',
            'access': 'Microsoft Access',
            'outlook': 'Microsoft Outlook'
        }
        
        for product, full_name in office_products.items():
            if product in text_lower and full_name not in found_skills:
                found_skills.append(full_name)
                
        # "MS Office" veya "Microsoft Office" ifadeleri
        if "microsoft office" in text_lower or "ms office" in text_lower:
            # Tekil Office ürünleri zaten eklendiyse genel Office becerisini eklemeyebiliriz
            if not any(skill.startswith("Microsoft ") for skill in found_skills):
                found_skills.append("Microsoft Office")
        
        # Tekrarları kaldır
        unique_skills = list(set(found_skills))
        return unique_skills
    
    def _preprocess_sections(self, sections: Dict[str, str], full_text: str):
        """CV bölümlerini ön işler ve eksik bölümleri tamamlar"""
        # Eğitim bölümü eksikse, 'EDUCATION' veya 'EDUCA TION' gibi terimlerle arama yap
        if 'eğitim' not in sections or not sections['eğitim']:
            education_match = re.search(r'(?i)(EDUCA\s*TION|EĞİTİM).+?(?=(EXPERIENCE|WORK|SKILLS|LANGUAGES|PROJECTS|İŞ|DENEYİM|PROJE)|\Z)', full_text, re.DOTALL)
            if education_match:
                sections['eğitim'] = education_match.group(0)
                logger.info(f"Eğitim bölümü otomatik tespit edildi: {sections['eğitim'][:100]}...")
        
        # Deneyim bölümü eksikse, 'EXPERIENCE' veya 'WORK EXPERIENCE' terimleriyle arama yap
        if 'deneyim' not in sections or not sections['deneyim']:
            experience_match = re.search(r'(?i)(EXPERIENCE|WORK\s*EXPERIENCE|İŞ\s*DENEYİMİ|DENEYİM).+?(?=(EDUCATION|SKILLS|LANGUAGES|PROJECTS|EĞİTİM|PROJE)|\Z)', full_text, re.DOTALL)
            if experience_match:
                sections['deneyim'] = experience_match.group(0)
                logger.info(f"Deneyim bölümü otomatik tespit edildi: {sections['deneyim'][:100]}...")
        
        # Beceri bölümü eksikse, 'SKILLS' veya 'ABILITIES' terimleriyle arama yap
        if 'beceriler' not in sections or not sections['beceriler']:
            skills_match = re.search(r'(?i)(SKILLS|ABILITIES|BECERİLER|YETENEKLER|SKILLS & INTERESTS).+?(?=(EXPERIENCE|EDUCATION|LANGUAGES|PROJECTS|DENEYİM|EĞİTİM|PROJE)|\Z)', full_text, re.DOTALL)
            if skills_match:
                sections['beceriler'] = skills_match.group(0)
                logger.info(f"Beceriler bölümü otomatik tespit edildi: {sections['beceriler'][:100]}...")
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Metni bölümlere ayırır"""
        sections = {}
        
        # Debug log ekle
        logger.info(f"Bölüm çıkarma başlatılıyor, metin uzunluğu: {len(text)}")
        
        # Yaygın bölüm başlıkları - Türkçe ve İngilizce
        section_patterns = {
            'kişisel bilgiler': [r'kişisel bilgiler', r'iletişim', r'profil', r'personal information', r'contact', r'profile', r'about me'],
            'özet': [r'özet', r'hakkımda', r'profil özeti', r'summary', r'about', r'objective', r'profile summary'],
            'eğitim': [r'eğitim', r'öğrenim', r'akademik', r'education', r'academic', r'qualifications', r'educational background'],
            'deneyim': [r'deneyim', r'iş deneyimi', r'çalışma geçmişi', r'profesyonel deneyim', 
                       r'work experience', r'professional experience', r'employment history', r'work history', r'work'],
            'beceriler': [r'beceri', r'yetenek', r'teknik beceriler', r'teknik yeterlilikler', 
                         r'skills', r'abilities', r'technical skills', r'competencies', r'skill set', r'skills & interests'],
            'diller': [r'dil', r'yabancı dil', r'dil becerileri', r'languages', r'language skills', r'foreign languages'],
            'sertifikalar': [r'sertifika', r'belge', r'lisans', r'sertifikalar ve belgeler', 
                            r'certifications', r'certificates', r'credentials', r'licenses', r'qualifications'],
            'projeler': [r'projeler', r'proje deneyimi', r'project experience', r'projects', r'project'],
            'liderlik': [r'liderlik', r'leadership experience', r'leadership'],
            'referanslar': [r'referanslar', r'references']
        }
        
        # Metnin satırlarını al
        lines = text.split('\n')
        
        # İlk 10 satırı logla (debug için)
        logger.info(f"İlk 10 satır: {[line for line in lines[:10] if line.strip()]}")
        
        # Tüm üst düzey başlıkları bul (genellikle tamamı büyük harflerle yazılmış)
        upper_headers = []
        for line in lines:
            line = line.strip()
            if len(line) > 3 and line.isupper() and not line.isdigit():
                upper_headers.append(line)
        
        logger.info(f"Tespit edilen üst düzey başlıklar: {upper_headers}")
        
        # Üst düzey başlıklar bulunduysa, bunları kullanarak metnin bölümlerini ayır
        if upper_headers:
            sections_raw = {}
            current_section = None
            current_content = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
            
                if line.upper() == line and line in upper_headers:
                    # Yeni bölüm başlığı
                    if current_section:
                        sections_raw[current_section] = current_content
                    current_section = line
                    current_content = []
                else:
                    # Mevcut bölüme satırı ekle
                    current_content.append(line)
            
            # Son bölümü ekle
            if current_section and current_content:
                sections_raw[current_section] = current_content
                
            # Üst düzey başlıkları standart bölüm adlarına eşle
            for header, content in sections_raw.items():
                header_lower = header.lower()
                matched = False
                
                for section_name, patterns in section_patterns.items():
                    for pattern in patterns:
                        if pattern in header_lower or re.search(pattern, header_lower, re.IGNORECASE):
                            sections[section_name] = '\n'.join(content)
                            matched = True
                            logger.info(f'Eşleşen bölüm: "{header}" -> "{section_name}"')
                            break
                    if matched:
                        break
                        
                # Eşleşmeyen başlıklar için orijinal başlığı kullan
                if not matched:
                    sections[header.lower()] = '\n'.join(content)
                    logger.info(f'Eşleşmeyen bölüm: "{header}" olduğu gibi kullanılıyor')
        else:
            # Üst düzey başlıklar bulunamazsa, normal section_patterns'e göre bölümleri ayır
            current_section = 'kişisel bilgiler'  # Varsayılan olarak ilk bölüm
            sections[current_section] = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
            
                # Satırın bir bölüm başlığı olup olmadığını kontrol et
                found_section = False
                for section_name, patterns in section_patterns.items():
                    if any(re.search(f"(?i){pattern}", line) for pattern in patterns):
                        current_section = section_name
                        sections[current_section] = []
                        found_section = True
                        logger.info(f'Bölüm başlığı bulundu: "{line}" -> "{section_name}"')
                        break
                        
                if not found_section:
                    sections[current_section].append(line)
        
        # Dict içindeki listeleri stringe çevir
        result = {k: '\n'.join(v) if isinstance(v, list) else v for k, v in sections.items()}
        
        # Bölümleri ve içeriklerini logla
        for section_name, content in result.items():
            content_preview = content[:100] + '...' if len(content) > 100 else content
            logger.info(f'Bölüm: {section_name}, İçerik önizlemesi: {content_preview}')
            
        return result
    
    def _extract_personal_info(self, full_text: str, section_text: str) -> Dict[str, str]:
        """Kişisel bilgileri çıkarır"""
        info = {
            'name': '',
            'email': '',
            'phone': '',
            'address': '',
            'linkedin': '',
            'website': '',
            'github': ''
        }
        
        # Ad soyad genelde CV'nin en başında olur
        first_lines = full_text.split('\n')[:3]  # İlk 3 satırı al
        for line in first_lines:
            line = line.strip()
            if line and not any(char.isdigit() for char in line) and '@' not in line and 'http' not in line:
                info['name'] = line
                break
        
        # E-posta
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, full_text)
        if email_match:
            info['email'] = email_match.group(0)
            
        # Telefon numarası
        phone_pattern = r'(?:\+\d{1,3}\s?)?(?:\(\d{1,4}\)\s?)?(?:\d{1,4}[.\-\s]?){1,4}'
        phone_match = re.search(phone_pattern, full_text)
        if phone_match:
            info['phone'] = phone_match.group(0)
            
        # LinkedIn
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/profile/|linkedin:)[^\s,)]*'
        linkedin_match = re.search(linkedin_pattern, full_text, re.IGNORECASE)
        if linkedin_match:
            info['linkedin'] = linkedin_match.group(0)
            
        # GitHub
        github_pattern = r'(?:github\.com/|github:)[^\s,)]*'
        github_match = re.search(github_pattern, full_text, re.IGNORECASE)
        if github_match:
            info['github'] = github_match.group(0)
            
        # Adres/konum - basit yaklaşım
        address_hints = ['istanbul', 'ankara', 'izmir', 'türkiye', 'adres:']
        for line in section_text.split('\n'):
            if any(hint in line.lower() for hint in address_hints):
                info['address'] = line.strip()
                break
                
        return info
    
    def _extract_education(self, section_text: str) -> List[Dict[str, Any]]:
        """Eğitim bilgilerini çıkarır"""
        education_list = []
        
        if not section_text:
            return education_list
            
        # Yaygın eğitim kurumları ve eğitim terimleri
        universities = [
            'üniversite', 'university', 'yüksek lisans', 'master', 'doktora', 'phd',
            'lisans', 'bachelor', 'fakülte', 'faculty', 'okul', 'school', 'college',
            'technical', 'institute', 'akademi', 'academy'
        ]
        
        # Eğitim bölümlerini ayır
        paragraphs = re.split(r'\n{2,}', section_text)
        
        # Eğer paragraf ayrımı yeterli değilse, alternatif ayrım yöntemleri deneyebiliriz
        if len(paragraphs) <= 1 and len(section_text) > 50:
            # Üniversite adı veya tarih ile başlayan satırları ayrım noktası olarak kullanabiliriz
            lines = section_text.split('\n')
            current_paragraph = []
            new_paragraphs = []
            
            for line in lines:
                # Eğer satır bir üniversite adı içeriyorsa ve önceki paragraf doluysa
                if any(uni in line.lower() for uni in universities) and current_paragraph:
                    new_paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = [line]
                else:
                    current_paragraph.append(line)
                    
            # Son paragrafı ekle
            if current_paragraph:
                new_paragraphs.append('\n'.join(current_paragraph))
                
            if len(new_paragraphs) > 1:
                paragraphs = new_paragraphs
        
        for paragraph in paragraphs:
            if not any(uni in paragraph.lower() for uni in universities):
                continue
            
            edu_entry = {
                'institution': '',
                'degree': '',
                'field_of_study': '',
                'start_date': None,
                'end_date': None,
                'gpa': None,
                'description': ''
            }
            
            lines = paragraph.split('\n')
            
            # Kurumu belirle - genellikle paragrafın ilk satırı veya üniversite kelimesi içeren satır
            for line in lines:
                if any(uni in line.lower() for uni in universities):
                    edu_entry['institution'] = line.strip()
                    break
                    
            # Derece ve alan
            degree_patterns = ['lisans', 'yüksek lisans', 'doktora', 'bachelor', 'master', 'phd', 'bs', 'ms', 'ba', 'ma', 
                              'bsc', 'msc', 'b.s.', 'm.s.', 'b.a.', 'm.a.', 'b.eng', 'm.eng', 'computer science', 'engineering']
            for line in lines:
                line_lower = line.lower()
                if any(pattern in line_lower for pattern in degree_patterns):
                    # Derece tipini belirle
                    edu_entry['degree'] = self._extract_degree(line)
                    
                    # Alan
                    for pattern in ['computer', 'engineering', 'science', 'business', 'administration', 'management', 
                                   'arts', 'sociology', 'psychology', 'economics', 'finance', 'marketing', 'law']:
                        if pattern in line_lower:
                            field_match = re.search(r'\b' + pattern + r'[a-z\s]*\b', line_lower)
                            if field_match:
                                edu_entry['field_of_study'] = field_match.group(0).title()
                                break
                    break
                    
            # Tarihler
            date_pattern = r'(?:19|20)\d{2}'  # 1900-2099 arası yıllar
            dates = re.findall(date_pattern, paragraph)
            if len(dates) >= 2:
                dates.sort()
                edu_entry['start_date'] = dates[0]
                edu_entry['end_date'] = dates[-1]
            elif len(dates) == 1:
                # Eğer 'Mezuniyet Tarihi', 'Graduation Date' gibi ifadeler varsa, bu tek tarih bitiş tarihidir
                if re.search(r'(mezuniyet|graduation|completion|expected|anticipated|degree)', paragraph, re.IGNORECASE):
                    edu_entry['end_date'] = dates[0]
                else:
                    edu_entry['start_date'] = dates[0]
                    
                if re.search(r'(devam ediyor|present|current|ongoing|in progress)', paragraph, re.IGNORECASE):
                    # Devam eden eğitim
                    edu_entry['end_date'] = None
                    
            # GPA
            gpa_pattern = r'(?:gpa|not ortalaması|ortalama|grade point)[:\s]*(\d+[.,]\d+)'
            gpa_match = re.search(gpa_pattern, paragraph, re.IGNORECASE)
            if gpa_match:
                try:
                    edu_entry['gpa'] = float(gpa_match.group(1).replace(',', '.'))
                except:
                    pass
                    
            education_list.append(edu_entry)
            
        return education_list
    
    def _extract_degree(self, text: str) -> str:
        """Eğitim derecesini belirler"""
        text = text.lower()
        if 'doktora' in text or 'phd' in text or 'doctor' in text:
            return 'Doktora'
        elif 'yüksek lisans' in text or 'master' in text or 'msc' in text or 'ma' in text:
            return 'Yüksek Lisans'
        elif 'lisans' in text or 'bachelor' in text or 'ba' in text or 'bs' in text:
            return 'Lisans'
        elif 'lise' in text or 'high school' in text:
            return 'Lise'
        return 'Diğer'
    
    def _extract_experience(self, section_text: str) -> List[Dict[str, Any]]:
        """İş deneyimlerini çıkarır"""
        experience_list = []
        
        if not section_text:
            return experience_list
            
        # Deneyim bölümlerini ayır
        paragraphs = re.split(r'\n{2,}', section_text)
        
        # Eğer paragraf ayrımı yeterli değilse, alternatif ayrım yöntemleri deneyebiliriz
        if len(paragraphs) <= 1 and len(section_text) > 200:
            # Şirket adı, tarih veya pozisyon ile başlayan satırları ayrım noktası olarak kullanabiliriz
            lines = section_text.split('\n')
            current_paragraph = []
            new_paragraphs = []
            
            # Yaygın iş deneyimi belirteçleri
            job_indicators = [
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
                r'\b\d{4}\s*-\s*(present|current|devam|şimdi|now|\d{4})\b',
                r'\b(engineer|developer|manager|director|specialist|analyst|intern|coordinator)\b',
                r'\b(mühendis|geliştirici|yönetici|uzman|analist|stajyer|koordinatör)\b'
            ]
        
            for line in lines:
                # Eğer satır bir iş deneyimi belirteci içeriyorsa ve önceki paragraf doluysa
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in job_indicators) and current_paragraph:
                    new_paragraphs.append('\n'.join(current_paragraph))
                    current_paragraph = [line]
                else:
                    current_paragraph.append(line)
                    
            # Son paragrafı ekle
            if current_paragraph:
                new_paragraphs.append('\n'.join(current_paragraph))
                
            if len(new_paragraphs) > 1:
                paragraphs = new_paragraphs
        
        for paragraph in paragraphs:
            if len(paragraph.strip()) < 10:  # Çok kısa paragrafları atla
                continue
            
            exp_entry = {
                'company': '',
                'title': '',
                'start_date': None,
                'end_date': None,
                'location': '',
                'description': '',
                'skills_used': []
            }
            
            lines = paragraph.split('\n')
            
            # Şirket adı, lokasyon ve pozisyon (genellikle ilk satırlarda bulunur)
            if lines and lines[0].strip():
                # Şirket adı ve lokasyon genelde birlikte olabilir (Şirket - Lokasyon formatında)
                company_location_match = re.search(r'(.+?)(?: (?:in|at|-)? ?)(istanbul|ankara|izmir|türkiye|usa|remote|uzaktan|online)', lines[0], re.IGNORECASE)
                if company_location_match:
                    exp_entry['company'] = company_location_match.group(1).strip()
                    exp_entry['location'] = company_location_match.group(2).capitalize()
                else:
                    exp_entry['company'] = lines[0].strip()
                    
                # Pozisyon genelde ikinci satırda veya ilk satırda tire ile ayrılmış olabilir
                if len(lines) >= 2:
                    title_match = re.search(r'(senior|junior|lead|chief|head|principal|software|systems|ai|data|machine learning|full-stack|frontend|backend|manager|director|engineer|developer|analyst|specialist|intern|coordinator|designer)', lines[1], re.IGNORECASE)
                    if title_match:
                        exp_entry['title'] = lines[1].strip()
                    else:
                        # Pozisyon ilk satırda tire ile ayrılmış olabilir
                        title_separator = re.search(r'(.+?)\s*[-–|]\s*(.+)', lines[0])
                        if title_separator:
                            exp_entry['company'] = title_separator.group(1).strip()
                            exp_entry['title'] = title_separator.group(2).strip()
            
            # Tarihleri çıkar - İngilizce ve Türkçe tarih formatlarını destekle
            date_patterns = [
                # YYYY-YYYY veya YYYY - Present
                r'(\d{4})\s*[-–]\s*(present|current|now|\d{4})',
                # Ay YYYY - Ay YYYY veya Ay YYYY - Present
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s*[-–]\s*(Present|Current|Now|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4}|)',
                # Türkçe aylar
                r'(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+(\d{4})\s*[-–]\s*(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık|Devam Ediyor|Mevcut)\s*(\d{4}|)'
            ]
            
            for line in lines:
                for pattern in date_patterns:
                    date_match = re.search(pattern, line, re.IGNORECASE)
                    if date_match:
                        # Yıl-yıl formatı
                        if len(date_match.groups()) == 2 and date_match.group(1).isdigit():
                            exp_entry['start_date'] = date_match.group(1)
                            if date_match.group(2).isdigit():
                                exp_entry['end_date'] = date_match.group(2)
                            else:
                                exp_entry['end_date'] = None  # Devam ediyor
                        # Ay yıl - ay yıl formatı
                        elif len(date_match.groups()) >= 3:
                            exp_entry['start_date'] = date_match.group(2) if date_match.group(2) and date_match.group(2).isdigit() else None
                            exp_entry['end_date'] = date_match.group(4) if date_match.group(4) and date_match.group(4).isdigit() else None
                        break
                
                # Konum arama (eğer daha önce bulunmadıysa)
                if not exp_entry['location']:
                    location_patterns = ['istanbul', 'ankara', 'izmir', 'türkiye', 'turkey', 'remote', 'uzaktan', 'online', 'hybrid', 'hibrit']
                    for loc in location_patterns:
                        if loc in line.lower():
                            loc_match = re.search(r'\b' + loc + r'\b', line, re.IGNORECASE)
                            if loc_match:
                                exp_entry['location'] = loc_match.group(0).capitalize()
                                break
            
            # Pozisyon hala boşsa, paragrafı tarayarak buluabilir
            if not exp_entry['title']:
                title_keywords = ['engineer', 'developer', 'manager', 'director', 'specialist', 'analyst', 'intern', 'coordinator',
                                'mühendis', 'geliştirici', 'yönetici', 'uzman', 'analist', 'stajyer', 'koordinatör']
                for line in lines[1:3]:  # İlk birkaç satıra bak
                    if any(keyword in line.lower() for keyword in title_keywords):
                        exp_entry['title'] = line.strip()
                        break
            
            # Açıklama - pozisyon ve şirket satırlarını çıkararak paragrafı al
            description_lines = []
            for line in lines:
                if line and line != exp_entry['company'] and line != exp_entry['title'] and line != exp_entry['location']:
                    # Tarih içeren satırları da çıkar
                    if not any(re.search(pattern, line, re.IGNORECASE) for pattern in date_patterns):
                        description_lines.append(line)
            
            exp_entry['description'] = ' '.join(description_lines).strip()
            
            # Beceriler - açıklama metni içinde geçen teknik terimler
            common_skills = ['python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node', 'express', 
                            'sql', 'nosql', 'mongodb', 'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind', 'material ui', 
                            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'ci/cd', 'git', 'github', 'gitlab',
                            'agile', 'scrum', 'kanban', 'jira', 'trello', 'figma', 'photoshop', 'illustrator',
                            'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'data science',
                            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
                            'devops', 'backend', 'frontend', 'fullstack', 'full-stack', 'mobile', 'android', 'ios', 'flutter', 'react native', 
                            'swift', 'kotlin', 'c#', 'c++', 'c', 'go', 'golang', 'rust', 'php', 'laravel', 'ruby', 'rails']
            
            # Becerileri kısaltmalarla da ara (örn: JS for JavaScript)
            skill_abbreviations = {
                'js': 'javascript', 'ts': 'typescript', 'py': 'python', 'k8s': 'kubernetes',
                'ml': 'machine learning', 'dl': 'deep learning', 'ai': 'artificial intelligence'
            }
            
            # Metni küçük harfe çevirip kelimelere ayır
            words = exp_entry['description'].lower().split()
            # Kısaltmaları çöz
            for i, word in enumerate(words):
                if word in skill_abbreviations:
                    words[i] = skill_abbreviations[word]
            
            # Becerileri bul
            exp_entry['skills_used'] = [skill for skill in common_skills if skill in ' '.join(words)]
            
            experience_list.append(exp_entry)
            
        # Zamansal olarak sırala (en son deneyim en başta)
        experience_list.sort(key=lambda x: x['start_date'] if x['start_date'] else '0', reverse=True)
            
        return experience_list
    
    def _extract_skills(self, section_text: str) -> List[str]:
        """Becerileri çıkarır"""
        logger.info(f"Beceri çıkarma başlatıldı, bölüm uzunluğu: {len(section_text) if section_text else 0}")
        
        # Beceri bölümü yoksa, tüm metinde becerileri aramayı dene
        if not section_text or len(section_text) < 10:
            logger.info("Beceri bölümü boş veya çok kısa, tüm metinden beceri çıkarma deneniyor")
            
            # Yaygın yazılım, teknoloji ve araçlar
            common_tech_skills = [
                'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node', 'express', 
                'sql', 'mysql', 'postgresql', 'mongodb', 'nosql', 'redis', 'html', 'css', 'scss', 'sass',
                'php', 'laravel', 'django', 'flask', 'ruby', 'rails', 'go', 'golang', 'rust', 'c#', 'c++', 'c',
                'swift', 'kotlin', 'objective-c', 'flutter', 'react native', 'xamarin',
                'aws', 'azure', 'gcp', 'firebase', 'heroku', 'digitalocean', 'docker', 'kubernetes', 'jenkins',
                'ci/cd', 'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'trello',
                'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'data science',
                'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'jupyter',
                'tableau', 'power bi', 'excel', 'word', 'powerpoint', 'photoshop', 'illustrator', 'figma', 'sketch',
                'office', 'microsoft office', 'microsoft'
            ]
            
            # CV metnindeki tüm satırları tara
            found_skills = []
            lines = section_text.split('\n')
            for line in lines:
                line_lower = line.lower()
                for skill in common_tech_skills:
                    if skill in line_lower:
                        found_skills.append(skill.title())  # Büyük harfle başlat
            
            # Tekrarları kaldır
            unique_skills = list(set(found_skills))
            logger.info(f"Tüm metinden çıkarılan beceriler: {unique_skills}")
            return unique_skills

        # Normal beceri çıkarma işlemi
        skills = []
        
        # "SKILLS & INTERESTS", "SKILLS", "SKILLS:" gibi bölüm başlıkları içeren özel işleme
        section_upper = section_text.upper()
        skills_section_found = any(header in section_upper for header in ["SKILLS", "COMPETENCIES", "TECHNICAL SKILLS", "TECHNOLOGIES"])
        logger.info(f"Beceri bölümü tespit edildi mi: {skills_section_found}")
        
        if skills_section_found:
            # Sık kullanılan beceri ayırıcıları
            separators = [',', ';', '•', '|', '/', '\\', ':']
            
            # Önce satırlara ayır
            for line in section_text.split('\n'):
                line = line.strip()
                if not line or any(header.lower() in line.lower() for header in ["skills", "competencies", "abilities"]):
                    continue
            
                logger.info(f"İşlenen beceri satırı: {line}")
                    
                # Satırda ayırıcı var mı kontrol et
                has_separator = any(sep in line for sep in separators)
                
                if has_separator:
                    # Ayırıcıya göre böl
                    for sep in separators:
                        if sep in line:
                            # Eğer ":" varsa ve satırın başındaysa, muhtemelen bir kategori başlığıdır
                            if sep == ':' and line.find(':') < 5:
                                parts = line.split(':', 1)
                                if len(parts) > 1 and parts[1].strip():
                                    logger.info(f"':' ayırıcısıyla bölündü: {parts[1]}")
                                    skills.extend([s.strip() for s in parts[1].split(',') if s.strip()])
                            else:
                                logger.info(f"'{sep}' ayırıcısıyla bölündü")
                                skills.extend([s.strip() for s in line.split(sep) if s.strip()])
                            break
                else:
                    # Anahtar teknoloji kelimelerini kontrol et
                    tech_keywords = ['python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue', 'node', 'sql', 
                                   'html', 'css', 'aws', 'azure', 'docker', 'git', 'ai', 'ml', 'office', 'excel', 'word']
                    
                    if any(keyword in line.lower() for keyword in tech_keywords):
                        logger.info(f"Teknoloji anahtar kelimesi içeren satır: {line}")
                        # Eğer "Skills:" gibi bir başlık içeriyorsa, başlığı çıkar
                        if ":" in line:
                            parts = line.split(":", 1)
                            if len(parts) > 1:
                                skills.append(parts[1].strip())
                            else:
                                skills.append(line)
                        else:
                            skills.append(line)
                    else:
                        # Boşluklarla ayırıp her kelimeyi potansiyel beceri olarak kontrol et
                        words = line.split()
                        for word in words:
                            word = word.strip('.,;:()')
                            if len(word) > 2 and any(c.isalpha() for c in word):
                                # Eğer tek bir kelime ve büyük/küçük harfle yazılmışsa (örn: "Python") beceri olabilir
                                if word[0].isupper() or word.lower() in tech_keywords:
                                    logger.info(f"Potansiyel beceri kelimesi: {word}")
                                    skills.append(word)
        else:
            # Normal ayırıcılar ile bölme
            logger.info("Normal ayırıcılarla beceri bölme kullanılıyor")
            for line in section_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
            
                # Virgül, noktalı virgül veya bullet ile ayrılmış olabilir
                if ',' in line:
                    skills.extend([s.strip() for s in line.split(',') if s.strip()])
                elif ';' in line:
                    skills.extend([s.strip() for s in line.split(';') if s.strip()])
                elif '•' in line:
                    skills.extend([s.strip() for s in line.split('•') if s.strip()])
                elif ':' in line:
                    # "Skills: Python, Java, JavaScript" formatı
                    parts = line.split(':', 1)
                    if len(parts) == 2 and ',' in parts[1]:
                        skills.extend([s.strip() for s in parts[1].split(',') if s.strip()])
                    elif len(parts) == 2:
                        skills.append(parts[1].strip())
                else:
                    # Tek bir beceri olabilir
                    skills.append(line)
        
        # Becerileri normalize et ve tekrarları kaldır
        normalized_skills = []
        for skill in skills:
            # Çok kısa veya çok uzunsa atla
            if len(skill) < 2 or len(skill) > 50:
                continue
            
            # Noktalama işaretlerini temizle
            skill = skill.strip('.,;:()')
                
            # Büyük/küçük harf normalizasyonu
            if skill.isupper():
                skill = skill.title()
                
            # Tekrarları kontrol et
            if skill not in normalized_skills:
                normalized_skills.append(skill)
        
        logger.info(f"Normalize edilmiş beceriler: {normalized_skills}")        
        return normalized_skills
    
    def _extract_languages(self, section_text: str) -> List[str]:
        """Dil bilgilerini çıkarır"""
        if not section_text:
            # CV'nin tamamında dil bilgisi arayalım
            return []
            
        # Yaygın diller ve seviyeler
        common_languages = ['türkçe', 'turkish', 'ingilizce', 'english', 'almanca', 'german', 'fransızca', 'french', 
                           'ispanyolca', 'spanish', 'rusça', 'russian', 'arapça', 'arabic', 'çince', 'chinese', 'japonca', 'japanese']
                           
        proficiency_levels = ['anadil', 'ana dil', 'native', 'akıcı', 'fluent', 'ileri', 'advanced', 'orta', 'intermediate', 
                             'temel', 'basic', 'başlangıç', 'beginner', 'profesyonel', 'professional',
                             'a1', 'a2', 'b1', 'b2', 'c1', 'c2']
        
        languages = []
        
        # İngilizce ve Türkçe dil bölümleri için özel işleme
        if "LANGUAGES" in section_text.upper() or "LANGUAGE" in section_text.upper() or "DİL" in section_text.upper():
            for line in section_text.split('\n'):
                line_lower = line.lower().strip()
                if "languages" in line_lower or "language" in line_lower or "dil" in line_lower:
                    continue
            
                if not line or len(line) < 3:
                    continue
            
                # Önce dil-seviye formatını kontrol et (İngilizce B2, English Advanced, vb.)
                for lang in common_languages:
                    if lang in line_lower:
                        # Seviye belirtilmiş mi kontrol et
                        level = next((level for level in proficiency_levels if level in line_lower), None)
                        
                        # Büyük/küçük harf düzenlemesi
                        cap_lang = lang.capitalize()
                        
                        if level:
                            if level in ['a1', 'a2', 'b1', 'b2', 'c1', 'c2']:
                                languages.append(f"{cap_lang} ({level.upper()})")
                            else:
                                languages.append(f"{cap_lang} ({level.capitalize()})")
                        else:
                            languages.append(cap_lang)
                        break
                else:
                    # Eğer hiçbir dil eşleşmezse, satırı kontrol et (örn: "English, German, French")
                    words = re.split(r'[,;|/]', line_lower)
                    for word in words:
                        word = word.strip()
                        if word in common_languages:
                            languages.append(word.capitalize())
        else:
            # Normal dil çıkarma
            for line in section_text.split('\n'):
                line_lower = line.lower().strip()
                if not line:
                    continue
            
                # Dil ve seviye eşleşmesi
                for lang in common_languages:
                    if lang in line_lower:
                        # Seviye belirtilmiş mi kontrol et
                        level = next((level for level in proficiency_levels if level in line_lower), None)
                        if level:
                            languages.append(f"{lang.capitalize()} ({level.capitalize()})")
                        else:
                            languages.append(lang.capitalize())
                
        return languages
        
    def _extract_certifications(self, section_text: str) -> List[str]:
        """Sertifikaları çıkarır"""
        if not section_text:
            return []
            
        certifications = []
        
        # Satır bazlı sertifikaları çıkar
        for line in section_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Sertifika olabilecek kelimeleri içeriyor mu kontrol et
            cert_keywords = ['sertifika', 'belge', 'certificate', 'certified', 'credential']
            has_cert_keyword = any(keyword in line.lower() for keyword in cert_keywords)
            
            # Yaygın sertifika vericiler
            common_issuers = ['microsoft', 'aws', 'google', 'oracle', 'ibm', 'cisco', 'comptia', 'pmi']
            has_issuer = any(issuer in line.lower() for issuer in common_issuers)
            
            # Sertifika ise ekle
            if has_cert_keyword or has_issuer:
                certifications.append(line)
            elif len(line) > 10 and line[0].isupper():  # Basit bir heuristik - büyük harfle başlayan uzun cümleler
                certifications.append(line)
                
        return certifications
        
    def _extract_summary(self, section_text: str) -> str:
        """Özet bilgisini çıkarır"""
        if not section_text:
            return ""
            
        # Sadece özet metni döndür
        return section_text.strip()
            
    def match_cv_with_position(self, cv_data: Dict[str, Any], position_data: Dict[str, Any], matching_options: Dict[str, float] = None) -> Dict[str, Any]:
        """
        CV'yi iş pozisyonuyla eşleştirir
        
        Args:
            cv_data (Dict[str, Any]): CV verisi
            position_data (Dict[str, Any]): İş pozisyonu verisi
            matching_options (Dict[str, float], optional): Eşleştirme seçenekleri
            
        Returns:
            Dict[str, Any]: Eşleştirme sonuçları
        """
        logger.info(f"CV ve pozisyon eşleştirmesi başlatılıyor")
        
        if matching_options is None:
            matching_options = {
                'skill_weight': 0.4,
                'experience_weight': 0.3,
                'education_weight': 0.2,
                'language_weight': 0.05,
                'certification_weight': 0.05
            }
            
        # Beceri eşleşmesi
        skill_score = self._calculate_skill_match(cv_data.get('skills', []), position_data.get('requirements', {}).get('skills', []))
        
        # Deneyim eşleşmesi
        experience_score = self._calculate_experience_match(cv_data.get('experience', []), position_data.get('requirements', {}).get('experience', {}))
        
        # Eğitim eşleşmesi
        education_score = self._calculate_education_match(cv_data.get('education', []), position_data.get('requirements', {}).get('education', {}))
        
        # Dil eşleşmesi
        language_score = self._calculate_language_match(cv_data.get('languages', []), position_data.get('requirements', {}).get('languages', []))
        
        # Sertifika eşleşmesi
        certification_score = self._calculate_certification_match(cv_data.get('certifications', []), position_data.get('requirements', {}).get('certifications', []))
        
        # Ağırlıklı toplam skor
        total_score = (
            skill_score * matching_options['skill_weight'] +
            experience_score * matching_options['experience_weight'] +
            education_score * matching_options['education_weight'] +
            language_score * matching_options['language_weight'] +
            certification_score * matching_options['certification_weight']
        )
        
        # Güçlü ve zayıf yönleri belirle
        strengths = []
        weaknesses = []
        
        # Beceri güçlü/zayıf yönleri
        if skill_score >= 0.8:
            strengths.append("Beceri setinin pozisyonla çok iyi uyumu")
        elif skill_score <= 0.4:
            weaknesses.append("Gerekli beceriler eksik")
            
        # Deneyim güçlü/zayıf yönleri
        if experience_score >= 0.8:
            strengths.append("Pozisyon için yeterli deneyim")
        elif experience_score <= 0.4:
            weaknesses.append("Pozisyon için deneyim eksikliği")
            
        # Eğitim güçlü/zayıf yönleri
        if education_score >= 0.8:
            strengths.append("Eğitim geçmişi pozisyonla uyumlu")
        elif education_score <= 0.4:
            weaknesses.append("Pozisyon için gerekli eğitim eksik")
            
        # Sonuçları döndür
        match_result = {
            'match_score': total_score,
            'category_scores': {
                'skills': skill_score,
                'experience': experience_score,
                'education': education_score,
                'languages': language_score,
                'certifications': certification_score
            },
            'strengths': strengths,
            'weaknesses': weaknesses,
            'recommendations': self._generate_recommendations(total_score, strengths, weaknesses)
        }
        
        logger.info(f"Eşleştirme tamamlandı, skor: {total_score:.2f}")
        return match_result
    
    def _calculate_skill_match(self, cv_skills: List[str], required_skills: List[str]) -> float:
        """Beceri eşleşme skorunu hesaplar"""
        if not required_skills:
            return 1.0  # Gerekli beceri yoksa tam puan
            
        # CV becerilerini ve gerekli becerileri küçük harfe çevir
        cv_skills_lower = [skill.lower() for skill in cv_skills]
        required_skills_lower = [skill.lower() for skill in required_skills]
        
        # Eşleşen becerileri say
        matches = sum(1 for skill in required_skills_lower if any(skill in cv_skill for cv_skill in cv_skills_lower))
        
        # Skor hesapla
        return matches / len(required_skills)
    
    def _calculate_experience_match(self, cv_experience: List[Dict[str, Any]], required_experience: Dict[str, Any]) -> float:
        """Deneyim eşleşme skorunu hesaplar"""
        if not required_experience:
            return 1.0  # Gerekli deneyim yoksa tam puan
            
        # Toplam deneyim yılını hesapla
        total_years = 0
        for exp in cv_experience:
            start_year = int(exp.get('start_date', 0)) if exp.get('start_date') else 0
            end_year = int(exp.get('end_date', date.today().year)) if exp.get('end_date') else date.today().year
            total_years += max(0, end_year - start_year)
            
        # Gerekli minimum deneyim
        min_years = required_experience.get('min_years', 0)
        
        # Deneyim skoru hesapla (maksimum 1.0)
        return min(1.0, total_years / max(1, min_years))
    
    def _calculate_education_match(self, cv_education: List[Dict[str, Any]], required_education: Dict[str, Any]) -> float:
        """Eğitim eşleşme skorunu hesaplar"""
        if not required_education:
            return 1.0  # Gerekli eğitim yoksa tam puan
            
        # Eğitim seviyelerini sayısal değerlere dönüştür
        education_levels = {
            'lise': 1,
            'önlisans': 2,
            'lisans': 3,
            'yüksek lisans': 4,
            'doktora': 5
        }
        
        # Gerekli minimum eğitim seviyesi
        required_level = education_levels.get(required_education.get('min_level', '').lower(), 0)
        
        # CV'deki en yüksek eğitim seviyesini bul
        cv_max_level = 0
        for edu in cv_education:
            level = education_levels.get(edu.get('degree', '').lower(), 0)
            cv_max_level = max(cv_max_level, level)
            
        # Eğitim skoru hesapla
        if required_level == 0:
            return 1.0
        elif cv_max_level == 0:
            return 0.0
        elif cv_max_level >= required_level:
            return 1.0
        else:
            return cv_max_level / required_level
    
    def _calculate_language_match(self, cv_languages: List[str], required_languages: List[str]) -> float:
        """Dil eşleşme skorunu hesaplar"""
        if not required_languages:
            return 1.0  # Gerekli dil yoksa tam puan
            
        # CV dillerini ve gerekli dilleri küçük harfe çevir
        cv_languages_lower = [lang.lower() for lang in cv_languages]
        required_languages_lower = [lang.lower() for lang in required_languages]
        
        # Eşleşen dilleri say
        matches = sum(1 for lang in required_languages_lower if any(lang in cv_lang for cv_lang in cv_languages_lower))
        
        # Skor hesapla
        return matches / len(required_languages)
    
    def _calculate_certification_match(self, cv_certifications: List[str], required_certifications: List[str]) -> float:
        """Sertifika eşleşme skorunu hesaplar"""
        if not required_certifications:
            return 1.0  # Gerekli sertifika yoksa tam puan
            
        # CV sertifikalarını ve gerekli sertifikaları küçük harfe çevir
        cv_certifications_lower = [cert.lower() for cert in cv_certifications]
        required_certifications_lower = [cert.lower() for cert in required_certifications]
        
        # Eşleşen sertifikaları say
        matches = sum(1 for cert in required_certifications_lower if any(cert in cv_cert for cv_cert in cv_certifications_lower))
        
        # Skor hesapla
        return matches / len(required_certifications)
    
    def _generate_recommendations(self, total_score: float, strengths: List[str], weaknesses: List[str]) -> List[str]:
        """Adaya öneriler oluşturur"""
        recommendations = []
        
        if total_score < 0.5:
            recommendations.append("Başvurulan pozisyon için gerekli beceri ve deneyimleri geliştirmek önerilir")
            
        if "Gerekli beceriler eksik" in weaknesses:
            recommendations.append("Pozisyon için gerekli teknik becerileri edinmek için eğitim veya kurslar alınabilir")
            
        if "Pozisyon için deneyim eksikliği" in weaknesses:
            recommendations.append("Benzer alanlarda proje veya gönüllü çalışmalarla deneyim kazanılabilir")
            
        if "Pozisyon için gerekli eğitim eksik" in weaknesses:
            recommendations.append("İlgili alanda eğitim veya sertifika programları değerlendirilebilir")
            
        return recommendations 