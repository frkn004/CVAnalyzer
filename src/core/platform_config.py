import platform
import psutil
import os
from typing import Dict, Any

class PlatformConfig:
    def __init__(self):
        """Platform yapılandırma sınıfı"""
        self.system = platform.system()
        self.machine = platform.machine()
        self.processor = platform.processor()
        self.python_version = platform.python_version()
        
    def get_system_info(self) -> Dict[str, Any]:
        """Sistem bilgilerini döndürür"""
        return {
            "system": self.system,
            "machine": self.machine,
            "processor": self.processor,
            "python_version": self.python_version,
            "memory": self._get_memory_info(),
            "cpu": self._get_cpu_info()
        }
        
    def _get_memory_info(self) -> Dict[str, Any]:
        """Bellek bilgilerini döndürür"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free
        }
        
    def _get_cpu_info(self) -> Dict[str, Any]:
        """CPU bilgilerini döndürür"""
        return {
            "physical_cores": psutil.cpu_count(logical=False),
            "total_cores": psutil.cpu_count(logical=True),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "cpu_percent": psutil.cpu_percent(interval=1)
        }
        
    def validate_requirements(self) -> bool:
        """Sistem gereksinimlerini kontrol eder"""
        # Minimum bellek gereksinimi (4GB)
        min_memory = 4 * 1024 * 1024 * 1024  # 4GB in bytes
        memory = psutil.virtual_memory()
        
        # Minimum CPU çekirdek sayısı (2)
        min_cores = 2
        cores = psutil.cpu_count(logical=False)
        
        return memory.total >= min_memory and cores >= min_cores
        
    def get_model_path(self) -> str:
        """Model dosyasının yolunu döndürür"""
        # Model dosyası yolu
        model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
        os.makedirs(model_dir, exist_ok=True)
        return os.path.join(model_dir, "model.gguf")
        
    def __str__(self) -> str:
        """String gösterimi"""
        return f"PlatformConfig(system={self.system}, machine={self.machine}, processor={self.processor})" 