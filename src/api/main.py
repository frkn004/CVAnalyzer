from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import os

from ..models.llm_manager import LLMManager
from ..processors.document_processor import DocumentProcessor
from ..utils.platform_utils import PlatformConfig

app = FastAPI(
    title="CV Analiz API",
    description="Yerel LLM tabanlı CV analiz ve eşleştirme sistemi",
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

# Global nesneler
llm_manager = LLMManager()
doc_processor = DocumentProcessor()
platform_config = PlatformConfig()

class Position(BaseModel):
    title: str
    description: str
    requirements: List[str]
    preferred_skills: Optional[List[str]] = None

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında çalışacak kod"""
    # Sistem gereksinimlerini kontrol et
    is_valid, message = platform_config.validate_requirements()
    if not is_valid:
        raise RuntimeError(f"Sistem gereksinimleri karşılanmıyor: {message}")
    
    # Model dizinini oluştur
    os.makedirs("models", exist_ok=True)
    
    # Modeli yükle
    if not llm_manager.initialize_model():
        raise RuntimeError("Model yüklenemedi!")

@app.get("/")
async def root():
    """API kök endpoint"""
    return {
        "status": "active",
        "system_info": str(platform_config)
    }

@app.post("/analyze-cv")
async def analyze_cv(file: UploadFile = File(...)):
    """CV dosyasını analiz et"""
    # Dosya uzantısını kontrol et
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in doc_processor.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dosya formatı: {file_ext}"
        )
    
    # Geçici dosya oluştur
    temp_path = f"temp_{file.filename}"
    try:
        # Dosyayı kaydet
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Metni çıkar
        cv_text = doc_processor.extract_text(temp_path)
        if not cv_text:
            raise HTTPException(
                status_code=400,
                detail="CV metnini çıkarma başarısız"
            )
        
        # CV'yi analiz et
        analysis = llm_manager.analyze_cv(cv_text)
        return analysis
        
    finally:
        # Geçici dosyayı temizle
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/match-cv")
async def match_cv(
    file: UploadFile = File(...),
    position: Position
):
    """CV'yi pozisyon ile eşleştir"""
    # Dosyayı analiz et
    cv_analysis = await analyze_cv(file)
    
    # Pozisyon verilerini hazırla
    position_data = {
        "title": position.title,
        "description": position.description,
        "requirements": position.requirements,
        "preferred_skills": position.preferred_skills or []
    }
    
    # Eşleştirme yap
    match_result = llm_manager.match_cv_with_position(cv_analysis, position_data)
    return match_result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 