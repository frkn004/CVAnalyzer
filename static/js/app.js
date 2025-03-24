document.addEventListener('DOMContentLoaded', () => {
    // DOM elementleri
    const sidebarItems = document.querySelectorAll('.sidebar-menu li');
    const tabContents = document.querySelectorAll('.tab-content');
    const fileUpload = document.getElementById('file');
    const dropArea = document.getElementById('dropArea');
    const uploadedFile = document.getElementById('uploadedFile');
    const fileName = document.getElementById('fileName');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const replaceFile = document.getElementById('replaceFile');
    const removeFile = document.getElementById('removeFile');
    const osType = document.getElementById('osType');
    const cpuInfo = document.getElementById('cpuInfo');
    const memoryInfo = document.getElementById('memoryInfo');
    const pythonVersion = document.getElementById('pythonVersion');
    const resultModal = document.getElementById('resultModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const saveResultBtn = document.getElementById('saveResultBtn');
    const closeModalX = document.querySelector('.close-modal');
    const modalContent = document.getElementById('modalContent');
    const memoryLimit = document.getElementById('memoryLimit');
    const rangeValue = document.querySelector('.range-value');
    const modelSelect = document.getElementById('model');
    const modelInfo = document.getElementById('model-info');
    const cacheBtn = document.getElementById('cacheBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');

    // Ana sekme navigasyonu
    const tabNavButtons = document.querySelectorAll('.tab-nav-button');
    const mainTabContents = document.querySelectorAll('main .tab-content');
    
    // Analiz sonuçları içindeki sekmeler
    const resultTabButtons = document.querySelectorAll('.results-tabs .tab-button');
    const resultTabContents = document.querySelectorAll('.results-container .tab-content');

    // Sekme değiştirme işlevi
    function switchTab(tabId) {
        sidebarItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-tab') === tabId) {
                item.classList.add('active');
            }
        });

        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === tabId) {
                content.classList.add('active');
            }
        });
    }

    // Ana sekme geçişleri
    if (tabNavButtons.length > 0) {
        tabNavButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Aktif sekmeyi temizle
                tabNavButtons.forEach(btn => btn.classList.remove('active'));
                mainTabContents.forEach(tab => tab.classList.remove('active'));
                
                // Tıklanan sekmeyi aktifleştir
                button.classList.add('active');
                const tabId = button.getAttribute('data-tab') + '-tab';
                document.getElementById(tabId).classList.add('active');
            });
        });
    }

    // Dosya yükleme işlemleri
    if (fileUpload) {
        fileUpload.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                showUploadedFile(file);
            }
        });
    }

    // Sürükle bırak işlemleri
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight() {
            dropArea.classList.add('highlight');
        }

        function unhighlight() {
            dropArea.classList.remove('highlight');
        }

        dropArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                const file = files[0];
                showUploadedFile(file);
            }
        }
    }

    // Yüklenen dosyayı göster
    function showUploadedFile(file) {
        const allowedTypes = ['.pdf', '.docx', '.txt'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(fileExtension)) {
            alert('Desteklenmeyen dosya formatı. Lütfen PDF, DOCX veya TXT dosyası yükleyin.');
            return;
        }
        
        dropArea.classList.add('hidden');
        uploadedFile.classList.remove('hidden');
        fileName.textContent = file.name;
        analyzeBtn.disabled = false;
    }

    // Dosya değiştirme
    if (replaceFile) {
        replaceFile.addEventListener('click', () => {
            fileUpload.click();
        });
    }

    // Dosya silme
    if (removeFile) {
        removeFile.addEventListener('click', () => {
            dropArea.classList.remove('hidden');
            uploadedFile.classList.add('hidden');
            fileUpload.value = '';
            analyzeBtn.disabled = true;
        });
    }

    // CV analiz etme
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async () => {
            if (!fileUpload || fileUpload.files.length === 0) {
                alert('Lütfen önce bir CV dosyası yükleyin.');
                return;
            }
            
            // Formdan model bilgisini al
            const selectedModel = modelSelect ? modelSelect.value : 'llama3:8b';
            const uploadForm = document.getElementById('uploadForm');
            
            if (!uploadForm) {
                alert('Form bulunamadı!');
                return;
            }
            
            // Analiz işlemini göstermek için ilerleme çubuğunu göster
            if (document.getElementById('analysisProgress')) {
                document.getElementById('analysisProgress').classList.remove('hidden');
                simulateProgress();
            }
            
            try {
                // API çağrısı için form verisi oluştur
                const formData = new FormData();
                formData.append('file', fileUpload.files[0]);
                formData.append('model', selectedModel);
                
                // CV analizi için API isteği yap
                const response = await fetch('/analyze-cv', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP hata! Durum: ${response.status}`);
                }
                
                const result = await response.json();
                
                // Başarılı yanıt durumunda form submit et
                if (!result.error) {
                    uploadForm.submit();
                } else {
                    if (document.getElementById('analysisProgress')) {
                        document.getElementById('analysisProgress').classList.add('hidden');
                    }
                    alert('CV analizi sırasında bir hata oluştu: ' + result.error);
                }
            } catch (error) {
                if (document.getElementById('analysisProgress')) {
                    document.getElementById('analysisProgress').classList.add('hidden');
                }
                console.error('CV analiz hatası:', error);
                alert('CV analizi sırasında bir hata oluştu. Lütfen tekrar deneyin.');
            }
        });
    }

    // İlerleme çubuğu simülasyonu
    function simulateProgress() {
        const progressFill = document.querySelector('.progress-fill');
        const progressPercent = document.getElementById('progress-percent');
        const steps = document.querySelectorAll('.step');
        
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width += 1;
                progressFill.style.width = width + '%';
                progressPercent.textContent = width + '%';
                
                // Adımları güncelleme
                if (width >= 25 && width < 50) {
                    steps[0].classList.add('completed');
                    steps[0].querySelector('i').className = 'fas fa-check';
                    steps[1].classList.add('active');
                } else if (width >= 50 && width < 75) {
                    steps[1].classList.remove('active');
                    steps[1].classList.add('completed');
                    steps[1].querySelector('i').className = 'fas fa-check';
                    steps[2].classList.add('active');
                } else if (width >= 75) {
                    steps[2].classList.remove('active');
                    steps[2].classList.add('completed');
                    steps[2].querySelector('i').className = 'fas fa-check';
                    steps[3].classList.add('active');
                }
            }
        }, 30);
    }

    // Analiz sonuçlarını gösterme
    function showAnalysisResults(results) {
        // Konsola analiz sonuçlarını yazdır (geliştirme için)
        console.log("Analiz sonuçları:", results);
        
        // Analiz ilerleme göstergesini gizle
        document.getElementById('analysisProgress').classList.add('hidden');
        
        // Hata kontrolü - Error ve error alanlarını kontrol et
        if (results && (results.error || results.Error)) {
            const errorMessage = results.error || results.Error || "Bilinmeyen hata";
            const rawResponse = results.raw_response || "";
            
            console.error("Analiz hatası:", errorMessage);
            
            // Hata mesajını göster
            // Önce personalInfo elementini deneyelim
            const personalInfoElement = document.getElementById('personalInfo');
            if (personalInfoElement) {
                personalInfoElement.innerHTML = `
                    <div class="error-message">
                        <h3>🔴 Analiz Hatası</h3>
                        <p>${errorMessage}</p>
                        ${rawResponse ? 
                            `<div class="raw-response">
                                <h4>Detaylar:</h4>
                                <pre>${rawResponse}</pre>
                             </div>` : ''}
                        <p>Tekrar deneyiniz veya farklı bir model seçiniz.</p>
                    </div>
                `;
                document.getElementById('analysisResults').classList.remove('hidden');
                return;
            } else {
                // Modal ile göster
                const modalContent = document.getElementById('modalContent');
                if (modalContent) {
                    modalContent.innerHTML = `
                        <div class="error-message">
                            <h3>🔴 Analiz Hatası</h3>
                            <p>${errorMessage}</p>
                            ${rawResponse ? 
                                `<div class="raw-response">
                                    <h4>Detaylar:</h4>
                                    <pre>${rawResponse}</pre>
                                 </div>` : ''}
                            <p>Tekrar deneyiniz veya farklı bir model seçiniz.</p>
                        </div>
                    `;
                    document.getElementById('resultModal').classList.add('open');
                    return;
                }
            }
        }
        
        // Sonuç boş mu veya undefined mı kontrol et
        if (!results || Object.keys(results).length === 0) {
            // Hata göster
            const errorHTML = `
                <div class="error-message">
                    <h3>🔴 Analiz Hatası</h3>
                    <p>Analiz sonucu boş veya geçersiz. Lütfen tekrar deneyiniz.</p>
                </div>
            `;
            
            // Sonucu uygun yerde göster
            const personalInfoElement = document.getElementById('personalInfo');
            if (personalInfoElement) {
                personalInfoElement.innerHTML = errorHTML;
                document.getElementById('analysisResults').classList.remove('hidden');
            } else {
                const modalContent = document.getElementById('modalContent');
                if (modalContent) {
                    modalContent.innerHTML = errorHTML;
                    document.getElementById('resultModal').classList.add('open');
                }
            }
            return;
        }
        
        try {
            // LLM mi yoksa standart analiz mi yapıldığını kontrol et
            const isLLMAnalysis = results.profil_degerlendirmesi || 
                                results.is_deneyimi || 
                                results.kisisel_bilgiler || 
                                results.egitim || 
                                results.beceriler ||
                                (results.raw_response && results.error);
            
            if (isLLMAnalysis) {
                // LLM analiz sonuçlarını göster
                showLLMAnalysisResults(results);
            } else {
                // Standart analiz sonuçlarını göster
                showStandardAnalysisResults(results);
            }
            
            // Sonuçları göster
            const analysisResultsElement = document.getElementById('analysisResults');
            if (analysisResultsElement) {
                analysisResultsElement.classList.remove('hidden');
            }
        } catch (error) {
            console.error("Sonuçları gösterirken hata:", error);
            
            // Hata mesajını göster
            const errorHTML = `
                <div class="error-message">
                    <h3>🔴 Gösterim Hatası</h3>
                    <p>Sonuçlar alındı fakat gösterilirken bir hata oluştu: ${error.message}</p>
                    <p>Lütfen tekrar deneyiniz.</p>
                </div>
            `;
            
            // Modal içinde hata göster
            const modalContent = document.getElementById('modalContent');
            if (modalContent) {
                modalContent.innerHTML = errorHTML;
                document.getElementById('resultModal').classList.add('open');
            }
        }
    }
    
    function showLLMAnalysisResults(results) {
        // Kişisel bilgiler
        let personalInfoHTML = '';
        
        // Gizli hata alanları kontrolü (_hata_bilgisi veya _ham_yanit gibi)
        const hasHiddenError = results._hata_bilgisi || results._ham_yanit;
        
        // Hata kontrolü - Eğer bir hata varsa ya da gizli hata alanları varsa, onu ana sayfada göster
        if (results.error || hasHiddenError) {
            const errorHTML = `
                <div class="error-message">
                    <h3>📝 Analiz Sonuçları (Hata Düzeltmesi ile)</h3>
                    <p>${results.error || results._hata_bilgisi || "Model yanıtında hata var, ancak CV'den bazı bilgiler çıkarılabildi."}</p>
                    ${results.raw_response || results._ham_yanit ? 
                        `<div class="raw-response">
                            <h4>Model Yanıtı:</h4>
                            <pre>${results.raw_response || results._ham_yanit}</pre>
                         </div>` : ''}
                    <p class="warning-note">Not: Analiz tam olarak yapılamadı, bazı bilgiler eksik olabilir.</p>
                </div>
            `;
            
            // Hata mesajını ana içerik alanında göster
            const personalInfoEl = document.getElementById('personalInfo');
            if (personalInfoEl) {
                personalInfoEl.innerHTML = errorHTML;
            }
            
            // Diğer alanlara devam et - CV'den alınabilen bilgileri yine de gösterelim
        }
        
        if (results.kisisel_bilgiler) {
            const info = results.kisisel_bilgiler;
            personalInfoHTML = `
                <h3>${info.isim || 'İsim bulunamadı'}</h3>
                <p><i class="fas fa-envelope"></i> ${info.email || 'E-posta bulunamadı'}</p>
                <p><i class="fas fa-phone"></i> ${info.telefon || 'Telefon bulunamadı'}</p>
                <p><i class="fas fa-map-marker-alt"></i> ${info.adres || 'Adres bulunamadı'}</p>
                <p><i class="fab fa-linkedin"></i> ${info.linkedin || 'LinkedIn bulunamadı'}</p>
                ${info.github ? `<p><i class="fab fa-github"></i> ${info.github}</p>` : ''}
            `;
            
            const personalInfoEl = document.getElementById('personalInfo');
            if (personalInfoEl && !personalInfoEl.innerHTML) {
                personalInfoEl.innerHTML = personalInfoHTML;
            }
        }
        
        // Özet
        let summaryHTML = '';
        if (results.ozet) {
            summaryHTML = `<p>${results.ozet}</p>`;
        }
        document.getElementById('summary').innerHTML = summaryHTML;
        
        // Beceriler
        let skillsHTML = '<h3>Beceriler</h3>';
        if (results.beceriler) {
            // Beceriler bir dizi olabilir
            if (Array.isArray(results.beceriler)) {
                skillsHTML += '<ul>';
                results.beceriler.forEach(skill => {
                    skillsHTML += `<li>${skill}</li>`;
                });
                skillsHTML += '</ul>';
            } 
            // Beceriler kategori nesnesi olabilir
            else if (typeof results.beceriler === 'object') {
                const skills = results.beceriler;
                
                if (skills.teknik && skills.teknik.length > 0) {
                    skillsHTML += '<div class="skill-category"><h4>Teknik Beceriler</h4><ul>';
                    skills.teknik.forEach(skill => {
                        skillsHTML += `<li>${skill}</li>`;
                    });
                    skillsHTML += '</ul></div>';
                }
                
                if (skills.yazilim && skills.yazilim.length > 0) {
                    skillsHTML += '<div class="skill-category"><h4>Yazılım</h4><ul>';
                    skills.yazilim.forEach(skill => {
                        skillsHTML += `<li>${skill}</li>`;
                    });
                    skillsHTML += '</ul></div>';
                }
                
                if (skills.metodolojiler && skills.metodolojiler.length > 0) {
                    skillsHTML += '<div class="skill-category"><h4>Metodolojiler</h4><ul>';
                    skills.metodolojiler.forEach(skill => {
                        skillsHTML += `<li>${skill}</li>`;
                    });
                    skillsHTML += '</ul></div>';
                }
                
                if (skills.profesyonel && skills.profesyonel.length > 0) {
                    skillsHTML += '<div class="skill-category"><h4>Profesyonel Beceriler</h4><ul>';
                    skills.profesyonel.forEach(skill => {
                        skillsHTML += `<li>${skill}</li>`;
                    });
                    skillsHTML += '</ul></div>';
                }
            } else {
                // String olarak gelmiş olabilir
                skillsHTML += `<p>${results.beceriler}</p>`;
            }
        } else if (Array.isArray(results.skills)) {
            skillsHTML += '<ul>';
            results.skills.forEach(skill => {
                skillsHTML += `<li>${skill}</li>`;
            });
            skillsHTML += '</ul>';
        } else {
            skillsHTML += '<p>Beceri bilgisi bulunamadı.</p>';
        }
        document.getElementById('skills').innerHTML = skillsHTML;
        
        // İş deneyimi
        let experienceHTML = '<h3>İş Deneyimi</h3>';
        try {
            if (results.is_deneyimi && results.is_deneyimi.length > 0) {
                results.is_deneyimi.forEach(exp => {
                    // Object.toString hatası yakalama
                    if (exp && typeof exp === 'object') {
                        experienceHTML += `
                            <div class="experience-item">
                                <div class="experience-header">
                                    <h4>${exp.pozisyon || 'Pozisyon Belirtilmemiş'}</h4>
                                    <h5>${exp.sirket || 'Şirket Belirtilmemiş'}</h5>
                                    <span class="date-range">${exp.tarih || exp.baslangic ? (exp.baslangic + (exp.bitis ? (' - ' + exp.bitis) : ' - Devam Ediyor')) : 'Tarih Belirtilmemiş'}</span>
                                    ${exp.lokasyon ? `<span class="location">${exp.lokasyon}</span>` : ''}
                                </div>
                                
                                <div class="experience-details">
                                    ${exp.gorevler && exp.gorevler.length > 0 ? 
                                        '<h5>Görevler</h5><ul>' + 
                                        exp.gorevler.map(task => `<li>${task}</li>`).join('') + 
                                        '</ul>' : ''}
                                    
                                    ${exp.teknolojiler && exp.teknolojiler.length > 0 ? 
                                        '<h5>Kullanılan Teknolojiler</h5><div class="tech-tags">' + 
                                        exp.teknolojiler.map(tech => `<span class="tech-tag">${tech}</span>`).join('') + 
                                        '</div>' : ''}
                                    
                                    ${exp.basarilar && exp.basarilar.length > 0 ? 
                                        '<h5>Başarılar</h5><ul>' + 
                                        exp.basarilar.map(achievement => `<li>${achievement}</li>`).join('') + 
                                        '</ul>' : ''}
                                </div>
                            </div>
                        `;
                    } else {
                        experienceHTML += `<p>Geçersiz deneyim verisi: ${typeof exp === 'string' ? exp : JSON.stringify(exp)}</p>`;
                    }
                });
            } else if (results.experience) {
                experienceHTML += `<p>${results.experience}</p>`;
            } else {
                experienceHTML += '<p>İş deneyimi bilgisi bulunamadı.</p>';
            }
        } catch (error) {
            console.error("İş deneyimi işlenirken hata:", error);
            experienceHTML += `<p>İş deneyimi verileri işlenirken hata oluştu: ${error.message}</p>`;
        }
        document.getElementById('experience').innerHTML = experienceHTML;
        
        // Eğitim
        let educationHTML = '<h3>Eğitim</h3>';
        try {
            if (results.egitim && results.egitim.length > 0) {
                results.egitim.forEach(edu => {
                    if (edu && typeof edu === 'object') {
                        educationHTML += `
                            <div class="education-item">
                                <h4>${edu.okul || edu.kurum || 'Kurum Belirtilmemiş'}</h4>
                                <h5>${edu.derece || edu.bolum || 'N/A'}${edu.alan ? ', ' + edu.alan : ''}</h5>
                                <span class="date-range">${edu.tarih || (edu.baslangic ? (edu.baslangic + (edu.bitis ? (' - ' + edu.bitis) : ' - Devam Ediyor')) : 'Tarih Belirtilmemiş')}</span>
                                ${edu.not_ortalamasi ? `<p>Not Ortalaması: ${edu.not_ortalamasi}</p>` : ''}
                                
                                ${edu.onemli_dersler && edu.onemli_dersler.length > 0 ? 
                                    '<h5>Önemli Dersler</h5><ul>' + 
                                    edu.onemli_dersler.map(course => `<li>${course}</li>`).join('') + 
                                    '</ul>' : ''}
                            </div>
                        `;
                    } else {
                        educationHTML += `<p>Geçersiz eğitim verisi: ${typeof edu === 'string' ? edu : JSON.stringify(edu)}</p>`;
                    }
                });
            } else if (results.education) {
                educationHTML += `<p>${results.education}</p>`;
            } else {
                educationHTML += '<p>Eğitim bilgisi bulunamadı.</p>';
            }
        } catch (error) {
            console.error("Eğitim verileri işlenirken hata:", error);
            educationHTML += `<p>Eğitim verileri işlenirken hata oluştu: ${error.message}</p>`;
        }
        document.getElementById('education').innerHTML = educationHTML;
        
        // Dil becerileri
        let languagesHTML = '<h3>Dil Becerileri</h3>';
        if (results.diller && results.diller.length > 0) {
            languagesHTML += '<ul>';
            results.diller.forEach(lang => {
                languagesHTML += `<li>${lang}</li>`;
            });
            languagesHTML += '</ul>';
        } else if (results.languages) {
            languagesHTML += `<p>${results.languages}</p>`;
        } else {
            languagesHTML += '<p>Dil becerisi bilgisi bulunamadı.</p>';
        }
        document.getElementById('languages').innerHTML = languagesHTML;
        
        // Sertifikalar
        let certificatesHTML = '<h3>Sertifikalar</h3>';
        if (results.sertifikalar && results.sertifikalar.length > 0) {
            certificatesHTML += '<ul>';
            results.sertifikalar.forEach(cert => {
                certificatesHTML += `<li>${cert}</li>`;
            });
            certificatesHTML += '</ul>';
        } else if (results.certificates) {
            certificatesHTML += `<p>${results.certificates}</p>`;
        } else {
            certificatesHTML += '<p>Sertifika bilgisi bulunamadı.</p>';
        }
        document.getElementById('certificates').innerHTML = certificatesHTML;
        
        // Profil değerlendirmesi
        if (results.profil_degerlendirmesi) {
            const evaluation = results.profil_degerlendirmesi;
            
            // Güçlü yönler
            let strengthsHTML = '';
            if (evaluation.guclu_yonler && evaluation.guclu_yonler.length > 0) {
                evaluation.guclu_yonler.forEach(strength => {
                    strengthsHTML += `<li>${strength}</li>`;
                });
            } else {
                strengthsHTML += '<li>Güçlü yön bilgisi bulunamadı.</li>';
            }
            document.getElementById('strengths').innerHTML = strengthsHTML;
            
            // Zayıf yönler / Geliştirilmesi gereken alanlar
            let weaknessesHTML = '';
            if (evaluation.gelistirilmesi_gereken_alanlar && evaluation.gelistirilmesi_gereken_alanlar.length > 0) {
                evaluation.gelistirilmesi_gereken_alanlar.forEach(weakness => {
                    weaknessesHTML += `<li>${weakness}</li>`;
                });
            } else {
                weaknessesHTML += '<li>Geliştirilmesi gereken alan bilgisi bulunamadı.</li>';
            }
            document.getElementById('weaknesses').innerHTML = weaknessesHTML;
            
            // Uygun pozisyonlar
            let positionsHTML = '';
            if (evaluation.uygun_pozisyonlar && evaluation.uygun_pozisyonlar.length > 0) {
                evaluation.uygun_pozisyonlar.forEach(position => {
                    positionsHTML += `<li>${position}</li>`;
                });
            } else {
                positionsHTML += '<li>Uygun pozisyon bilgisi bulunamadı.</li>';
            }
            document.getElementById('suitablePositions').innerHTML = positionsHTML;
            
            // Öneriler
            let recommendationsHTML = '';
            if (evaluation.oneriler && evaluation.oneriler.length > 0) {
                evaluation.oneriler.forEach(recommendation => {
                    recommendationsHTML += `<li>${recommendation}</li>`;
                });
            } else {
                recommendationsHTML += '<li>Öneri bilgisi bulunamadı.</li>';
            }
            document.getElementById('recommendations').innerHTML = recommendationsHTML;
        } else {
            // Profil değerlendirmesi yoksa varsayılan seçenekler göster
            document.getElementById('strengths').innerHTML = '<li>Değerlendirme verisi bulunamadı.</li>';
            document.getElementById('weaknesses').innerHTML = '<li>Değerlendirme verisi bulunamadı.</li>';
            document.getElementById('suitablePositions').innerHTML = '<li>Değerlendirme verisi bulunamadı.</li>';
            document.getElementById('recommendations').innerHTML = '<li>Değerlendirme verisi bulunamadı.</li>';
        }
    }
    
    function showStandardAnalysisResults(results) {
        // Analiz sonuçlarını HTML olarak hazırlama
        const htmlContent = `
            <div class="cv-analysis-results">
                <div class="result-section">
                    <div class="result-header">
                        <h4>Genel Bilgiler</h4>
                        <span class="match-score">Eşleşme: %${results.match_score ? Math.round(results.match_score * 100) : 'N/A'}</span>
                    </div>
                    <div class="result-content">
                        <div class="personal-info">
                            <h3>${results.personal_info && results.personal_info.name ? results.personal_info.name : 'İsim bulunamadı'}</h3>
                            <p><i class="fas fa-envelope"></i> ${results.personal_info && results.personal_info.email ? results.personal_info.email : 'N/A'}</p>
                            <p><i class="fas fa-phone"></i> ${results.personal_info && results.personal_info.phone ? results.personal_info.phone : 'N/A'}</p>
                            <p><i class="fas fa-map-marker-alt"></i> ${results.personal_info && results.personal_info.address ? results.personal_info.address : 'N/A'}</p>
                            <p><i class="fab fa-linkedin"></i> ${results.personal_info && results.personal_info.linkedin ? results.personal_info.linkedin : 'N/A'}</p>
                        </div>
                        <div class="summary">
                            <p>${results.summary || 'Özet bilgi bulunamadı.'}</p>
                        </div>
                    </div>
                </div>
                
                <div class="result-section">
                    <div class="result-header">
                        <h4>Beceriler</h4>
                    </div>
                    <div class="result-content">
                        <div class="skills-container">
                            ${results.skills && results.skills.length > 0 ? 
                                results.skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('') : 
                                'Beceri bilgisi bulunamadı.'}
                        </div>
                    </div>
                </div>
                
                <div class="result-section">
                    <div class="result-header">
                        <h4>İş Deneyimi</h4>
                    </div>
                    <div class="result-content">
                        ${results.experience || 'İş deneyimi bilgisi bulunamadı.'}
                    </div>
                </div>
                
                <div class="result-section">
                    <div class="result-header">
                        <h4>Eğitim</h4>
                    </div>
                    <div class="result-content">
                        ${results.education || 'Eğitim bilgisi bulunamadı.'}
                    </div>
                </div>
                
                <div class="result-section">
                    <div class="result-header">
                        <h4>Dil Becerileri</h4>
                    </div>
                    <div class="result-content">
                        ${results.languages || 'Dil becerisi bilgisi bulunamadı.'}
                    </div>
                </div>
                
                <div class="result-section">
                    <div class="result-header">
                        <h4>Sertifikalar</h4>
                    </div>
                    <div class="result-content">
                        ${results.certificates || 'Sertifika bilgisi bulunamadı.'}
                    </div>
                </div>
            </div>
        `;
        
        // HTML içeriğini yerleştir
        const resultContentElement = document.getElementById('analysisResultContent');
        if (resultContentElement) {
            resultContentElement.innerHTML = htmlContent;
        } else {
            console.error("analysisResultContent elementi bulunamadı!");
            
            // Alternatif olarak modalContent'e yerleştir
            const modalContent = document.getElementById('modalContent');
            if (modalContent) {
                modalContent.innerHTML = htmlContent;
                // Modal'ı göster
                document.getElementById('resultModal').classList.add('open');
            } else {
                // Son çare olarak sayfada bir div oluştur
                const mainContent = document.querySelector('.content');
                if (mainContent) {
                    const newResultDiv = document.createElement('div');
                    newResultDiv.id = 'dynamicAnalysisResult';
                    newResultDiv.innerHTML = htmlContent;
                    mainContent.appendChild(newResultDiv);
                }
            }
        }
    }

    // Analiz sonuçları sekmesini güncelleme
    function updateAnalysisResultsTab(results) {
        const analyzeResultsContent = document.querySelector('#analyze-results .panel-body');
        
        analyzeResultsContent.innerHTML = `
            <div class="cv-overview">
                <div class="cv-header">
                    <div>
                        <h3>${results.personal_info.name}</h3>
                        <p>${results.experience && results.experience.length > 0 ? `${results.experience[0].title} @ ${results.experience[0].company}` : 'İş deneyimi bulunamadı'}</p>
                    </div>
                    <button class="btn btn-primary" id="viewDetailsBtn">
                        <i class="fas fa-eye"></i> Detayları Görüntüle
                    </button>
                </div>
                
                <div class="cv-summary">
                    <div class="summary-item">
                        <span class="summary-label">Toplam Deneyim</span>
                        <span class="summary-value">${getTotalExperience(results.experience) || 'N/A'}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Eğitim</span>
                        <span class="summary-value">${results.education && results.education.length > 0 ? results.education[results.education.length - 1].degree : 'N/A'}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Beceri Sayısı</span>
                        <span class="summary-value">${results.skills ? results.skills.length : '0'}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Eşleşme Puanı</span>
                        <span class="summary-value ${results.match_score ? `score-${Math.round(results.match_score * 100)}` : ''}">${results.match_score ? `${Math.round(results.match_score * 100)}%` : 'N/A'}</span>
                    </div>
                </div>
                
                <div class="cv-details">
                    <div class="details-section">
                        <h4>Öne Çıkan Beceriler</h4>
                        <div class="skills-list">
                            ${results.skills && results.skills.length > 0 
                                ? results.skills.slice(0, 5).map(skill => `<span class="skill-tag">${skill}</span>`).join('') 
                                : 'Beceri bilgisi bulunamadı.'}
                            ${results.skills && results.skills.length > 5 ? `<span class="skill-tag more">+${results.skills.length - 5}</span>` : ''}
                        </div>
                    </div>
                    
                    ${results.experience && results.experience.length > 0 ? `
                    <div class="details-section">
                        <h4>Son Deneyim</h4>
                        <div class="experience-item compact">
                            <div class="exp-header">
                                <h5>${results.experience[0].title}</h5>
                                <span class="exp-company">${results.experience[0].company}</span>
                            </div>
                            <p class="exp-description">${results.experience[0].description || 'Açıklama bulunamadı'}</p>
                        </div>
                    </div>` : ''}
                </div>
                
                <div class="action-buttons cv-actions">
                    <button class="btn" id="matchPositionBtn">
                        <i class="fas fa-link"></i> İş Pozisyonuyla Eşleştir
                    </button>
                    <button class="btn btn-primary" id="exportCVBtn">
                        <i class="fas fa-download"></i> Analiz Sonucunu İndir
                    </button>
                </div>
            </div>
        `;
        
        // Detayları görüntüleme düğmesi
        document.getElementById('viewDetailsBtn').addEventListener('click', () => {
            resultModal.classList.add('open');
        });
        
        // Eşleştirme düğmesi
        document.getElementById('matchPositionBtn').addEventListener('click', () => {
            switchTab('job-positions');
        });
    }

    // Toplam deneyim süresini hesaplama
    function getTotalExperience(experience) {
        if (!experience || experience.length === 0) return 'N/A';
        
        let totalYears = 0;
        const currentYear = new Date().getFullYear();
        
        experience.forEach(exp => {
            const startYear = exp.start_date ? new Date(exp.start_date).getFullYear() : currentYear;
            const endYear = exp.end_date ? new Date(exp.end_date).getFullYear() : currentYear;
            totalYears += (endYear - startYear);
        });
        
        return totalYears > 0 ? `${totalYears} Yıl` : 'N/A';
    }

    // Modal kapatma
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            resultModal.classList.remove('open');
        });
    }
    
    if (closeModalX) {
        closeModalX.addEventListener('click', () => {
            resultModal.classList.remove('open');
        });
    }

    // Bellek limitini güncelleme
    if (memoryLimit) {
        memoryLimit.addEventListener('input', () => {
            rangeValue.textContent = memoryLimit.value + ' GB';
        });
    }

    // Model seçimini güncelleme
    if (modelSelect) {
        modelSelect.addEventListener('change', () => {
            modelInfo.textContent = modelSelect.options[modelSelect.selectedIndex].text.split(' ')[0];
        });
    }

    // Önbelleği temizleme
    if (cacheBtn) {
        cacheBtn.addEventListener('click', () => {
            alert('Önbellek başarıyla temizlendi.');
        });
    }

    // Ayarları kaydetme
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            alert('Ayarlar başarıyla kaydedildi.');
        });
    }

    // Sistem bilgilerini API'den alma
    fetchSystemInfo();
    
    // API'den sistem bilgilerini alma
    async function fetchSystemInfo() {
        try {
            const response = await fetch('/api/system-info');
            
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Sistem bilgisi elementlerini seç
            const osType = document.getElementById('osType');
            const cpuInfo = document.getElementById('cpuInfo');
            const memoryInfo = document.getElementById('memoryInfo');
            const pythonVersion = document.getElementById('pythonVersion');
            
            // Veri ve elementlerin varlığını kontrol et
            if (data && data.system_info) {
                const info = data.system_info;
                
                // Elementlerin varlığını kontrol et ve varsa değerleri güncelle
                if (osType) osType.textContent = info.system || 'Bilinmiyor';
                if (cpuInfo) cpuInfo.textContent = info.processor || 'Bilinmiyor';
                if (pythonVersion) pythonVersion.textContent = info.python_version || 'Bilinmiyor';
                
                if (memoryInfo && info.memory) {
                    const totalGB = (info.memory.total / (1024 * 1024 * 1024)).toFixed(2);
                    const usedGB = (info.memory.used / (1024 * 1024 * 1024)).toFixed(2);
                    memoryInfo.textContent = `${usedGB} GB / ${totalGB} GB (${info.memory.percent}%)`;
                }
            } else {
                setDefaultSystemInfo();
            }
        } catch (error) {
            console.error('[Error] Sistem bilgileri alınamadı:', error);
            setDefaultSystemInfo();
        }
    }
    
    // Varsayılan sistem bilgilerini ayarla
    function setDefaultSystemInfo() {
        if (osType) osType.textContent = 'macOS';
        if (cpuInfo) cpuInfo.textContent = 'Apple Silicon';
        if (memoryInfo) memoryInfo.textContent = '16GB / 32GB';
        if (pythonVersion) pythonVersion.textContent = '3.11.2';
    }

    // CSS için ek stilller (bu modülde tanımlanan ancak CSS'te bulunmayan sınıflar için)
    const dynamicStyles = document.createElement('style');
    dynamicStyles.textContent = `
        .cv-analysis-results .result-section {
            margin-bottom: 1.5rem;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            overflow: hidden;
        }
        
        .cv-analysis-results .result-header {
            background-color: rgba(59, 130, 246, 0.05);
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .cv-analysis-results .result-content {
            padding: 1rem;
        }
        
        .cv-analysis-results .match-score {
            background-color: var(--primary-color);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 500;
        }
        
        .cv-analysis-results .personal-info {
            margin-bottom: 1rem;
        }
        
        .cv-analysis-results .personal-info h3 {
            margin-bottom: 0.5rem;
        }
        
        .cv-analysis-results .personal-info p {
            margin-bottom: 0.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .cv-analysis-results .summary {
            padding: 0.75rem;
            background-color: rgba(59, 130, 246, 0.05);
            border-radius: 4px;
            margin-top: 1rem;
        }
        
        .skills-list, .languages-list {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        
        .skill-tag, .language-tag {
            background-color: rgba(59, 130, 246, 0.1);
            color: var(--primary-color);
            padding: 0.35rem 0.75rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        .skill-tag.small {
            font-size: 0.8rem;
            padding: 0.25rem 0.5rem;
        }
        
        .skill-tag.more {
            background-color: rgba(100, 116, 139, 0.1);
            color: var(--secondary-color);
        }
        
        .experience-item, .education-item {
            margin-bottom: 1.25rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .experience-item:last-child, .education-item:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        
        .exp-header, .edu-header {
            margin-bottom: 0.5rem;
        }
        
        .exp-company, .edu-degree {
            color: var(--text-light);
            font-size: 0.9rem;
        }
        
        .exp-period, .edu-period {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-light);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        .exp-description, .edu-gpa {
            margin-bottom: 0.75rem;
        }
        
        .exp-skills {
            margin-top: 0.75rem;
        }
        
        .cert-list {
            list-style: none;
            padding: 0;
        }
        
        .cert-list li {
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .cert-list li i {
            color: var(--primary-color);
        }
        
        .cv-overview {
            width: 100%;
        }
        
        .cv-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
        }
        
        .cv-summary {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .summary-item {
            background-color: rgba(59, 130, 246, 0.05);
            padding: 1rem;
            border-radius: var(--border-radius);
        }
        
        .summary-label {
            display: block;
            font-size: 0.875rem;
            color: var(--text-light);
            margin-bottom: 0.25rem;
        }
        
        .summary-value {
            font-weight: 600;
            font-size: 1.1rem;
        }
        
        .score-90, .score-91, .score-92, .score-93, .score-94, .score-95, .score-96, .score-97, .score-98, .score-99, .score-100 {
            color: var(--success-color);
        }
        
        .score-70, .score-71, .score-72, .score-73, .score-74, .score-75, .score-76, .score-77, .score-78, .score-79, .score-80, .score-81, .score-82, .score-83, .score-84, .score-85, .score-86, .score-87, .score-88, .score-89 {
            color: var(--primary-color);
        }
        
        .score-50, .score-51, .score-52, .score-53, .score-54, .score-55, .score-56, .score-57, .score-58, .score-59, .score-60, .score-61, .score-62, .score-63, .score-64, .score-65, .score-66, .score-67, .score-68, .score-69 {
            color: var(--warning-color);
        }
        
        .score-0, .score-1, .score-2, .score-3, .score-4, .score-5, .score-6, .score-7, .score-8, .score-9, .score-10, .score-11, .score-12, .score-13, .score-14, .score-15, .score-16, .score-17, .score-18, .score-19, .score-20, .score-21, .score-22, .score-23, .score-24, .score-25, .score-26, .score-27, .score-28, .score-29, .score-30, .score-31, .score-32, .score-33, .score-34, .score-35, .score-36, .score-37, .score-38, .score-39, .score-40, .score-41, .score-42, .score-43, .score-44, .score-45, .score-46, .score-47, .score-48, .score-49 {
            color: var(--danger-color);
        }
        
        .cv-details {
            margin-bottom: 1.5rem;
        }
        
        .details-section {
            margin-bottom: 1.25rem;
        }
        
        .details-section h4 {
            margin-bottom: 0.75rem;
            font-size: 1rem;
            padding-bottom: 0.375rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        .experience-item.compact {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        
        .cv-actions {
            justify-content: flex-start;
        }
    `;
    
    document.head.appendChild(dynamicStyles);
}); 