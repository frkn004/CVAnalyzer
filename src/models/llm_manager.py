from typing import Dict, Optional, List
import os
from llama_cpp import Llama
from ..utils.platform_utils import PlatformConfig

class LLMManager:
    def __init__(self):
        self.platform_config = PlatformConfig()
        self.model_config = self.platform_config.get_recommended_model_config()
        self.model: Optional[Llama] = None
        
    def initialize_model(self) -> bool:
        """Model'i yükler ve başlatır"""
        if not os.path.exists(self.model_config["model_path"]):
            raise FileNotFoundError(
                f"Model dosyası bulunamadı: {self.model_config['model_path']}\n"
                "Lütfen model dosyasını indirip models/ dizinine yerleştirin."
            )
        
        try:
            self.model = Llama(
                model_path=self.model_config["model_path"],
                n_ctx=self.model_config["n_ctx"],
                n_batch=self.model_config["n_batch"],
                n_threads=self.model_config["n_threads"],
                n_gpu_layers=self.model_config["n_gpu_layers"],
                use_mmap=self.model_config["use_mmap"],
                use_mlock=self.model_config["use_mlock"]
            )
            return True
        except Exception as e:
            print(f"Model yüklenirken hata oluştu: {str(e)}")
            return False
    
    def analyze_cv(self, cv_text: str) -> Dict:
        """CV metnini analiz eder ve yapılandırılmış veri döndürür"""
        if not self.model:
            raise RuntimeError("Model henüz yüklenmedi. Önce initialize_model() çağrılmalı.")
        
        prompt = self._create_cv_analysis_prompt(cv_text)
        response = self.model.create_completion(
            prompt,
            max_tokens=2048,
            temperature=0.1,
            top_p=0.95,
            stop=["</CV_ANALYSIS>"],
            echo=False
        )
        
        return self._parse_cv_analysis_response(response.choices[0].text)
    
    def match_cv_with_position(self, cv_data: Dict, position_data: Dict) -> Dict:
        """CV ve pozisyon verilerini karşılaştırır ve eşleşme skoru döndürür"""
        if not self.model:
            raise RuntimeError("Model henüz yüklenmedi. Önce initialize_model() çağrılmalı.")
        
        prompt = self._create_matching_prompt(cv_data, position_data)
        response = self.model.create_completion(
            prompt,
            max_tokens=1024,
            temperature=0.1,
            top_p=0.95,
            stop=["</MATCH_ANALYSIS>"],
            echo=False
        )
        
        return self._parse_matching_response(response.choices[0].text)
    
    def _create_cv_analysis_prompt(self, cv_text: str) -> str:
        """CV analizi için prompt oluşturur"""
        return f"""<CV_ANALYSIS>
Lütfen aşağıdaki CV'yi analiz ederek yapılandırılmış formatta bilgileri çıkar:

{cv_text}

Lütfen aşağıdaki formatta yanıt ver:
{{
    "kisisel_bilgiler": {{
        "ad_soyad": "",
        "email": "",
        "telefon": "",
        "lokasyon": ""
    }},
    "egitim": [
        {{
            "okul": "",
            "bolum": "",
            "derece": "",
            "baslangic": "",
            "bitis": ""
        }}
    ],
    "deneyimler": [
        {{
            "sirket": "",
            "pozisyon": "",
            "baslangic": "",
            "bitis": "",
            "sorumluluklar": []
        }}
    ],
    "beceriler": {{
        "teknik": [],
        "diller": [],
        "soft_skills": []
    }}
}}
</CV_ANALYSIS>"""

    def _create_matching_prompt(self, cv_data: Dict, position_data: Dict) -> str:
        """Eşleştirme analizi için prompt oluşturur"""
        return f"""<MATCH_ANALYSIS>
Lütfen aşağıdaki CV ve pozisyon verilerini karşılaştırarak eşleşme analizi yap:

CV Verileri:
{cv_data}

Pozisyon Gereksinimleri:
{position_data}

Lütfen aşağıdaki formatta yanıt ver:
{{
    "genel_skor": 0-100,
    "kategori_skorlari": {{
        "teknik_beceriler": 0-100,
        "deneyim": 0-100,
        "egitim": 0-100
    }},
    "guclu_yonler": [],
    "eksik_yonler": [],
    "tavsiyeler": []
}}
</MATCH_ANALYSIS>"""

    def _parse_cv_analysis_response(self, response: str) -> Dict:
        """Model yanıtını işler ve yapılandırılmış veri döndürür"""
        # TODO: Yanıt parsing işlemi geliştirilecek
        return eval(response.strip())
    
    def _parse_matching_response(self, response: str) -> Dict:
        """Eşleştirme yanıtını işler ve yapılandırılmış veri döndürür"""
        # TODO: Yanıt parsing işlemi geliştirilecek
        return eval(response.strip()) 