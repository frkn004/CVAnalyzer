from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, Any, List, Optional, Tuple
import os
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from ..processors.document_processor import DocumentProcessor
from ..models.cv_models import CV
from ..core.platform_config import PlatformConfig
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI(
    title="CV Analiz API",
    description="CV dosyalarını analiz eden ve iş tanımlarıyla eşleştiren API",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Geçici dosya dizini
UPLOAD_DIR = Path("temp_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Belge işlemci ve platform yapılandırması
document_processor = DocumentProcessor()
platform_config = PlatformConfig()

class FilterOptions(BaseModel):
    min_experience_years: Optional[int] = None
    required_skills: Optional[List[str]] = None
    education_level: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[Tuple[float, float]] = None
    work_type: Optional[str] = None
    languages: Optional[List[str]] = None
    certifications: Optional[List[str]] = None

class SearchOptions(BaseModel):
    sort_by: Optional[str] = "match_score"
    sort_order: Optional[str] = "descending"
    min_match_score: Optional[float] = 0.0
    required_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None

class MatchingOptions(BaseModel):
    skill_weight: float = 0.4
    experience_weight: float = 0.3
    education_weight: float = 0.2
    language_weight: float = 0.05
    certification_weight: float = 0.05

class BatchAnalysisOptions(BaseModel):
    filter_options: Optional[FilterOptions] = None
    search_options: Optional[SearchOptions] = None
    generate_report: bool = True
    generate_visualizations: bool = True

class ComparisonOptions(BaseModel):
    comparison_fields: List[str] = ["skills", "experience", "education"]
    generate_charts: bool = True
    export_format: str = "pdf"

class ReportOptions(BaseModel):
    report_type: str = "detailed"  # detailed, summary, custom
    include_charts: bool = True
    include_statistics: bool = True
    export_format: str = "pdf"

class StatisticalAnalysis(BaseModel):
    skill_distribution: Dict[str, float]
    experience_distribution: Dict[str, int]
    education_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    average_match_scores: Dict[str, float]

@app.get("/")
async def root():
    """Kök endpoint"""
    return {
        "status": "active",
        "system_info": platform_config.get_system_info()
    }

@app.post("/analyze-cv", response_model=CV)
async def analyze_cv(
    file: UploadFile = File(...),
    filter_options: Optional[FilterOptions] = None
) -> Dict[str, Any]:
    """
    CV dosyasını analiz eder
    
    Args:
        file (UploadFile): Yüklenen CV dosyası
        filter_options (FilterOptions, optional): Filtreleme seçenekleri
        
    Returns:
        Dict[str, Any]: Analiz sonuçları
    """
    file_path = None
    try:
        # Dosyayı geçici dizine kaydet
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Metni çıkar
        text = document_processor.extract_text(str(file_path))
        
        # CV'yi analiz et
        result = document_processor.analyze_cv(text)
        
        # Filtreleme uygula
        if filter_options:
            result = _apply_filters(result, filter_options)
        
        # Geçici dosyayı sil
        if file_path and file_path.exists():
            file_path.unlink()
        
        return result
        
    except Exception as e:
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/match-cv")
async def match_cv(
    file: UploadFile = File(...),
    position: str = Form(...),
    filter_options: Optional[FilterOptions] = None,
    search_options: Optional[SearchOptions] = None,
    matching_options: Optional[MatchingOptions] = None
) -> Dict[str, Any]:
    """
    CV'yi iş tanımıyla eşleştirir
    
    Args:
        file (UploadFile): Yüklenen CV dosyası
        position (str): İş tanımı (JSON formatında)
        filter_options (FilterOptions, optional): Filtreleme seçenekleri
        search_options (SearchOptions, optional): Arama seçenekleri
        matching_options (MatchingOptions, optional): Eşleştirme seçenekleri
        
    Returns:
        Dict[str, Any]: Eşleştirme sonuçları
    """
    file_path = None
    try:
        # Pozisyon verisini JSON'dan dict'e çevir
        try:
            position_data = json.loads(position)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Geçersiz pozisyon verisi")
            
        # Gerekli alanları kontrol et
        required_fields = ["title", "description", "requirements"]
        if not all(field in position_data for field in required_fields):
            raise HTTPException(status_code=400, detail="Geçersiz pozisyon verisi")
            
        # Dosyayı geçici dizine kaydet
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
            
        # Metni çıkar
        text = document_processor.extract_text(str(file_path))
        
        # CV'yi analiz et
        cv_data = document_processor.analyze_cv(text)
        
        # Filtreleme uygula
        if filter_options:
            cv_data = _apply_filters(cv_data, filter_options)
            
        # Eşleştirme yap
        result = {
            "match_score": 0.85,  # TODO: Gerçek eşleştirme yapılacak
            "category_scores": {
                "skills": 0.9,
                "experience": 0.8,
                "education": 0.85
            },
            "strengths": [
                "Python ve FastAPI deneyimi",
                "Docker ve Kubernetes bilgisi"
            ],
            "weaknesses": [
                "AWS deneyimi eksik"
            ],
            "recommendations": [
                "AWS sertifikasyonu alınabilir",
                "Cloud teknolojileri üzerine çalışılabilir"
            ]
        }
        
        # Arama seçeneklerini uygula
        if search_options:
            result = _apply_search_options(result, search_options)
            
        # Geçici dosyayı sil
        if file_path and file_path.exists():
            file_path.unlink()
        
        return result
        
    except Exception as e:
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    """API sağlık kontrolü"""
    return {"status": "healthy"}

def _apply_filters(cv_data: Dict[str, Any], filter_options: FilterOptions) -> Dict[str, Any]:
    """Filtreleme seçeneklerini uygular"""
    # Deneyim yılı kontrolü
    if filter_options.min_experience_years:
        total_experience = sum(
            int(exp.get('end_date', '2024')) - int(exp.get('start_date', '2024'))
            for exp in cv_data.get('experience', [])
        )
        if total_experience < filter_options.min_experience_years:
            raise HTTPException(status_code=400, detail="Yetersiz deneyim")
            
    # Gerekli beceriler kontrolü
    if filter_options.required_skills:
        cv_skills = set(skill.lower() for skill in cv_data.get('skills', []))
        required_skills = set(skill.lower() for skill in filter_options.required_skills)
        if not required_skills.issubset(cv_skills):
            raise HTTPException(status_code=400, detail="Eksik beceriler")
            
    # Eğitim seviyesi kontrolü
    if filter_options.education_level:
        education_levels = {
            'lisans': ['lisans', 'bachelor'],
            'yüksek lisans': ['yüksek lisans', 'master'],
            'doktora': ['doktora', 'phd']
        }
        cv_education = [edu.get('degree', '').lower() for edu in cv_data.get('education', [])]
        if not any(level in edu for edu in cv_education for level in education_levels.get(filter_options.education_level.lower(), [])):
            raise HTTPException(status_code=400, detail="Yetersiz eğitim seviyesi")
            
    # Konum kontrolü
    if filter_options.location:
        cv_location = cv_data.get('personal_info', {}).get('location', '').lower()
        if filter_options.location.lower() not in cv_location:
            raise HTTPException(status_code=400, detail="Uygun olmayan konum")
            
    # Dil kontrolü
    if filter_options.languages:
        cv_languages = set(lang.lower() for lang in cv_data.get('languages', []))
        required_languages = set(lang.lower() for lang in filter_options.languages)
        if not required_languages.issubset(cv_languages):
            raise HTTPException(status_code=400, detail="Eksik dil bilgisi")
            
    # Sertifika kontrolü
    if filter_options.certifications:
        cv_certifications = set(cert.lower() for cert in cv_data.get('certifications', []))
        required_certifications = set(cert.lower() for cert in filter_options.certifications)
        if not required_certifications.issubset(cv_certifications):
            raise HTTPException(status_code=400, detail="Eksik sertifikalar")
            
    return cv_data

def _apply_search_options(result: Dict[str, Any], search_options: SearchOptions) -> Dict[str, Any]:
    """Arama seçeneklerini uygular"""
    # Minimum eşleşme skoru kontrolü
    if search_options.min_match_score and result['match_score'] < search_options.min_match_score:
        raise HTTPException(status_code=400, detail="Yetersiz eşleşme skoru")
        
    # Anahtar kelime kontrolü
    if search_options.required_keywords:
        text = ' '.join(str(v) for v in result.values())
        if not all(keyword.lower() in text.lower() for keyword in search_options.required_keywords):
            raise HTTPException(status_code=400, detail="Eksik anahtar kelimeler")
            
    # Hariç tutulan kelimeler kontrolü
    if search_options.exclude_keywords:
        text = ' '.join(str(v) for v in result.values())
        if any(keyword.lower() in text.lower() for keyword in search_options.exclude_keywords):
            raise HTTPException(status_code=400, detail="Hariç tutulan kelimeler mevcut")
            
    return result 

@app.post("/analyze-batch")
async def analyze_batch_cvs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    options: BatchAnalysisOptions = None
) -> Dict[str, Any]:
    """
    Birden fazla CV'yi toplu olarak analiz eder
    
    Args:
        background_tasks (BackgroundTasks): Arka plan görevleri
        files (List[UploadFile]): Yüklenen CV dosyaları
        options (BatchAnalysisOptions): Analiz seçenekleri
        
    Returns:
        Dict[str, Any]: Toplu analiz sonuçları
    """
    results = []
    file_paths = []
    
    try:
        # Dosyaları geçici dizine kaydet
        for file in files:
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            file_paths.append(file_path)
            
        # Paralel analiz yap
        async def analyze_single_cv(file_path: Path) -> Dict[str, Any]:
            text = document_processor.extract_text(str(file_path))
            result = document_processor.analyze_cv(text)
            if options and options.filter_options:
                result = _apply_filters(result, options.filter_options)
            return result
            
        tasks = [analyze_single_cv(path) for path in file_paths]
        results = await asyncio.gather(*tasks)
        
        # İstatistiksel analiz yap
        stats = _calculate_statistics(results)
        
        # Rapor ve görselleştirme oluştur
        if options and options.generate_report:
            background_tasks.add_task(
                _generate_batch_report,
                results,
                stats,
                options.generate_visualizations
            )
        
        return {
            "total_cvs": len(results),
            "analysis_results": results,
            "statistics": stats
        }
        
    finally:
        # Geçici dosyaları temizle
        for path in file_paths:
            if path.exists():
                path.unlink()

@app.post("/compare-cvs")
async def compare_cvs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    options: ComparisonOptions = None
) -> Dict[str, Any]:
    """
    Birden fazla CV'yi karşılaştırır
    
    Args:
        background_tasks (BackgroundTasks): Arka plan görevleri
        files (List[UploadFile]): Karşılaştırılacak CV'ler
        options (ComparisonOptions): Karşılaştırma seçenekleri
        
    Returns:
        Dict[str, Any]: Karşılaştırma sonuçları
    """
    results = []
    file_paths = []
    
    try:
        # Dosyaları geçici dizine kaydet
        for file in files:
            file_path = UPLOAD_DIR / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            file_paths.append(file_path)
            
        # CV'leri analiz et
        for path in file_paths:
            text = document_processor.extract_text(str(path))
            result = document_processor.analyze_cv(text)
            results.append(result)
            
        # Karşılaştırma yap
        comparison = _compare_cv_data(results, options)
        
        # Görselleştirme oluştur
        if options and options.generate_charts:
            background_tasks.add_task(
                _generate_comparison_charts,
                comparison,
                options.export_format
            )
            
        return comparison
        
    finally:
        # Geçici dosyaları temizle
        for path in file_paths:
            if path.exists():
                path.unlink()

@app.post("/generate-report")
async def generate_report(
    background_tasks: BackgroundTasks,
    cv_data: Dict[str, Any],
    options: ReportOptions = None
) -> Dict[str, Any]:
    """
    CV analizi için detaylı rapor oluşturur
    
    Args:
        background_tasks (BackgroundTasks): Arka plan görevleri
        cv_data (Dict[str, Any]): CV analiz verisi
        options (ReportOptions): Rapor seçenekleri
        
    Returns:
        Dict[str, Any]: Rapor sonuçları
    """
    try:
        # Rapor oluştur
        report = _generate_detailed_report(cv_data, options)
        
        # Görselleştirme oluştur
        if options and options.include_charts:
            background_tasks.add_task(
                _generate_report_charts,
                cv_data,
                options.export_format
            )
            
        return report
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _calculate_statistics(results: List[Dict[str, Any]]) -> StatisticalAnalysis:
    """CV sonuçları için istatistiksel analiz yapar"""
    stats = {
        "skill_distribution": {},
        "experience_distribution": {},
        "education_distribution": {},
        "language_distribution": {},
        "average_match_scores": {}
    }
    
    # Beceri dağılımı
    all_skills = []
    for result in results:
        all_skills.extend(result.get('skills', []))
    skill_counts = pd.Series(all_skills).value_counts()
    stats["skill_distribution"] = skill_counts.to_dict()
    
    # Deneyim dağılımı
    experience_years = []
    for result in results:
        total_exp = sum(
            int(exp.get('end_date', '2024')) - int(exp.get('start_date', '2024'))
            for exp in result.get('experience', [])
        )
        experience_years.append(total_exp)
    stats["experience_distribution"] = {
        "min": min(experience_years),
        "max": max(experience_years),
        "average": sum(experience_years) / len(experience_years)
    }
    
    # Eğitim dağılımı
    education_levels = []
    for result in results:
        for edu in result.get('education', []):
            education_levels.append(edu.get('degree', ''))
    stats["education_distribution"] = pd.Series(education_levels).value_counts().to_dict()
    
    # Dil dağılımı
    all_languages = []
    for result in results:
        all_languages.extend(result.get('languages', []))
    stats["language_distribution"] = pd.Series(all_languages).value_counts().to_dict()
    
    return StatisticalAnalysis(**stats)

def _compare_cv_data(results: List[Dict[str, Any]], options: ComparisonOptions) -> Dict[str, Any]:
    """CV'leri karşılaştırır"""
    comparison = {
        "field_comparisons": {},
        "similarity_scores": {},
        "unique_features": {}
    }
    
    # Alan karşılaştırmaları
    for field in options.comparison_fields:
        field_data = [result.get(field, []) for result in results]
        comparison["field_comparisons"][field] = {
            "common": list(set.intersection(*map(set, field_data))),
            "unique": list(set.union(*map(set, field_data)) - set.intersection(*map(set, field_data)))
        }
    
    # Benzerlik skorları
    for i, result1 in enumerate(results):
        for j, result2 in enumerate(results[i+1:], i+1):
            similarity = _calculate_similarity(result1, result2)
            comparison["similarity_scores"][f"cv_{i}_cv_{j}"] = similarity
    
    # Benzersiz özellikler
    for i, result in enumerate(results):
        comparison["unique_features"][f"cv_{i}"] = {
            field: result.get(field, [])
            for field in options.comparison_fields
            if result.get(field, [])
        }
    
    return comparison

def _calculate_similarity(cv1: Dict[str, Any], cv2: Dict[str, Any]) -> float:
    """İki CV arasındaki benzerlik skorunu hesaplar"""
    # Beceri benzerliği
    skills1 = set(cv1.get('skills', []))
    skills2 = set(cv2.get('skills', []))
    skill_similarity = len(skills1.intersection(skills2)) / len(skills1.union(skills2))
    
    # Deneyim benzerliği
    exp1 = set(exp.get('company', '') for exp in cv1.get('experience', []))
    exp2 = set(exp.get('company', '') for exp in cv2.get('experience', []))
    exp_similarity = len(exp1.intersection(exp2)) / len(exp1.union(exp2))
    
    # Eğitim benzerliği
    edu1 = set(edu.get('school', '') for edu in cv1.get('education', []))
    edu2 = set(edu.get('school', '') for edu in cv2.get('education', []))
    edu_similarity = len(edu1.intersection(edu2)) / len(edu1.union(edu2))
    
    # Ağırlıklı ortalama
    return (skill_similarity * 0.4 + exp_similarity * 0.4 + edu_similarity * 0.2)

def _generate_batch_report(results: List[Dict[str, Any]], stats: StatisticalAnalysis, include_charts: bool):
    """Toplu analiz raporu oluşturur"""
    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"batch_report_{timestamp}.pdf"
    
    # Rapor içeriği oluştur
    report_content = {
        "summary": {
            "total_cvs": len(results),
            "average_experience": stats.experience_distribution["average"],
            "top_skills": dict(list(stats.skill_distribution.items())[:10]),
            "top_languages": dict(list(stats.language_distribution.items())[:5])
        },
        "detailed_results": results,
        "statistics": stats.dict()
    }
    
    # Görselleştirme oluştur
    if include_charts:
        _create_visualization_charts(stats, report_dir / f"charts_{timestamp}")
    
    # PDF raporu oluştur
    _generate_pdf_report(report_content, report_path)

def _generate_comparison_charts(comparison: Dict[str, Any], export_format: str):
    """Karşılaştırma grafikleri oluşturur"""
    charts_dir = Path("charts")
    charts_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Beceri karşılaştırma grafiği
    plt.figure(figsize=(12, 6))
    skills_data = comparison["field_comparisons"]["skills"]
    plt.bar(["Ortak", "Benzersiz"], [len(skills_data["common"]), len(skills_data["unique"])])
    plt.title("Beceri Karşılaştırması")
    plt.savefig(charts_dir / f"skills_comparison_{timestamp}.png")
    plt.close()
    
    # Benzerlik skoru grafiği
    plt.figure(figsize=(10, 6))
    similarity_scores = list(comparison["similarity_scores"].values())
    plt.hist(similarity_scores, bins=10)
    plt.title("CV Benzerlik Skorları Dağılımı")
    plt.xlabel("Benzerlik Skoru")
    plt.ylabel("CV Çifti Sayısı")
    plt.savefig(charts_dir / f"similarity_distribution_{timestamp}.png")
    plt.close()

def _generate_detailed_report(cv_data: Dict[str, Any], options: ReportOptions) -> Dict[str, Any]:
    """Detaylı CV raporu oluşturur"""
    report = {
        "personal_info": cv_data.get("personal_info", {}),
        "summary": {
            "total_experience": sum(
                int(exp.get('end_date', '2024')) - int(exp.get('start_date', '2024'))
                for exp in cv_data.get('experience', [])
            ),
            "education_level": max(
                (edu.get('degree', '') for edu in cv_data.get('education', [])),
                key=len
            ) if cv_data.get('education') else "",
            "skill_count": len(cv_data.get('skills', [])),
            "language_count": len(cv_data.get('languages', []))
        },
        "detailed_analysis": {
            "skills": {
                "technical": [s for s in cv_data.get('skills', []) if any(tech in s.lower() for tech in ['python', 'java', 'javascript', 'sql'])],
                "soft": [s for s in cv_data.get('skills', []) if any(soft in s.lower() for soft in ['iletişim', 'liderlik', 'takım', 'problem'])],
                "certifications": cv_data.get('certifications', [])
            },
            "experience": {
                "total_years": sum(
                    int(exp.get('end_date', '2024')) - int(exp.get('start_date', '2024'))
                    for exp in cv_data.get('experience', [])
                ),
                "companies": [exp.get('company', '') for exp in cv_data.get('experience', [])],
                "roles": [exp.get('position', '') for exp in cv_data.get('experience', [])]
            },
            "education": {
                "degrees": [edu.get('degree', '') for edu in cv_data.get('education', [])],
                "schools": [edu.get('school', '') for edu in cv_data.get('education', [])],
                "fields": [edu.get('field', '') for edu in cv_data.get('education', [])]
            }
        }
    }
    
    return report

def _create_visualization_charts(stats: StatisticalAnalysis, output_dir: Path):
    """İstatistiksel görselleştirmeler oluşturur"""
    output_dir.mkdir(exist_ok=True)
    
    # Beceri dağılımı grafiği
    plt.figure(figsize=(12, 6))
    skills_df = pd.DataFrame(list(stats.skill_distribution.items()), columns=['Skill', 'Count'])
    skills_df = skills_df.nlargest(10, 'Count')
    sns.barplot(data=skills_df, x='Count', y='Skill')
    plt.title("En Yaygın 10 Beceri")
    plt.savefig(output_dir / "top_skills.png")
    plt.close()
    
    # Deneyim dağılımı grafiği
    plt.figure(figsize=(10, 6))
    exp_data = stats.experience_distribution
    plt.bar(exp_data.keys(), exp_data.values())
    plt.title("Deneyim Dağılımı")
    plt.xlabel("Yıl")
    plt.ylabel("CV Sayısı")
    plt.savefig(output_dir / "experience_distribution.png")
    plt.close()
    
    # Dil dağılımı grafiği
    plt.figure(figsize=(10, 6))
    languages_df = pd.DataFrame(list(stats.language_distribution.items()), columns=['Language', 'Count'])
    sns.barplot(data=languages_df, x='Count', y='Language')
    plt.title("Dil Dağılımı")
    plt.savefig(output_dir / "language_distribution.png")
    plt.close()

def _generate_pdf_report(content: Dict[str, Any], output_path: Path):
    """PDF raporu oluşturur"""
    # TODO: PDF oluşturma işlemi eklenecek
    pass 

def _generate_report_charts(cv_data: Dict[str, Any], export_format: str):
    """Rapor grafiklerini oluşturur"""
    charts_dir = Path("charts")
    charts_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Beceri dağılımı grafiği
    plt.figure(figsize=(12, 6))
    skills = cv_data.get('skills', [])
    skill_counts = pd.Series(skills).value_counts()
    skill_counts = skill_counts.nlargest(10)
    sns.barplot(x=skill_counts.values, y=skill_counts.index)
    plt.title("En Yaygın 10 Beceri")
    plt.savefig(charts_dir / f"skills_distribution_{timestamp}.png")
    plt.close()
    
    # Deneyim dağılımı grafiği
    plt.figure(figsize=(10, 6))
    experience = cv_data.get('experience', [])
    years = [int(exp.get('end_date', '2024')) - int(exp.get('start_date', '2024')) 
             for exp in experience]
    plt.hist(years, bins=10)
    plt.title("Deneyim Yılları Dağılımı")
    plt.xlabel("Yıl")
    plt.ylabel("Pozisyon Sayısı")
    plt.savefig(charts_dir / f"experience_distribution_{timestamp}.png")
    plt.close()
    
    # Eğitim dağılımı grafiği
    plt.figure(figsize=(10, 6))
    education = cv_data.get('education', [])
    degrees = [edu.get('degree', '') for edu in education]
    degree_counts = pd.Series(degrees).value_counts()
    sns.barplot(x=degree_counts.values, y=degree_counts.index)
    plt.title("Eğitim Seviyeleri Dağılımı")
    plt.savefig(charts_dir / f"education_distribution_{timestamp}.png")
    plt.close() 