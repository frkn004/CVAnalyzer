import pytest
from src.models.llm_manager import LLMManager
import os
from unittest.mock import Mock, patch

@pytest.fixture
def llm_manager():
    return LLMManager()

@pytest.fixture
def sample_cv_text():
    return """John Doe
john.doe@email.com
+90 555 123 4567

EĞİTİM
XYZ Üniversitesi, Bilgisayar Mühendisliği (2015-2019)

DENEYİM
ABC Teknoloji - Senior Developer (2019-2023)
- Python ve FastAPI ile backend geliştirme
- Docker ve Kubernetes ile deployment
- AWS servisleri yönetimi

BECERİLER
Python, FastAPI, Docker, Kubernetes, AWS, PostgreSQL"""

@pytest.fixture
def sample_position():
    return {
        "title": "Senior Python Developer",
        "description": "Backend geliştirme pozisyonu",
        "requirements": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AWS"]
    }

def test_model_initialization_without_model_file(llm_manager):
    """Model dosyası olmadan başlatma denemesi"""
    with pytest.raises(FileNotFoundError):
        llm_manager.initialize_model()

@patch('os.path.exists')
def test_model_initialization_with_mock_file(mock_exists, llm_manager):
    """Mock model dosyası ile başlatma denemesi"""
    mock_exists.return_value = True
    
    with patch('llama_cpp.Llama') as mock_llama:
        mock_llama.return_value = Mock()
        assert llm_manager.initialize_model() is True
        
        # Model yapılandırma parametrelerini kontrol et
        mock_llama.assert_called_once()
        args = mock_llama.call_args[1]
        assert "model_path" in args
        assert "n_ctx" in args
        assert "n_batch" in args
        assert "n_threads" in args
        assert "n_gpu_layers" in args

def test_analyze_cv_without_initialization(llm_manager, sample_cv_text):
    """Model yüklenmeden CV analizi denemesi"""
    with pytest.raises(RuntimeError):
        llm_manager.analyze_cv(sample_cv_text)

@patch('os.path.exists')
def test_analyze_cv_with_mock_model(mock_exists, llm_manager, sample_cv_text):
    """Mock model ile CV analizi"""
    mock_exists.return_value = True
    
    with patch('llama_cpp.Llama') as mock_llama:
        # Mock model yanıtı
        mock_response = Mock()
        mock_response.choices = [Mock(text="""
{
    "kisisel_bilgiler": {
        "ad_soyad": "John Doe",
        "email": "john.doe@email.com",
        "telefon": "+90 555 123 4567",
        "lokasyon": ""
    },
    "egitim": [
        {
            "okul": "XYZ Üniversitesi",
            "bolum": "Bilgisayar Mühendisliği",
            "derece": "Lisans",
            "baslangic": "2015",
            "bitis": "2019"
        }
    ],
    "deneyimler": [
        {
            "sirket": "ABC Teknoloji",
            "pozisyon": "Senior Developer",
            "baslangic": "2019",
            "bitis": "2023",
            "sorumluluklar": [
                "Python ve FastAPI ile backend geliştirme",
                "Docker ve Kubernetes ile deployment",
                "AWS servisleri yönetimi"
            ]
        }
    ],
    "beceriler": {
        "teknik": ["Python", "FastAPI", "Docker", "Kubernetes", "AWS", "PostgreSQL"],
        "diller": [],
        "soft_skills": []
    }
}
        """)]
        
        mock_llama.return_value = Mock(create_completion=Mock(return_value=mock_response))
        
        # Model'i başlat
        llm_manager.initialize_model()
        
        # CV analizi yap
        result = llm_manager.analyze_cv(sample_cv_text)
        
        # Sonuçları kontrol et
        assert isinstance(result, dict)
        assert "kisisel_bilgiler" in result
        assert "egitim" in result
        assert "deneyimler" in result
        assert "beceriler" in result
        
        assert result["kisisel_bilgiler"]["ad_soyad"] == "John Doe"
        assert len(result["egitim"]) == 1
        assert len(result["deneyimler"]) == 1
        assert len(result["beceriler"]["teknik"]) == 6

@patch('os.path.exists')
def test_match_cv_with_position(mock_exists, llm_manager, sample_cv_text, sample_position):
    """CV-pozisyon eşleştirme testi"""
    mock_exists.return_value = True
    
    with patch('llama_cpp.Llama') as mock_llama:
        # Mock model yanıtı
        mock_response = Mock()
        mock_response.choices = [Mock(text="""
{
    "genel_skor": 85,
    "kategori_skorlari": {
        "teknik_beceriler": 90,
        "deneyim": 85,
        "egitim": 80
    },
    "guclu_yonler": [
        "Python ve FastAPI deneyimi",
        "AWS ve Docker bilgisi"
    ],
    "eksik_yonler": [],
    "tavsiyeler": []
}
        """)]
        
        mock_llama.return_value = Mock(create_completion=Mock(return_value=mock_response))
        
        # Model'i başlat
        llm_manager.initialize_model()
        
        # Eşleştirme yap
        result = llm_manager.match_cv_with_position(
            llm_manager.analyze_cv(sample_cv_text),
            sample_position
        )
        
        # Sonuçları kontrol et
        assert isinstance(result, dict)
        assert "genel_skor" in result
        assert "kategori_skorlari" in result
        assert "guclu_yonler" in result
        assert "eksik_yonler" in result
        assert "tavsiyeler" in result
        
        assert isinstance(result["genel_skor"], int)
        assert 0 <= result["genel_skor"] <= 100
        assert len(result["guclu_yonler"]) > 0 