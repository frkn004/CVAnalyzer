from typing import Optional, Dict, Any, List
from ctransformers import AutoModelForCausalLM
import os
from pathlib import Path
import json
from tqdm import tqdm

class LLMManager:
    def __init__(self, model_path: str, model_type: str = "llama"):
        """
        LLM yönetici sınıfı
        
        Args:
            model_path (str): Model dosyasının yolu
            model_type (str): Model tipi (varsayılan: "llama")
        """
        self.model_path = Path(model_path)
        self.model_type = model_type
        self.model: Optional[AutoModelForCausalLM] = None
        self._ensure_model_directory()
        
    def _ensure_model_directory(self):
        """Model dizininin varlığını kontrol eder ve yoksa oluşturur."""
        model_dir = os.path.dirname(self.model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
    def load_model(self, context_length: int = 2048, max_new_tokens: int = 512) -> None:
        """Modeli yükler veya indirir."""
        if not os.path.exists(self.model_path):
            print(f"Model dosyası bulunamadı: {self.model_path}")
            print("Model indiriliyor...")
            # Model indirme URL'si
            model_url = "https://huggingface.co/TheBloke/DeepSeek-LLM-67B-GGUF/resolve/main/deepseek-llm-67b.Q4_K_M.gguf"
            
            # İndirme işlemi
            import requests
            response = requests.get(model_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(self.model_path, 'wb') as f, tqdm(
                desc="Model indiriliyor",
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = f.write(data)
                    pbar.update(size)
            
            print("Model indirme tamamlandı!")
        
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                model_type=self.model_type,
                context_length=context_length,
                max_new_tokens=max_new_tokens
            )
            print("Model başarıyla yüklendi!")
        except Exception as e:
            raise RuntimeError(f"Model yüklenirken hata oluştu: {str(e)}")
        
    def generate(self, prompt: str, **kwargs: Dict[str, Any]) -> str:
        """
        Verilen prompt için metin üretir
        
        Args:
            prompt (str): Giriş metni
            **kwargs: Ek parametreler
            
        Returns:
            str: Üretilen metin
        """
        if self.model is None:
            raise RuntimeError("Model yüklenmemiş. Önce load_model() çağrılmalı.")
            
        response = self.model(prompt, **kwargs)
        return response
        
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
        response = self.generate(prompt)
        
        # Yanıtı işle
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # JSON ayrıştırma hatası durumunda varsayılan sonuç
            result = {
                "match_score": 0.5,
                "category_scores": {
                    "skills": 0.5,
                    "experience": 0.5,
                    "education": 0.5
                },
                "strengths": ["Model yanıtı ayrıştırılamadı"],
                "weaknesses": ["Model yanıtı ayrıştırılamadı"],
                "recommendations": ["Model yanıtı ayrıştırılamadı"]
            }
            
        return result
        
    def _create_matching_prompt(self, cv_data: Dict[str, Any], position_data: Dict[str, Any]) -> str:
        """Eşleştirme için prompt oluşturur"""
        prompt = f"""Aşağıdaki CV'yi iş pozisyonuyla eşleştir ve sonuçları JSON formatında döndür:

CV:
{json.dumps(cv_data, indent=2, ensure_ascii=False)}

İş Pozisyonu:
{json.dumps(position_data, indent=2, ensure_ascii=False)}

Lütfen aşağıdaki formatta bir JSON yanıtı döndür:
{{
    "match_score": 0.0-1.0 arası bir sayı,
    "category_scores": {{
        "skills": 0.0-1.0 arası bir sayı,
        "experience": 0.0-1.0 arası bir sayı,
        "education": 0.0-1.0 arası bir sayı
    }},
    "strengths": ["güçlü yönler listesi"],
    "weaknesses": ["zayıf yönler listesi"],
    "recommendations": ["öneriler listesi"]
}}"""
        return prompt
        
    def __del__(self):
        """Kaynakları temizler"""
        if self.model is not None:
            del self.model 