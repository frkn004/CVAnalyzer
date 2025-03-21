import platform
import psutil
from typing import Tuple, Dict, Any
from pathlib import Path

class PlatformConfig:
    def __init__(self):
        """Platform yapılandırma sınıfı"""
        self.system = platform.system()
        self.machine = platform.machine()
        self.processor = platform.processor()
        self.memory = psutil.virtual_memory()
        self.cpu_count = psutil.cpu_count()
        
    def get_system_info(self) -> Dict[str, Any]:
        """
        Sistem bilgilerini döndürür
        
        Returns:
            Dict[str, Any]: Sistem bilgileri
        """
        return {
            "system": self.system,
            "machine": self.machine,
            "processor": self.processor,
            "memory_total": self.memory.total,
            "memory_available": self.memory.available,
            "cpu_count": self.cpu_count
        }
        
    def validate_requirements(self) -> Tuple[bool, str]:
        """
        Sistem gereksinimlerini kontrol eder
        
        Returns:
            Tuple[bool, str]: (Gereksinimler karşılanıyor mu?, Hata mesajı)
        """
        # Minimum bellek gereksinimi (4GB)
        min_memory = 4 * 1024 * 1024 * 1024  # 4GB in bytes
        if self.memory.total < min_memory:
            return False, f"Yetersiz bellek: {self.memory.total / (1024**3):.1f}GB (minimum 4GB gerekli)"
            
        # Minimum CPU çekirdek sayısı
        min_cpu = 2
        if self.cpu_count < min_cpu:
            return False, f"Yetersiz CPU çekirdek sayısı: {self.cpu_count} (minimum {min_cpu} gerekli)"
            
        return True, "Tüm gereksinimler karşılanıyor"
        
    def get_model_path(self) -> Path:
        """
        Model dosyasının yolunu döndürür
        
        Returns:
            Path: Model dosyası yolu
        """
        return Path("models")
        
    def __str__(self) -> str:
        """Platform bilgilerini string olarak döndürür"""
        info = self.get_system_info()
        return (
            f"Sistem: {info['system']}\n"
            f"Mimari: {info['machine']}\n"
            f"İşlemci: {info['processor']}\n"
            f"Bellek: {info['memory_total'] / (1024**3):.1f}GB\n"
            f"CPU Çekirdek: {info['cpu_count']}"
        ) 