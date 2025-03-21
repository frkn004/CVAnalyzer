from typing import Optional, Dict, Any, List
from pathlib import Path
import PyPDF2
from docx import Document
import os
import re
from datetime import date
from functools import lru_cache
from ..models.cv_models import CV, PersonalInfo, Education, Experience

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
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ' '.join([page.extract_text() for page in reader.pages])
                    
            elif file_path.suffix == '.docx':
                doc = Document(file_path)
                text = ' '.join([paragraph.text for paragraph in doc.paragraphs])
                
            # Önbelleğe kaydet
            self._text_cache[cache_key] = text
            return text
                
        except Exception as e:
            raise ValueError(f"Dosya okuma hatası: {str(e)}")
            
    @lru_cache(maxsize=100)
    def analyze_cv(self, text: str) -> Dict[str, Any]:
        """
        CV metnini analiz eder
        
        Args:
            text (str): CV metni
            
        Returns:
            Dict[str, Any]: Analiz sonuçları
        """
        # Önbellekte varsa döndür
        cache_key = hash(text)
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
            
        # Metni temizle ve bölümlere ayır
        text = self._clean_text(text)
        sections = self._split_into_sections(text)
        
        # Kişisel bilgileri çıkar
        personal_info = self._extract_personal_info(sections.get('personal', ''))
        
        # Eğitim bilgilerini çıkar
        education = self._extract_education(sections.get('education', ''))
        
        # İş deneyimlerini çıkar
        experience = self._extract_experience(sections.get('experience', ''))
        
        # Becerileri çıkar
        skills = self._extract_skills(text)
        
        # Dil bilgilerini çıkar
        languages = self._extract_languages(text)
        
        # Sertifikaları çıkar
        certifications = self._extract_certifications(text)
        
        # Özet bilgisini çıkar
        summary = self._extract_summary(sections.get('summary', ''))
        
        # CV nesnesini oluştur
        cv = CV(
            personal_info=personal_info,
            education=education,
            experience=experience,
            skills=skills,
            languages=languages,
            certifications=certifications,
            summary=summary
        )
        
        result = cv.model_dump()
        
        # Önbelleğe kaydet
        self._analysis_cache[cache_key] = result
        return result
        
    def clear_cache(self):
        """Önbelleği temizler"""
        self._text_cache.clear()
        self._analysis_cache.clear()
        self.extract_text.cache_clear()
        self.analyze_cv.cache_clear()
        
    def _clean_text(self, text: str) -> str:
        """Metni temizler ve normalleştirir"""
        # Gereksiz boşlukları temizle
        text = re.sub(r'\s+', ' ', text)
        
        # Özel karakterleri temizle
        text = re.sub(r'[^\w\s@.,-]', '', text)
        
        # Metin normalizasyonu
        text = text.strip()
        text = re.sub(r'\n+', '\n', text)
        
        return text
        
    def _split_into_sections(self, text: str) -> Dict[str, str]:
        """Metni bölümlere ayırır"""
        sections = {}
        
        # Bölüm başlıkları
        section_headers = {
            'personal': r'(?i)(kişisel|personal|about|hakkında)',
            'education': r'(?i)(eğitim|education|öğrenim)',
            'experience': r'(?i)(deneyim|experience|iş|work)',
            'skills': r'(?i)(beceriler|skills|yetenekler)',
            'languages': r'(?i)(diller|languages)',
            'certifications': r'(?i)(sertifikalar|certifications)',
            'summary': r'(?i)(özet|summary)'
        }
        
        # Her bölüm için metni ayır
        current_section = 'personal'
        current_text = []
        
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Yeni bölüm başlığı kontrolü
            for section, pattern in section_headers.items():
                if re.search(pattern, line):
                    sections[current_section] = '\n'.join(current_text)
                    current_section = section
                    current_text = []
                    break
            else:
                current_text.append(line)
                
        # Son bölümü ekle
        if current_text:
            sections[current_section] = '\n'.join(current_text)
            
        return sections
        
    def _extract_personal_info(self, text: str) -> PersonalInfo:
        """Kişisel bilgileri çıkarır"""
        lines = text.split('\n')
        name = lines[0].strip() if lines else ""
        
        # E-posta ara
        email = ""
        email_pattern = r'[\w\.-]+@[\w\.-]+'
        email_matches = re.findall(email_pattern, text)
        if email_matches:
            email = email_matches[0]
            
        # Telefon ara
        phone = ""
        phone_pattern = r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}'
        phone_matches = re.findall(phone_pattern, text)
        if phone_matches:
            phone = phone_matches[0]
            
        # Konum ara
        location = ""
        location_keywords = ['istanbul', 'ankara', 'izmir', 'bursa', 'antalya']
        for line in lines:
            if any(keyword in line.lower() for keyword in location_keywords):
                location = line.strip()
                break
                
        return PersonalInfo(
            name=name,
            email=email,
            phone=phone,
            location=location
        )
        
    def _extract_education(self, text: str) -> List[Education]:
        """Eğitim bilgilerini çıkarır"""
        education = []
        lines = text.split('\n')
        
        current_edu = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_edu:
                    education.append(Education(**current_edu))
                    current_edu = {}
                continue
                
            # Tarih kontrolü
            date_match = re.search(r'(\d{4})[-–](\d{4})', line)
            if date_match:
                current_edu['start_date'] = date_match.group(1)
                current_edu['end_date'] = date_match.group(2)
                continue
                
            # Kurum ve bölüm kontrolü
            if 'üniversite' in line.lower() or 'university' in line.lower():
                current_edu['institution'] = line
                current_edu['degree'] = 'Lisans'  # Varsayılan
                current_edu['field_of_study'] = 'Belirtilmemiş'
                
        # Son eğitim bilgisini ekle
        if current_edu:
            education.append(Education(**current_edu))
            
        return education
        
    def _extract_experience(self, text: str) -> List[Experience]:
        """İş deneyimlerini çıkarır"""
        experience = []
        lines = text.split('\n')
        
        current_exp = {}
        responsibilities = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_exp and responsibilities:
                    current_exp['responsibilities'] = responsibilities
                    experience.append(Experience(**current_exp))
                    current_exp = {}
                    responsibilities = []
                continue
                
            # Tarih kontrolü
            date_match = re.search(r'(\d{4})[-–](\d{4})', line)
            if date_match:
                current_exp['start_date'] = date_match.group(1)
                current_exp['end_date'] = date_match.group(2)
                continue
                
            # Şirket ve pozisyon kontrolü
            if any(keyword in line.lower() for keyword in ['şirket', 'sirket', 'company', 'firma']):
                parts = line.split('-')
                if len(parts) >= 2:
                    current_exp['company'] = parts[0].strip()
                    current_exp['position'] = parts[1].strip()
                continue
                
            # Sorumluluklar
            if line.startswith('-'):
                responsibilities.append(line[1:].strip())
                
        # Son deneyim bilgisini ekle
        if current_exp and responsibilities:
            current_exp['responsibilities'] = responsibilities
            experience.append(Experience(**current_exp))
            
        return experience
        
    def _extract_skills(self, text: str) -> List[str]:
        """Becerileri çıkarır"""
        # Yaygın programlama dilleri ve teknolojiler
        common_skills = [
            'python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'git', 'jenkins', 'jira', 'agile', 'scrum',
            'linux', 'unix', 'windows', 'macos',
            'html', 'css', 'react', 'angular', 'vue', 'node.js',
            'machine learning', 'deep learning', 'ai', 'data science',
            'rest', 'soap', 'graphql', 'api', 'microservices'
        ]
        
        skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill in text_lower:
                skills.append(skill.capitalize())
                
        return skills
        
    def _extract_languages(self, text: str) -> List[str]:
        """Dil bilgilerini çıkarır"""
        languages = []
        language_pattern = r'(?i)(english|ingilizce|türkçe|turkish|almanca|german|fransızca|french)'
        matches = re.findall(language_pattern, text)
        
        for match in matches:
            if match.lower() in ['english', 'ingilizce']:
                languages.append('İngilizce')
            elif match.lower() in ['türkçe', 'turkish']:
                languages.append('Türkçe')
            elif match.lower() in ['almanca', 'german']:
                languages.append('Almanca')
            elif match.lower() in ['fransızca', 'french']:
                languages.append('Fransızca')
                
        return languages
        
    def _extract_certifications(self, text: str) -> List[str]:
        """Sertifikaları çıkarır"""
        certifications = []
        cert_pattern = r'(?i)(aws|azure|gcp|cisco|microsoft|oracle|pmi|scrum|agile)'
        matches = re.findall(cert_pattern, text)
        
        for match in matches:
            if match.lower() in ['aws']:
                certifications.append('AWS Sertifikaları')
            elif match.lower() in ['azure']:
                certifications.append('Azure Sertifikaları')
            elif match.lower() in ['gcp']:
                certifications.append('Google Cloud Sertifikaları')
            elif match.lower() in ['cisco']:
                certifications.append('Cisco Sertifikaları')
            elif match.lower() in ['microsoft']:
                certifications.append('Microsoft Sertifikaları')
            elif match.lower() in ['pmi']:
                certifications.append('PMI Sertifikaları')
            elif match.lower() in ['scrum', 'agile']:
                certifications.append('Agile/Scrum Sertifikaları')
                
        return certifications
        
    def _extract_summary(self, text: str) -> Optional[str]:
        """Özet bilgisini çıkarır"""
        if not text:
            return None
            
        # İlk 3 cümleyi al
        sentences = re.split(r'[.!?]+', text)
        summary = '. '.join(sentences[:3])
        
        return summary.strip() if summary else None 