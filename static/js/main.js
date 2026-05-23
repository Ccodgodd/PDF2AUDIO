// Frontend Application Logic for VoicePDF

document.addEventListener('DOMContentLoaded', () => {
    // --- State Variables ---
    let selectedFile = null;
    let uploadedFilename = null;
    let languagesConfig = {};
    let isPlaying = false;
    let isMuted = false;
    let preMuteVolume = 0.8;

    // --- DOM Elements ---
    // Navigation / General
    const themeToggleBtn = document.getElementById('theme-toggle');
    const toastContainer = document.getElementById('toast-container');
    const mouseGlow = document.getElementById('mouse-glow');

    // Step 1: Upload & Config
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('pdf-file-input');
    const fileDetails = document.getElementById('file-details');
    const fileNameDisplay = document.getElementById('file-name');
    const fileSizeDisplay = document.getElementById('file-size');
    const removeFileBtn = document.getElementById('remove-file-btn');
    const statPages = document.getElementById('stat-pages');
    const statChars = document.getElementById('stat-chars');
    const languageSelect = document.getElementById('language-select');
    const accentSelect = document.getElementById('accent-select');
    const speedSlowCheckbox = document.getElementById('speed-slow-checkbox');
    const generateBtn = document.getElementById('generate-btn');

    // Step 2: Display States
    const outputIdle = document.getElementById('output-idle');
    const outputConverting = document.getElementById('output-converting');
    const convertingStatusText = document.getElementById('converting-status');
    const conversionProgressBar = document.getElementById('conversion-progress');
    const outputSuccess = document.getElementById('output-success');
    const pdfPreviewBox = document.getElementById('pdf-preview-box');
    const extractedTextPreview = document.getElementById('extracted-text-preview');

    // Step 2: Custom Audio Player
    const mainAudio = document.getElementById('main-audio');
    const waveBars = document.getElementById('wave-bars');
    const audioTitle = document.getElementById('audio-title');
    const audioSubtitle = document.getElementById('audio-subtitle');
    const playPauseBtn = document.getElementById('play-pause-btn');
    const playIcon = playPauseBtn.querySelector('.icon-play');
    const pauseIcon = playPauseBtn.querySelector('.icon-pause');
    const skipBackBtn = document.getElementById('skip-back-btn');
    const skipForwardBtn = document.getElementById('skip-forward-btn');
    const timelineSlider = document.getElementById('timeline-slider');
    const timeCurrent = document.getElementById('time-current');
    const timeTotal = document.getElementById('time-total');
    const muteBtn = document.getElementById('mute-btn');
    const volumeSlider = document.getElementById('volume-slider');
    const playbackSpeedSelect = document.getElementById('playback-speed');
    const downloadAudioBtn = document.getElementById('download-audio-btn');

    // --- Init App ---
    initTheme();
    fetchLanguages();
    
    // Set initial volumes & slider fills
    volumeSlider.value = 80;
    updateSliderBackground(volumeSlider);
    updateSliderBackground(timelineSlider);

    // --- Mouse Glow Tracker (Spotify Inspired Spring Motion) ---
    let targetX = window.innerWidth / 2;
    let targetY = window.innerHeight / 2;
    let currentX = targetX;
    let currentY = targetY;

    window.addEventListener('mousemove', (e) => {
        targetX = e.clientX;
        targetY = e.clientY;
    });

    function animateMouseGlow() {
        // 0.08 interpolation coefficient simulates a smooth spring drag/lag
        currentX += (targetX - currentX) * 0.08;
        currentY += (targetY - currentY) * 0.08;
        
        if (mouseGlow) {
            mouseGlow.style.left = `${currentX}px`;
            mouseGlow.style.top = `${currentY}px`;
        }
        requestAnimationFrame(animateMouseGlow);
    }
    animateMouseGlow();

    // Resize window adjusts safety margins
    window.addEventListener('resize', () => {
        targetX = Math.min(targetX, window.innerWidth);
        targetY = Math.min(targetY, window.innerHeight);
    });

    // --- Event Listeners ---

    // Theme Toggle
    themeToggleBtn.addEventListener('click', toggleTheme);

    // Dropzone Events
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    dropzone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });

    // Remove File
    removeFileBtn.addEventListener('click', resetUploadState);

    // Config Option Handlers
    languageSelect.addEventListener('change', () => {
        populateAccents(languageSelect.value);
    });

    // Conversion Trigger
    generateBtn.addEventListener('click', convertPdfToSpeech);

    // Audio Playback Elements
    playPauseBtn.addEventListener('click', togglePlayPause);
    skipBackBtn.addEventListener('click', () => skipAudio(-10));
    skipForwardBtn.addEventListener('click', () => skipAudio(10));
    
    // Sliders
    timelineSlider.addEventListener('input', (e) => {
        seekAudio(e);
        updateSliderBackground(timelineSlider);
    });
    
    muteBtn.addEventListener('click', toggleMute);
    
    volumeSlider.addEventListener('input', (e) => {
        changeVolume(e);
        updateSliderBackground(volumeSlider);
    });
    
    playbackSpeedSelect.addEventListener('change', changePlaybackRate);

    // Audio HTML5 Events
    mainAudio.addEventListener('timeupdate', () => {
        updateTimeline();
        updateSliderBackground(timelineSlider);
    });
    
    mainAudio.addEventListener('loadedmetadata', () => {
        timeTotal.textContent = formatTime(mainAudio.duration);
        updateSliderBackground(timelineSlider);
    });
    
    mainAudio.addEventListener('ended', () => {
        setPlaybackState(false);
        timelineSlider.value = 0;
        timeCurrent.textContent = "0:00";
        updateSliderBackground(timelineSlider);
    });

    // --- Core Functions ---

    // Spotify range input fill painter
    function updateSliderBackground(slider) {
        const min = parseFloat(slider.min) || 0;
        const max = parseFloat(slider.max) || 100;
        const val = parseFloat(slider.value) || 0;
        const pct = ((val - min) / (max - min)) * 100;
        
        const colorFilled = 'var(--primary)';
        const colorTrack = 'rgba(255, 255, 255, 0.08)';
        slider.style.background = `linear-gradient(to right, ${colorFilled} 0%, ${colorFilled} ${pct}%, ${colorTrack} ${pct}%, ${colorTrack} 100%)`;
    }

    // 1. Toast Notification System
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let iconName = 'info';
        if (type === 'success') iconName = 'check-circle';
        if (type === 'error') iconName = 'alert-triangle';
        
        toast.innerHTML = `
            <div class="toast-icon"><i data-lucide="${iconName}"></i></div>
            <div class="toast-message">${message}</div>
        `;
        
        toastContainer.appendChild(toast);
        lucide.createIcons();

        // Animate Out & Remove
        setTimeout(() => {
            toast.style.animation = 'toastSlideOut 0.3s ease forwards';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }

    // 2. Theme Controller
    function initTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Refresh slider visual colors to match active theme rules
        updateSliderBackground(volumeSlider);
        updateSliderBackground(timelineSlider);
    }

    // 3. Languages Setup
    async function fetchLanguages() {
        try {
            const response = await fetch('/api/languages');
            if (!response.ok) throw new Error('Failed to fetch languages configuration');
            
            languagesConfig = await response.json();
            
            // Populate language select dropdown
            languageSelect.innerHTML = '';
            for (const langCode in languagesConfig) {
                const opt = document.createElement('option');
                opt.value = langCode;
                opt.textContent = languagesConfig[langCode].name;
                // English as default
                if (langCode === 'en') opt.selected = true;
                languageSelect.appendChild(opt);
            }
            
            // Populate accents initially for default English
            populateAccents('en');
        } catch (err) {
            console.error(err);
            showToast('Could not load voices. Using English defaults.', 'error');
        }
    }

    function populateAccents(langCode) {
        if (!languagesConfig[langCode]) return;
        
        accentSelect.innerHTML = '';
        const accents = languagesConfig[langCode].accents;
        for (const accentCode in accents) {
            const opt = document.createElement('option');
            opt.value = accentCode;
            opt.textContent = accents[accentCode];
            accentSelect.appendChild(opt);
        }
    }

    // 4. File Handler (Upload)
    function handleFileSelection(file) {
        if (!file) return;

        // Validation
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== 'pdf') {
            showToast('Invalid file format. Please upload a PDF.', 'error');
            return;
        }

        const sizeMB = file.size / (1024 * 1024);
        if (sizeMB > 15) {
            showToast('File is too large. Max size allowed is 15MB.', 'error');
            return;
        }

        selectedFile = file;
        
        // Show File Info in UI
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = `${sizeMB.toFixed(2)} MB`;
        
        dropzone.classList.add('hidden');
        fileDetails.classList.remove('hidden');

        // Immediately upload file to Backend API
        uploadFile(file);
    }

    async function uploadFile(file) {
        showConvertingState('Uploading and extracting PDF text...');
        
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            // Successfully Uploaded & Parsed
            uploadedFilename = data.filename;
            statPages.textContent = data.pages_count;
            statChars.textContent = data.characters_count.toLocaleString();
            
            // Populate Preview Box
            extractedTextPreview.textContent = data.preview;
            pdfPreviewBox.classList.remove('hidden');
            
            generateBtn.disabled = false;
            showIdleState();
            showToast('PDF uploaded and text parsed successfully!', 'success');
        } catch (err) {
            showToast(err.message || 'File upload failed', 'error');
            resetUploadState();
        }
    }

    function resetUploadState() {
        selectedFile = null;
        uploadedFilename = null;
        fileInput.value = '';
        
        // Disable convert action
        generateBtn.disabled = true;
        
        // Hide stats & preview
        fileDetails.classList.add('hidden');
        dropzone.classList.remove('hidden');
        pdfPreviewBox.classList.add('hidden');
        extractedTextPreview.textContent = '';
        
        // Set state back to idle
        showIdleState();
    }

    // 5. Conversion Handler
    async function convertPdfToSpeech() {
        if (!uploadedFilename) return;

        showConvertingState('Synthesizing speech. Generating audio file...');
        
        const requestData = {
            filename: uploadedFilename,
            lang: languageSelect.value,
            tld: accentSelect.value,
            slow: speedSlowCheckbox.checked
        };

        try {
            // Fake progression meter on UI
            let progress = 10;
            const progressInterval = setInterval(() => {
                if (progress < 90) {
                    progress += Math.floor(Math.random() * 8) + 1;
                    conversionProgressBar.style.width = `${progress}%`;
                }
            }, 600);

            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            clearInterval(progressInterval);
            conversionProgressBar.style.width = '100%';

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Conversion failed');
            }

            // Success conversion
            showToast('Audio generated successfully!', 'success');
            
            setTimeout(() => {
                showSuccessState(data.audio_url, data.download_url, data.filename);
            }, 400);

        } catch (err) {
            showToast(err.message || 'Failed to convert document', 'error');
            showIdleState();
        }
    }

    // UI state switchers
    function showIdleState() {
        outputIdle.classList.remove('hidden');
        outputConverting.classList.add('hidden');
        outputSuccess.classList.add('hidden');
        conversionProgressBar.style.width = '0%';
    }

    function showConvertingState(statusText) {
        convertingStatusText.textContent = statusText;
        outputIdle.classList.add('hidden');
        outputConverting.classList.remove('hidden');
        outputSuccess.classList.add('hidden');
    }

    function showSuccessState(audioUrl, downloadUrl, audioFilename) {
        outputIdle.classList.add('hidden');
        outputConverting.classList.add('hidden');
        outputSuccess.classList.remove('hidden');

        // Set Audio source
        mainAudio.src = audioUrl;
        mainAudio.load();

        // Update player labels
        audioTitle.textContent = selectedFile ? selectedFile.name.replace('.pdf', '') : 'Document Audio';
        const langName = languageSelect.options[languageSelect.selectedIndex].text;
        const accentName = accentSelect.options[accentSelect.selectedIndex].text;
        audioSubtitle.textContent = `${langName} (${accentName})`;

        // Configure Download Button
        downloadAudioBtn.href = downloadUrl;

        // Reset player timeline
        timelineSlider.value = 0;
        timeCurrent.textContent = "0:00";
        setPlaybackState(false);
        updateSliderBackground(timelineSlider);
    }

    // 6. Custom Audio Player Controls
    function togglePlayPause() {
        if (!mainAudio.src) return;

        if (isPlaying) {
            mainAudio.pause();
            setPlaybackState(false);
        } else {
            mainAudio.play();
            setPlaybackState(true);
        }
    }

    function setPlaybackState(play) {
        isPlaying = play;
        if (isPlaying) {
            playIcon.classList.add('hidden');
            pauseIcon.classList.remove('hidden');
            waveBars.classList.add('playing');
        } else {
            playIcon.classList.remove('hidden');
            pauseIcon.classList.add('hidden');
            waveBars.classList.remove('playing');
        }
    }

    function updateTimeline() {
        if (!mainAudio.duration) return;
        
        const pct = (mainAudio.currentTime / mainAudio.duration) * 100;
        timelineSlider.value = pct;
        timeCurrent.textContent = formatTime(mainAudio.currentTime);
    }

    function seekAudio(e) {
        if (!mainAudio.duration) return;
        
        const pct = e.target.value;
        const targetTime = (pct / 100) * mainAudio.duration;
        mainAudio.currentTime = targetTime;
    }

    function skipAudio(seconds) {
        if (!mainAudio.src) return;
        mainAudio.currentTime = Math.max(0, Math.min(mainAudio.duration || 0, mainAudio.currentTime + seconds));
        updateSliderBackground(timelineSlider);
    }

    function toggleMute() {
        isMuted = !isMuted;
        mainAudio.muted = isMuted;
        
        const muteIcon = muteBtn.querySelector('i');
        
        if (isMuted) {
            muteIcon.setAttribute('data-lucide', 'volume-x');
            volumeSlider.value = 0;
        } else {
            muteIcon.setAttribute('data-lucide', 'volume-2');
            volumeSlider.value = preMuteVolume * 100;
        }
        updateSliderBackground(volumeSlider);
        lucide.createIcons();
    }

    function changeVolume(e) {
        const val = e.target.value / 100;
        mainAudio.volume = val;
        
        const muteIcon = muteBtn.querySelector('i');
        
        if (val === 0) {
            isMuted = true;
            mainAudio.muted = true;
            muteIcon.setAttribute('data-lucide', 'volume-x');
        } else {
            isMuted = false;
            mainAudio.muted = false;
            preMuteVolume = val;
            
            if (val < 0.4) {
                muteIcon.setAttribute('data-lucide', 'volume-1');
            } else {
                muteIcon.setAttribute('data-lucide', 'volume-2');
            }
        }
        lucide.createIcons();
    }

    function changePlaybackRate() {
        const rate = parseFloat(playbackSpeedSelect.value);
        mainAudio.playbackRate = rate;
    }

    // Helper Time Formatter (mm:ss)
    function formatTime(secs) {
        if (isNaN(secs)) return "0:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    }
});
