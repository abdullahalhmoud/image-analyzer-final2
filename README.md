# 🕵️‍♀️ Stellar Forensics Engine - Advanced AI Digital Forensics Platform

### A Next-Generation AI-Powered Digital Forensics, Steganography Detection, Hidden Payload Extraction, and AI-Generated Image Verification System

---

# 🌟 Overview

Stellar Forensics Engine is a professional-grade digital forensic analysis platform engineered for:

- Hidden payload extraction
- Steganography detection
- AI-generated image verification
- Metadata integrity validation
- C2PA synthetic media verification
- Error Level Analysis (ELA)
- OCR-based embedded text analysis
- Traditional forensic extraction
- Manual forensic scoring
- Security-grade reporting

---

# 🔬 Core Capabilities

## Traditional Forensics Engine
- Steghide payload extraction
- StegSleuth heuristic detection
- Manual forensic scoring
- Hidden stream detection
- OCR artifact extraction
- EXIF metadata analysis
- Embedded file recovery
- Suspicious binary stream analysis

---

## 🤖 AI Forensics Engine
- AI-generated image classifier
- Synthetic media detection
- GAN detection
- Human vs AI classification
- Model confidence scoring
- Fully separated AI authenticity verdict
- Does NOT alter hidden payload verdict

---

## 📷 Metadata Intelligence Engine
- Camera Make / Model
- GPS coordinates
- File creation timestamps
- Software generation history
- C2PA provenance verification
- OpenAI / GPT image generation traces
- Synthetic media source indicators
- JUMD source verification

---

## 🧪 Image Tampering Detection
- Error Level Analysis (ELA)
- Compression artifact analysis
- Image manipulation heatmaps
- Structural anomaly identification

---

# 🛡️ Final Decision Categories

- CRITICAL / HIDDEN PAYLOAD CONFIRMED
- SUSPICIOUS / STEGHIDE PAYLOAD DETECTED
- SUSPICIOUS / STEGSLEUTH FLAG ONLY
- SUSPICIOUS / MANUAL FORENSIC INDICATORS
- LOW RISK / WEAK WARNING
- ANALYSIS COMPLETE / CLEAN

---

# 🎨 User Experience Features

- Modern glassmorphism forensic dashboard
- Responsive web UI
- Dynamic HTML reports
- PDF forensic reports
- JSON forensic exports
- Hidden payload download support
- Extracted file recovery
- AI visual authenticity section
- EXIF deep analysis dashboard
- Clean verdict separation

---

# 🚀 Full Installation Guide

## 📋 System Requirements

### Operating Systems:
- Kali Linux (Recommended)
- Ubuntu / Debian
- Windows (WSL optional)
- macOS

---

## 🐍 Python Requirements
- Python 3.10+
- pip
- virtualenv

---
# ⚙️ Step 1: Clone Repository

```bash
git clone https://github.com/abdullahalhmoud/image-analyzer-final2.git
cd image-analyzer-final2
```

# ⚙️ Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

# ⚙️ Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

# ⚙️ Step 4: Install External Forensic Tools

## Steghide

```bash
sudo apt update
sudo apt install steghide -y
```

## ExifTool

```bash
sudo apt install libimage-exiftool-perl -y
```

## Tesseract OCR

```bash
sudo apt install tesseract-ocr -y
```

## PDF Analysis Tool

```bash
sudo apt install poppler-utils -y
```

## Binwalk (Optional)

```bash
sudo apt install binwalk -y
```

## Zsteg (Optional for PNG)

```bash
sudo gem install zsteg
```

# ⚙️ Step 5: Verify Installations

```bash
steghide --version
exiftool -ver
tesseract --version
pdfinfo -v
binwalk --help
```

# ▶️ Running the Project

```bash
python app.py
```

# 🌐 Default Access

```text
http://127.0.0.1:5000
```

# 🌐 Production Deployment

## Gunicorn

```bash
gunicorn app:app
```

## Render Deployment

### Build Command

```bash
pip install -r requirements.txt
```

### Start Command

```bash
gunicorn app:app
```
### 📁 Recommended Project Structure
```bash
image-analyzer/
│
├── app.py
├── ai_model.py
├── ai_generated_detector.py
├── core_management.py
├── requirements.txt
├── report_template.html
│
├── templates/
│   ├── result.html
│   └── report_template.html
│
├── static/
├── reports/
├── tools/
│   └── stegsleuth/
│
└── models/

