import pytest
from src.utils.platform_config import PlatformConfig
from pathlib import Path

@pytest.fixture
def config():
    """Platform yapılandırma fixture'ı"""
    return PlatformConfig()

def test_get_system_info(config):
    """Sistem bilgisi testi"""
    info = config.get_system_info()
    assert isinstance(info, dict)
    assert "system" in info
    assert "machine" in info
    assert "processor" in info
    assert "memory_total" in info
    assert "memory_available" in info
    assert "cpu_count" in info

def test_validate_requirements(config):
    """Gereksinim kontrolü testi"""
    is_valid, message = config.validate_requirements()
    assert isinstance(is_valid, bool)
    assert isinstance(message, str)

def test_get_model_path(config):
    """Model yolu testi"""
    path = config.get_model_path()
    assert isinstance(path, Path)
    assert path.name == "models"

def test_str_representation(config):
    """String temsili testi"""
    string_repr = str(config)
    assert isinstance(string_repr, str)
    assert "Sistem:" in string_repr
    assert "Mimari:" in string_repr
    assert "İşlemci:" in string_repr
    assert "Bellek:" in string_repr
    assert "CPU Çekirdek:" in string_repr 