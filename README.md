# ⚡ OpusCut AI - Auto Clipper for Long-Form Videos to Viral Shorts

Transform long-form YouTube videos, podcasts, and video uploads into high-retention 9:16 vertical viral shorts for TikTok, Instagram Reels, and YouTube Shorts. 

Includes **Psychological Hook Detection**, **Virality Scoring (0-100)**, **AI Campaign Rules Matching (from text or rule screenshots via OCR)**, and **Ultra-Fast FFmpeg Rendering** with blurred ambient glow or solid black backgrounds.

---

## 🌟 Key Features

- **🎯 AI Virality & Retention Scoring (0–100)**:
  - Scans transcripts and speech patterns to identify high-retention moments and viral hooks (rhetorical questions, curiosity gaps, bold statements, story openers).
  - Eliminates filler and selects punchy, complete thoughts with natural sentence boundaries.

- **📋 AI Campaign Rules Engine (Image OCR & Briefs)**:
  - **Upload Rule Screenshots**: Drag & drop screenshots of Discord campaign guidelines, brand kits, or client briefs.
  - **Native OCR**: Instantly extracts and parses text into actionable rules (positive keywords, banned topics, required hook types, duration targets).
  - **Strict Negative Filtering**: Automatically disqualifies or penalizes moments containing forbidden words or off-topic content.
  - **1-Click Campaign Presets**: Quick buttons for TikTok Viral Growth, SaaS Scaling, Mindset & Performance, Wealth & Investing, and Step-by-Step How-To.

- **📱 Multi-Format Layout Engine**:
  - **9:16 Vertical** (optimized for TikTok, Reels, Shorts)
  - **16:9 Landscape** & **1:1 Square**
  - **Framing Styles**:
    - *Opus Blur*: High-speed ambient blurred background with centered foreground.
    - *Solid Black Background*: Clean letterbox/pillarbox with `#000000` padding.
    - *Center Crop*: Full screen fill.

- **⚡ Blazing Fast FFmpeg Engine**:
  - Hardware-optimized filter graphs render 25-second 1080x1920 HD vertical video in **~3.7 seconds** (a 15x speedup over standard blur pipelines).
  - Universal browser playback with strict `yuv420p` encoding.

- **✂ Bulk Generation & Fine-Tuning**:
  - Request **3, 5, 10, 20, 30, 50, 100**, or custom clip counts in bulk.
  - Interactive slider modal to fine-tune clip start and end timestamps.
  - **1-Click Batch ZIP Download** containing all generated clips.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.10+**
- **FFmpeg 4.0+** (must be on system `PATH`)

Check FFmpeg installation:
```bash
ffmpeg -version
```

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/sandeepthala07-png/auto-clip-og.git
cd auto-clip-og
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python server.py
```

Open your browser at:
```
http://localhost:8000
```

---

## 📁 Project Structure

```
├── server.py              # FastAPI server & background job pipeline
├── video_engine.py        # High-performance FFmpeg rendering & YouTube stream processing
├── analyzer.py            # Virality scoring, hook detection & candidate segmentation
├── rules_engine.py        # Campaign rules parser, compliance scoring & OCR bridge
├── ocr_helper.ps1         # Windows native OCR script for screenshot analysis
├── generate_samples.py    # Generates local demo master videos and sample transcripts
├── requirements.txt       # Project dependencies
├── static/
│   ├── index.html         # Modern dark-mode Studio UI
│   ├── css/style.css      # Glassmorphic responsive styling
│   └── js/app.js          # Interactive frontend logic & progress tracking
└── samples/               # Pre-packaged demo master videos & transcripts
```

---

## 📜 License
MIT License
