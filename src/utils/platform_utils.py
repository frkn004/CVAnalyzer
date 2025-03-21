import platform
import psutil
import torch
import os
from typing import Dict, Tuple

class PlatformConfig:
    def __init__(self):
        self.system_info = self._get_system_info()
        self.gpu_info = self._get_gpu_info()
        self.memory_info = self._get_memory_info()
        
    def _get_system_info(self) -> Dict[str, str]:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    
    def _get_gpu_info(self) -> Dict[str, bool]:
        has_cuda = torch.cuda.is_available()
        has_mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
        
        return {
            "cuda_available": has_cuda,
            "mps_available": has_mps,
            "gpu_count": torch.cuda.device_count() if has_cuda else 0,
            "gpu_name": torch.cuda.get_device_name(0) if has_cuda else None
        }
    
    def _get_memory_info(self) -> Dict[str, float]:
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024 ** 3),
            "available_gb": memory.available / (1024 ** 3),
            "percent_used": memory.percent
        }
    
    def get_recommended_model_config(self) -> Dict[str, any]:
        """Model yapılandırmasını platform özelliklerine göre belirler"""
        is_mac = self.system_info["os"].lower() == "darwin"
        is_windows = self.system_info["os"].lower() == "windows"
        has_cuda = self.gpu_info["cuda_available"]
        has_mps = self.gpu_info["mps_available"]
        
        config = {
            "model_path": None,
            "n_ctx": 8192,
            "n_batch": 512,
            "n_threads": psutil.cpu_count(logical=False),
            "n_gpu_layers": 0
        }
        
        if is_mac and has_mps:
            config.update({
                "model_name": "deepseek-coder-7b-q4_0",
                "n_gpu_layers": -1,  # Tüm katmanları GPU'ya yükle
                "use_mmap": True,
                "use_mlock": False
            })
        elif is_windows and has_cuda:
            config.update({
                "model_name": "deepseek-llm-67b-q5_k_m",
                "n_gpu_layers": -1,
                "use_mmap": True,
                "use_mlock": False
            })
        else:
            config.update({
                "model_name": "deepseek-coder-7b-q4_0",
                "n_gpu_layers": 0,  # CPU-only mode
                "use_mmap": True,
                "use_mlock": False
            })
            
        # Model dosya yolunu ayarla
        models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        config["model_path"] = os.path.join(models_dir, f"{config['model_name']}.gguf")
        
        return config
    
    def validate_requirements(self) -> Tuple[bool, str]:
        """Sistem gereksinimlerini kontrol eder"""
        min_memory_gb = 16
        recommended_memory_gb = 32
        
        if self.memory_info["total_gb"] < min_memory_gb:
            return False, f"Yetersiz RAM: {self.memory_info['total_gb']:.1f}GB. Minimum {min_memory_gb}GB gerekli."
        
        if not (self.gpu_info["cuda_available"] or self.gpu_info["mps_available"]):
            if self.memory_info["total_gb"] < recommended_memory_gb:
                return False, f"GPU bulunamadı ve RAM yetersiz ({self.memory_info['total_gb']:.1f}GB). En az {recommended_memory_gb}GB önerilir."
        
        return True, "Sistem gereksinimleri karşılanıyor."

    def __str__(self) -> str:
        """Platform bilgilerini okunabilir formatta döndürür"""
        return f"""
Sistem Bilgileri:
----------------
İşletim Sistemi: {self.system_info['os']} {self.system_info['os_version']}
İşlemci: {self.system_info['processor']}
Mimari: {self.system_info['machine']}

GPU Bilgileri:
-------------
CUDA Kullanılabilir: {self.gpu_info['cuda_available']}
MPS Kullanılabilir: {self.gpu_info['mps_available']}
GPU Sayısı: {self.gpu_info['gpu_count']}
GPU Adı: {self.gpu_info['gpu_name'] if self.gpu_info['gpu_name'] else 'N/A'}

Bellek Bilgileri:
----------------
Toplam RAM: {self.memory_info['total_gb']:.1f}GB
Kullanılabilir RAM: {self.memory_info['available_gb']:.1f}GB
Kullanım Yüzdesi: {self.memory_info['percent']}%
""" 