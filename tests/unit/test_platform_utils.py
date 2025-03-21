import pytest
from src.utils.platform_utils import PlatformConfig
import platform
import psutil
import torch

@pytest.fixture
def platform_config():
    return PlatformConfig()

def test_system_info(platform_config):
    """Sistem bilgilerinin doğru alındığını test eder"""
    system_info = platform_config.system_info
    
    assert isinstance(system_info, dict)
    assert "os" in system_info
    assert system_info["os"] == platform.system()
    assert "os_version" in system_info
    assert "machine" in system_info
    assert "processor" in system_info

def test_gpu_info(platform_config):
    """GPU bilgilerinin doğru alındığını test eder"""
    gpu_info = platform_config.gpu_info
    
    assert isinstance(gpu_info, dict)
    assert "cuda_available" in gpu_info
    assert isinstance(gpu_info["cuda_available"], bool)
    assert "mps_available" in gpu_info
    assert isinstance(gpu_info["mps_available"], bool)
    assert "gpu_count" in gpu_info
    assert isinstance(gpu_info["gpu_count"], int)
    
    if gpu_info["cuda_available"]:
        assert gpu_info["gpu_count"] > 0
        assert gpu_info["gpu_name"] is not None
    else:
        assert gpu_info["gpu_count"] == 0

def test_memory_info(platform_config):
    """Bellek bilgilerinin doğru alındığını test eder"""
    memory_info = platform_config.memory_info
    
    assert isinstance(memory_info, dict)
    assert "total_gb" in memory_info
    assert "available_gb" in memory_info
    assert "percent_used" in memory_info
    
    assert memory_info["total_gb"] > 0
    assert memory_info["available_gb"] > 0
    assert 0 <= memory_info["percent_used"] <= 100

def test_model_config(platform_config):
    """Model yapılandırmasının doğru oluşturulduğunu test eder"""
    config = platform_config.get_recommended_model_config()
    
    assert isinstance(config, dict)
    assert "model_path" in config
    assert "n_ctx" in config
    assert "n_batch" in config
    assert "n_threads" in config
    assert "n_gpu_layers" in config
    assert "model_name" in config
    
    # Platform'a göre doğru model seçildiğini kontrol et
    is_mac = platform.system().lower() == "darwin"
    is_windows = platform.system().lower() == "windows"
    has_cuda = torch.cuda.is_available()
    has_mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()
    
    if is_mac and has_mps:
        assert config["model_name"] == "deepseek-coder-7b-q4_0"
        assert config["n_gpu_layers"] == -1
    elif is_windows and has_cuda:
        assert config["model_name"] == "deepseek-llm-67b-q5_k_m"
        assert config["n_gpu_layers"] == -1

def test_validate_requirements(platform_config):
    """Sistem gereksinimleri kontrolünün doğru çalıştığını test eder"""
    is_valid, message = platform_config.validate_requirements()
    
    assert isinstance(is_valid, bool)
    assert isinstance(message, str)
    
    # Minimum bellek gereksinimini kontrol et
    if platform_config.memory_info["total_gb"] < 16:
        assert not is_valid
        assert "Yetersiz RAM" in message
    elif not (platform_config.gpu_info["cuda_available"] or platform_config.gpu_info["mps_available"]):
        if platform_config.memory_info["total_gb"] < 32:
            assert not is_valid
            assert "GPU bulunamadı" in message 