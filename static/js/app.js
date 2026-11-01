/**
 * OpusCut AI - Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    sourceType: 'youtube', // 'youtube' | 'upload' | 'sample'
    currentMeta: null,
    clipCount: 10,
    jobId: null,
    pollTimer: null,
    clips: [],
    activeFilter: 'all',
    activeTrimClip: null,
    rulesImages: []
  };

  // DOM Elements
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const youtubeInput = document.getElementById('youtube-url-input');
  const btnFetchYt = document.getElementById('btn-fetch-yt');
  const dropzone = document.getElementById('file-dropzone');
  const fileInput = document.getElementById('video-file-input');
  const samplesContainer = document.getElementById('samples-container');
  const previewBanner = document.getElementById('video-preview-banner');
  const previewThumb = document.getElementById('preview-thumbnail');
  const previewTitle = document.getElementById('preview-title');
  const previewUploader = document.getElementById('preview-uploader');
  const previewDuration = document.getElementById('preview-duration');
  const previewBadge = document.getElementById('preview-source-badge');
  
  // Campaign Rules Elements
  const toggleCampaignRules = document.getElementById('toggle-campaign-rules');
  const campaignRulesBody = document.getElementById('campaign-rules-body');
  const btnToggleRulesUi = document.getElementById('btn-toggle-rules-ui');
  const rulesToggleText = document.getElementById('rules-toggle-text');
  const rulesToggleArrow = document.getElementById('rules-toggle-arrow');
  const rulesStatusBadge = document.getElementById('rules-status-badge');
  const rulesDropzone = document.getElementById('rules-dropzone');
  const rulesFileInput = document.getElementById('rules-file-input');
  const rulesImagesList = document.getElementById('rules-images-list');
  const presetChips = document.querySelectorAll('.preset-chip[data-preset]');
  const btnClearRules = document.getElementById('btn-clear-rules');
  const campaignRulesText = document.getElementById('campaign-rules-text');
  const ocrStatusTag = document.getElementById('ocr-status-tag');
  const rulesKeywordsInput = document.getElementById('rules-keywords-input');
  const rulesBannedInput = document.getElementById('rules-banned-input');
  const rulesHookSelect = document.getElementById('rules-hook-select');
  const rulesStrictnessSelect = document.getElementById('rules-strictness-select');

  // Clip count selector elements
  const countChips = document.querySelectorAll('.count-chip');
  const customCountInput = document.getElementById('custom-clip-count');
  
  // Settings
  const durationSelect = document.getElementById('target-duration-select');
  const aspectSelect = document.getElementById('aspect-ratio-select');
  const cropSelect = document.getElementById('crop-style-select');
  const btnStartProcess = document.getElementById('btn-start-process');
  
  // Pipeline & Results
  const pipelineSection = document.getElementById('pipeline-section');
  const pipelinePct = document.getElementById('pipeline-percent');
  const progressFill = document.getElementById('progress-fill');
  const pipelineStatusMsg = document.getElementById('pipeline-status-msg');
  
  const resultsSection = document.getElementById('results-section');
  const resultsMeta = document.getElementById('results-count-meta');
  const clipsGrid = document.getElementById('clips-grid');
  const btnZipDownload = document.getElementById('btn-download-all-zip');
  const filterChips = document.querySelectorAll('.filter-chip');
  const countAll = document.getElementById('count-all');
  const countRules = document.getElementById('count-rules');
  
  // Trim Modal Elements
  const trimModal = document.getElementById('trim-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const trimStartSlider = document.getElementById('trim-start-slider');
  const trimEndSlider = document.getElementById('trim-end-slider');
  const trimStartDisplay = document.getElementById('trim-start-display');
  const trimEndDisplay = document.getElementById('trim-end-display');
  const btnSaveTrim = document.getElementById('btn-save-trim');
  
  const toastContainer = document.getElementById('toast-container');

  // Helper: Format seconds to MM:SS
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  }

  // Helper: Show Toast Notification
  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    const icon = type === 'error' ? '❌' : (type === 'success' ? '✅' : '⚡');
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ==========================================
  // Campaign Rules & OCR Logic
  // ==========================================
  let rulesExpanded = true;
  function toggleRulesUI() {
    rulesExpanded = !rulesExpanded;
    campaignRulesBody.style.display = rulesExpanded ? 'flex' : 'none';
    rulesToggleText.textContent = rulesExpanded ? 'Collapse Rules' : 'Configure Rules';
    rulesToggleArrow.textContent = rulesExpanded ? '▴' : '▾';
  }

  toggleCampaignRules.addEventListener('click', (e) => {
    // Only toggle if not clicking directly on an input or button inside
    if (!e.target.closest('button') || e.target.closest('#btn-toggle-rules-ui')) {
      toggleRulesUI();
    }
  });

  // Rule Images Dropzone
  rulesDropzone.addEventListener('click', () => rulesFileInput.click());

  rulesDropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    rulesDropzone.classList.add('dragover');
  });

  rulesDropzone.addEventListener('dragleave', () => rulesDropzone.classList.remove('dragover'));

  rulesDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    rulesDropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleRuleImagesUpload(Array.from(e.dataTransfer.files));
    }
  });

  rulesFileInput.addEventListener('change', () => {
    if (rulesFileInput.files && rulesFileInput.files.length > 0) {
      handleRuleImagesUpload(Array.from(rulesFileInput.files));
    }
  });

  async function handleRuleImagesUpload(files) {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));

    ocrStatusTag.textContent = 'Analyzing image rules via OCR...';
    showToast(`Analyzing ${files.length} rule image(s)...`, 'info');

    try {
      const res = await fetch('/api/rules/upload-images', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) throw new Error('Rule image OCR processing failed');
      const data = await res.json();

      // Store in state
      data.images.forEach(img => {
        state.rulesImages.push(img);
      });

      renderRuleImages();

      // Append or set extracted OCR text
      if (data.extracted_text) {
        const existing = campaignRulesText.value.trim();
        campaignRulesText.value = existing ? `${existing}\n\n[OCR Rules]:\n${data.extracted_text}` : data.extracted_text;
      }

      // Populate keywords and banned words if found
      if (data.rules) {
        if (data.rules.keywords && data.rules.keywords.length > 0) {
          const currentKw = rulesKeywordsInput.value.split(',').map(s => s.trim()).filter(Boolean);
          const mergedKw = Array.from(new Set([...currentKw, ...data.rules.keywords]));
          rulesKeywordsInput.value = mergedKw.join(', ');
        }
        if (data.rules.banned_keywords && data.rules.banned_keywords.length > 0) {
          const currentBanned = rulesBannedInput.value.split(',').map(s => s.trim()).filter(Boolean);
          const mergedBanned = Array.from(new Set([...currentBanned, ...data.rules.banned_keywords]));
          rulesBannedInput.value = mergedBanned.join(', ');
        }
        if (data.rules.hook_preference && data.rules.hook_preference !== 'any') {
          rulesHookSelect.value = data.rules.hook_preference;
        }
        if (data.rules.preferred_duration && data.rules.preferred_duration !== 'auto') {
          durationSelect.value = data.rules.preferred_duration;
        }
      }

      ocrStatusTag.textContent = `✓ ${state.rulesImages.length} Image(s) Parsed`;
      rulesStatusBadge.textContent = 'Active Rules Applied';
      rulesStatusBadge.style.background = 'rgba(0, 223, 216, 0.2)';
      rulesStatusBadge.style.color = 'var(--accent-cyan)';
      showToast(`Extracted campaign rules from ${files.length} screenshot(s)!`, 'success');
    } catch (err) {
      ocrStatusTag.textContent = 'OCR Error';
      showToast(err.message, 'error');
    }
  }

  function renderRuleImages() {
    rulesImagesList.innerHTML = '';
    state.rulesImages.forEach((img, idx) => {
      const chip = document.createElement('div');
      chip.className = 'rule-image-chip';
      chip.innerHTML = `
        <img src="${img.url}" class="rule-image-thumb" alt="${img.filename}">
        <span>${img.filename.slice(0, 16)}...</span>
        <button type="button" class="rule-image-remove" data-idx="${idx}">&times;</button>
      `;
      chip.querySelector('.rule-image-remove').addEventListener('click', () => {
        state.rulesImages.splice(idx, 1);
        renderRuleImages();
        ocrStatusTag.textContent = state.rulesImages.length ? `${state.rulesImages.length} Image(s) active` : 'Ready';
      });
      rulesImagesList.appendChild(chip);
    });
  }

  // Preset Handlers
  const PRESET_DATA = {
    tiktok: {
      text: "Target punchy 15-30s high-energy clips. Must start with a bold statement or rhetorical question. Focus on viral hooks, hacks, and surprising insights. Avoid slow intros and filler.",
      keywords: "secret, mistake, hack, truth, 10x, insane, crazy",
      banned: "boring, slow, intro, hello",
      hook: "question_hook",
      duration: "short"
    },
    saas: {
      text: "Focus on AI agents, automation, enterprise revenue scaling, and engineering leverage. Disallow chatbot wrappers and generic fluff. Target high-authority founder advice.",
      keywords: "ai, scaling, revenue, automation, leverage, workflow, enterprise",
      banned: "wrapper, chatbots, generic, fluff",
      hook: "bold_statement",
      duration: "medium"
    },
    mindset: {
      text: "Emphasize discipline, daily micro-wins, execution over motivation, and mental toughness. Must inspire immediate action and resilience.",
      keywords: "discipline, motivation, execution, consistency, habits, action",
      banned: "lazy, excuse, surrender",
      hook: "bold_statement",
      duration: "auto"
    },
    wealth: {
      text: "Highlight money-making frameworks, asymmetrical risk, compounding assets, and capital leverage. Strictly avoid get-rich-quick claims.",
      keywords: "investing, leverage, wealth, assets, capital, revenue, money",
      banned: "scam, guarantee, casino",
      hook: "curiosity_gap",
      duration: "medium"
    },
    education: {
      text: "Deliver clear, step-by-step actionable tutorials and frameworks. Focus on 'How to' explanations and tactical implementation.",
      keywords: "how to, step one, framework, system, tutorial, formula",
      banned: "theory, philosophical, speculation",
      hook: "question_hook",
      duration: "medium"
    }
  };

  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      presetChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const presetKey = chip.dataset.preset;
      const data = PRESET_DATA[presetKey];
      if (data) {
        campaignRulesText.value = data.text;
        rulesKeywordsInput.value = data.keywords;
        rulesBannedInput.value = data.banned;
        rulesHookSelect.value = data.hook;
        durationSelect.value = data.duration;
        rulesStatusBadge.textContent = 'Preset Active';
        showToast(`Applied "${chip.textContent}" campaign preset!`, 'success');
      }
    });
  });

  btnClearRules.addEventListener('click', () => {
    campaignRulesText.value = '';
    rulesKeywordsInput.value = '';
    rulesBannedInput.value = '';
    rulesHookSelect.value = 'any';
    state.rulesImages = [];
    renderRuleImages();
    presetChips.forEach(c => c.classList.remove('active'));
    ocrStatusTag.textContent = 'Ready';
    rulesStatusBadge.textContent = 'Standard Clipping';
    rulesStatusBadge.style.background = 'rgba(255, 255, 255, 0.08)';
    rulesStatusBadge.style.color = 'var(--text-secondary)';
    showToast('Campaign rules cleared', 'info');
  });

  // Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      
      btn.classList.add('active');
      document.getElementById(`tab-content-${target}`).classList.add('active');
      state.sourceType = target;
      
      // If switching to sample and none active, pick first
      if (target === 'samples' && !state.currentMeta?.sample_id) {
        const firstCard = samplesContainer.querySelector('.sample-card');
        if (firstCard) firstCard.click();
      }
    });
  });

  // Load Samples
  async function loadSamples() {
    try {
      const res = await fetch('/api/samples');
      const samples = await res.json();
      samplesContainer.innerHTML = '';
      
      samples.forEach((sample, idx) => {
        const card = document.createElement('div');
        card.className = `sample-card ${idx === 0 ? 'active' : ''}`;
        card.dataset.sampleId = sample.id;
        card.innerHTML = `
          <img src="${sample.thumbnail}" class="sample-thumb" alt="${sample.title}" onerror="this.src='/static/css/default_thumb.jpg'">
          <div class="sample-info">
            <div class="sample-title">${sample.title}</div>
            <div class="sample-meta">${sample.uploader} • ${formatTime(sample.duration)}</div>
          </div>
        `;
        
        card.addEventListener('click', () => {
          document.querySelectorAll('.sample-card').forEach(c => c.classList.remove('active'));
          card.classList.add('active');
          selectVideoMeta({
            ...sample,
            sample_id: sample.id,
            source_type: 'sample'
          });
        });
        
        samplesContainer.appendChild(card);
      });
      
      // Default to sample 1 if youtube input is empty
      if (!youtubeInput.value.trim() && samples.length > 0) {
        selectVideoMeta({
          ...samples[0],
          sample_id: samples[0].id,
          source_type: 'sample'
        });
      }
    } catch (err) {
      console.error('Error loading samples:', err);
    }
  }

  // Update Preview Banner UI
  function selectVideoMeta(meta) {
    state.currentMeta = meta;
    previewThumb.src = meta.thumbnail || '';
    previewTitle.textContent = meta.title || 'Untitled Video';
    previewUploader.textContent = meta.uploader || 'Creator';
    previewDuration.textContent = formatTime(meta.duration || 0);
    previewBadge.textContent = meta.source_type === 'youtube' ? 'YouTube Stream' : 
                               (meta.source_type === 'upload' ? 'Uploaded Video' : 'Masterclass Demo');
    previewBanner.style.display = 'flex';
  }

  // Fetch YouTube Info
  async function fetchYouTubeInfo() {
    const url = youtubeInput.value.trim();
    if (!url) {
      showToast('Please enter a YouTube link first', 'error');
      return;
    }

    btnFetchYt.disabled = true;
    btnFetchYt.innerHTML = '<span>Inspecting...</span>';

    try {
      const res = await fetch('/api/video-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to fetch YouTube video');
      }

      const meta = await res.json();
      meta.source_type = 'youtube';
      meta.url = url;
      selectVideoMeta(meta);
      showToast(`Found: ${meta.title.slice(0, 40)}...`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btnFetchYt.disabled = false;
      btnFetchYt.innerHTML = '<span>Inspect Video</span><span>→</span>';
    }
  }

  btnFetchYt.addEventListener('click', fetchYouTubeInfo);
  youtubeInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') fetchYouTubeInfo();
  });

  // Dropzone File Upload
  dropzone.addEventListener('click', () => fileInput.click());
  
  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFileUpload(fileInput.files[0]);
    }
  });

  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    showToast(`Uploading ${file.name}...`, 'info');
    dropzone.innerHTML = `<div class="dropzone-icon">⏳</div><div class="dropzone-title">Uploading & analyzing ${file.name}...</div>`;

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) throw new Error('Upload failed');

      const meta = await res.json();
      meta.source_type = 'upload';
      meta.upload_id = meta.id;
      selectVideoMeta(meta);
      
      dropzone.innerHTML = `
        <div class="dropzone-icon" style="color: var(--accent-green);">✓</div>
        <div class="dropzone-title">${file.name} ready!</div>
        <div class="dropzone-sub">Click to select a different video</div>
      `;
      showToast('Video uploaded and inspected successfully!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
      dropzone.innerHTML = `
        <div class="dropzone-icon">📁</div>
        <div class="dropzone-title">Drag & drop your long video here, or browse</div>
        <div class="dropzone-sub">Supports MP4, MOV, WebM, MKV</div>
      `;
    }
  }

  // Clip Count Selector Logic (Supports 3, 5, 10, 20, 30, 50, 100, custom)
  countChips.forEach(chip => {
    chip.addEventListener('click', () => {
      countChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const count = parseInt(chip.dataset.count, 10);
      state.clipCount = count;
      customCountInput.value = count;
    });
  });

  customCountInput.addEventListener('input', () => {
    const val = parseInt(customCountInput.value, 10);
    if (!isNaN(val) && val >= 1 && val <= 150) {
      state.clipCount = val;
      // Check if matches an existing chip
      let matched = false;
      countChips.forEach(chip => {
        if (parseInt(chip.dataset.count, 10) === val) {
          chip.classList.add('active');
          matched = true;
        } else {
          chip.classList.remove('active');
        }
      });
      if (!matched) {
        countChips.forEach(chip => chip.classList.remove('active'));
      }
    }
  });

  // START CLIPPING PIPELINE
  btnStartProcess.addEventListener('click', async () => {
    if (state.sourceType === 'youtube') {
      const url = (youtubeInput.value.trim()) || (state.currentMeta && state.currentMeta.url);
      if (!url) {
        showToast('Please enter a YouTube link or switch to Demo Samples', 'error');
        youtubeInput.focus();
        return;
      }
      if (!state.currentMeta || state.currentMeta.source_type !== 'youtube') {
        state.currentMeta = { url: url, title: 'YouTube Video', source_type: 'youtube' };
      }
    } else if (state.sourceType === 'upload') {
      if (!state.currentMeta || !state.currentMeta.upload_id) {
        showToast('Please upload a video file first', 'error');
        return;
      }
    } else if (state.sourceType === 'sample') {
      if (!state.currentMeta || !state.currentMeta.sample_id) {
        const firstCard = samplesContainer.querySelector('.sample-card');
        if (firstCard) firstCard.click();
        if (!state.currentMeta || !state.currentMeta.sample_id) {
          showToast('Please select a sample video', 'error');
          return;
        }
      }
    } else if (!state.currentMeta) {
      showToast('Please select or upload a video first', 'error');
      return;
    }

    const rulesText = campaignRulesText.value.trim();
    const keywords = rulesKeywordsInput.value.split(',').map(s => s.trim()).filter(Boolean);
    const banned = rulesBannedInput.value.split(',').map(s => s.trim()).filter(Boolean);
    const hookStyle = rulesHookSelect.value;
    const strictness = parseFloat(rulesStrictnessSelect.value) || 75;

    const campaignRules = {
      has_rules: Boolean(rulesText || keywords.length > 0 || banned.length > 0 || hookStyle !== 'any' || state.rulesImages.length > 0),
      raw_text: rulesText,
      keywords: keywords,
      banned_keywords: banned,
      hook_preference: hookStyle,
      min_compliance: strictness,
      image_urls: state.rulesImages.map(img => img.url)
    };

    const payload = {
      source_type: state.sourceType,
      url: state.sourceType === 'youtube' ? (state.currentMeta.url || youtubeInput.value.trim()) : null,
      sample_id: state.sourceType === 'sample' ? state.currentMeta.sample_id : null,
      upload_id: state.sourceType === 'upload' ? state.currentMeta.upload_id : null,
      clip_count: state.clipCount,
      target_duration: durationSelect.value,
      aspect_ratio: aspectSelect.value,
      crop_style: cropSelect.value,
      campaign_rules: campaignRules
    };

    btnStartProcess.disabled = true;
    pipelineSection.style.display = 'block';
    resultsSection.style.display = 'none';
    progressFill.style.width = '5%';
    pipelinePct.textContent = '5%';
    pipelineStatusMsg.textContent = 'Submitting video to OpusCut AutoClipper engine...';

    // Smooth scroll down to pipeline
    pipelineSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
      const res = await fetch('/api/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to start clipping');
      }

      const data = await res.json();
      state.jobId = data.job_id;
      startPollingProgress(data.job_id);
    } catch (err) {
      btnStartProcess.disabled = false;
      pipelineStatusMsg.textContent = `Error: ${err.message}`;
      showToast(err.message, 'error');
    }
  });

  // Polling Job Status
  function startPollingProgress(jobId) {
    if (state.pollTimer) clearInterval(state.pollTimer);

    state.pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/job/${jobId}`);
        if (!res.ok) throw new Error('Failed to query job status');

        const job = await res.json();
        const progress = Math.min(100, Math.max(5, job.progress || 5));
        
        progressFill.style.width = `${progress}%`;
        pipelinePct.textContent = `${progress}%`;
        pipelineStatusMsg.textContent = job.stage || 'Analyzing video...';

        if (job.status === 'completed') {
          clearInterval(state.pollTimer);
          btnStartProcess.disabled = false;
          pipelineSection.style.display = 'none';
          state.clips = job.clips || [];
          btnZipDownload.href = job.zip_url || '#';
          renderClips(state.clips);
          resultsSection.style.display = 'block';
          resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          showToast(`Successfully generated ${job.clips.length} viral clips!`, 'success');
        } else if (job.status === 'error') {
          clearInterval(state.pollTimer);
          btnStartProcess.disabled = false;
          pipelineStatusMsg.textContent = `Pipeline Error: ${job.error}`;
          showToast(`Processing error: ${job.error}`, 'error');
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 900);
  }

  // Render Clips to Grid
  function renderClips(clips) {
    countAll.textContent = clips.length;
    const ruleMatchCount = clips.filter(c => (c.rule_score || 0) >= 70).length;
    if (countRules) countRules.textContent = ruleMatchCount;

    resultsMeta.textContent = `Showing ${clips.length} viral clips ranked by campaign rules & virality score`;
    clipsGrid.innerHTML = '';

    if (clips.length === 0) {
      clipsGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No clips generated.</div>';
      return;
    }

    clips.forEach(clip => {
      const card = document.createElement('div');
      card.className = 'clip-card';
      card.dataset.clipId = clip.id;
      card.dataset.score = clip.virality_score;
      card.dataset.ruleScore = clip.rule_score || 100;

      card.innerHTML = `
        <div class="clip-video-box">
          <div class="virality-badge-overlay ${clip.badge_class}">
            ${clip.badge}
          </div>
          <div class="score-circle-overlay">
            <span class="score-num">${clip.virality_score}</span>
            <span class="score-label">Score</span>
          </div>
          <video 
            class="clip-video" 
            src="${clip.video_url}" 
            poster="${clip.thumbnail_url}" 
            controls 
            preload="metadata"
            playsinline
          ></video>
        </div>

        <div class="clip-body">
          <div class="clip-title">${clip.title}</div>
          <div class="clip-stats-row">
            <span class="stat-item">⏱ ${formatTime(clip.start)} - ${formatTime(clip.end)} (${clip.duration}s)</span>
            <span>•</span>
            <span class="stat-item" style="color: var(--accent-cyan); font-weight: 600;">${clip.trigger || 'Viral Hook'}</span>
          </div>

          <div class="clip-hook-summary">
            "${clip.summary || 'Peak engagement highlight with high curiosity retention.'}"
          </div>

          ${clip.rule_reasons && clip.rule_reasons.length > 0 ? `
            <div class="rule-compliance-reasons">
              <span>🎯 ${clip.rule_reasons[0]}</span>
            </div>
          ` : ''}

          <div class="metrics-bars">
            <div class="metric-bar-item">
              <div class="metric-bar-label">
                <span>Campaign Rule Match</span>
                <span style="color: var(--accent-cyan); font-weight: 700;">${clip.rule_score || 100}%</span>
              </div>
              <div class="metric-track">
                <div class="metric-fill rules" style="width: ${clip.rule_score || 100}%;"></div>
              </div>
            </div>
            <div class="metric-bar-item">
              <div class="metric-bar-label">
                <span>Hook Strength</span>
                <span>${clip.hook_score}%</span>
              </div>
              <div class="metric-track">
                <div class="metric-fill hook" style="width: ${clip.hook_score}%;"></div>
              </div>
            </div>
            <div class="metric-bar-item">
              <div class="metric-bar-label">
                <span>Retention Flow</span>
                <span>${clip.retention_score}%</span>
              </div>
              <div class="metric-track">
                <div class="metric-fill" style="width: ${clip.retention_score}%;"></div>
              </div>
            </div>
          </div>

          <div class="clip-card-actions">
            <a href="${clip.video_url}" download="${clip.download_name}" class="btn-card-action primary">
              <span>⬇</span>
              <span>Download MP4</span>
            </a>
            <button type="button" class="btn-card-action btn-fine-tune" data-clip-id="${clip.id}">
              <span>✂</span>
              <span>Fine-Tune</span>
            </button>
            <button type="button" class="btn-card-action btn-copy-meta" data-clip-id="${clip.id}">
              <span>📋</span>
            </button>
          </div>
        </div>
      `;

      // Fine-Tune Handler
      card.querySelector('.btn-fine-tune').addEventListener('click', () => openTrimModal(clip));

      // Copy Details Handler
      card.querySelector('.btn-copy-meta').addEventListener('click', () => {
        const text = `Clip #${clip.id}: ${clip.title}\nTimestamps: ${formatTime(clip.start)} - ${formatTime(clip.end)}\nVirality: ${clip.virality_score}/100 | Rule Match: ${clip.rule_score || 100}%`;
        navigator.clipboard.writeText(text);
        showToast(`Clip #${clip.id} details copied to clipboard!`, 'info');
      });

      clipsGrid.appendChild(card);
    });
  }

  // Filter Chips Logic
  filterChips.forEach(chip => {
    chip.addEventListener('click', () => {
      filterChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const filter = chip.dataset.filter;
      state.activeFilter = filter;

      const cards = document.querySelectorAll('.clip-card');
      cards.forEach(card => {
        const score = parseInt(card.dataset.score, 10);
        const ruleScore = parseInt(card.dataset.ruleScore, 10);
        if (filter === 'all') {
          card.style.display = 'flex';
        } else if (filter === 'rules') {
          card.style.display = ruleScore >= 70 ? 'flex' : 'none';
        } else if (filter === 'mega') {
          card.style.display = score >= 90 ? 'flex' : 'none';
        } else if (filter === 'high') {
          card.style.display = score >= 80 ? 'flex' : 'none';
        }
      });
    });
  });

  // Fine-Tune Trim Modal Logic
  function openTrimModal(clip) {
    state.activeTrimClip = clip;
    const maxDur = state.currentMeta ? state.currentMeta.duration : clip.end + 60;
    
    trimStartSlider.min = 0;
    trimStartSlider.max = Math.max(10, clip.end);
    trimStartSlider.value = clip.start;

    trimEndSlider.min = clip.start;
    trimEndSlider.max = Math.min(maxDur, clip.end + 60);
    trimEndSlider.value = clip.end;

    trimStartDisplay.textContent = formatTime(clip.start);
    trimEndDisplay.textContent = formatTime(clip.end);

    trimModal.classList.add('open');
  }

  function closeTrimModal() {
    trimModal.classList.remove('open');
    state.activeTrimClip = null;
  }

  modalCloseBtn.addEventListener('click', closeTrimModal);
  trimModal.addEventListener('click', (e) => {
    if (e.target === trimModal) closeTrimModal();
  });

  trimStartSlider.addEventListener('input', () => {
    let startVal = parseFloat(trimStartSlider.value);
    let endVal = parseFloat(trimEndSlider.value);
    if (startVal >= endVal - 5) {
      startVal = endVal - 5;
      trimStartSlider.value = startVal;
    }
    trimStartDisplay.textContent = `${formatTime(startVal)} (${startVal.toFixed(1)}s)`;
  });

  trimEndSlider.addEventListener('input', () => {
    let startVal = parseFloat(trimStartSlider.value);
    let endVal = parseFloat(trimEndSlider.value);
    if (endVal <= startVal + 5) {
      endVal = startVal + 5;
      trimEndSlider.value = endVal;
    }
    trimEndDisplay.textContent = `${formatTime(endVal)} (${endVal.toFixed(1)}s)`;
  });

  btnSaveTrim.addEventListener('click', async () => {
    if (!state.activeTrimClip || !state.jobId) return;

    const clip = state.activeTrimClip;
    const newStart = parseFloat(trimStartSlider.value);
    const newEnd = parseFloat(trimEndSlider.value);

    btnSaveTrim.disabled = true;
    btnSaveTrim.innerHTML = '<span>Rendering new timestamps with FFmpeg...</span>';

    try {
      const res = await fetch('/api/trim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: state.jobId,
          clip_id: clip.id,
          start: newStart,
          end: newEnd
        })
      });

      if (!res.ok) throw new Error('Trim failed');
      const data = await res.json();
      
      // Update state clip
      clip.start = newStart;
      clip.end = newEnd;
      clip.duration = Math.round((newEnd - newStart) * 10) / 10;
      clip.video_url = data.clip.video_url;

      // Update card video player
      const card = document.querySelector(`.clip-card[data-clip-id="${clip.id}"]`);
      if (card) {
        const video = card.querySelector('.clip-video');
        video.src = clip.video_url;
        video.load();
        const statItem = card.querySelector('.clip-stats-row .stat-item');
        if (statItem) {
          statItem.textContent = `⏱ ${formatTime(clip.start)} - ${formatTime(clip.end)} (${clip.duration}s)`;
        }
      }

      showToast(`Clip #${clip.id} trimmed and re-rendered!`, 'success');
      closeTrimModal();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      btnSaveTrim.disabled = false;
      btnSaveTrim.innerHTML = '<span>✂ Re-Cut Clip with New Timestamps</span>';
    }
  });

  // Initialize
  loadSamples();
});
