# 🕵️‍♀️ Stellar Forensics Engine - AI Digital Forensics Tool

> **A Next-Generation Digital Forensics & Steganography Analysis Platform**
> *Powered by Artificial Intelligence & Advanced Image Processing*

## 🌟 Overview
**Stellar Forensics** is a powerful, web-based tool designed to analyze digital images for signs of tampering, manipulation, and hidden data. Built with a modern, sci-fi inspired interface, it combines traditional forensic techniques (ELA, EXIF) with state-of-the-art AI detection to provide comprehensive forensic reports.

## ✨ Key Features

### 🔍 Deep Analysis
- **Error Level Analysis (ELA)**: Detects compression artifacts to identify manipulated areas.
- **AI-Powered Detection**: Uses a trained `EfficientNet-B0` model to classify images as "Real" or "AI-Generated/Forged".
- **Metadata Extraction**: Pulls EXIF data, including Camera Make/Model, Datestamps, and GPS Coordinates.
- **Steganography Checks**: Scans for hidden data embedded within image files.

### 🎨 Modern Experience
- **Stunning UI**: Dark-mode, glassmorphism design with responsive animations.
- **Drag & Drop**: Seamless file upload experience.
- **Instant Reporting**: Generates dynamic HTML & PDF reports.
- **Cross-Platform**: Runs on Windows, macOS, and Linux (Auto-launches in Firefox/Default Browser).

## 🚀 How to Run

### Prerequisites
- Python 3.8+
- Firefox (Recommended for best experience)

### Installation
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/stellar-forensics.git
   cd stellar-forensics
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure `torch` and `torchvision` are compatible with your system)*

3. **External Tools (Optional for full power):**
   - Install `steghide` and `binwalk` for advanced hidden data extraction.

### Usage
Run the application with a single command:
```bash
python app.py
```
The application will automatically launch in your browser at `http://127.0.0.1:5001`.

## 🌐 Deployment (Live Website)

### Using Render (Recommended)
This project is configured for easy deployment on [Render](https://render.com).

1. **Push code to GitHub**.
2. **Sign up on Render** and create a **New Web Service**.
3. **Connect your GitHub repository**.
4. **Settings**:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Click **Create Web Service**. 🚀

## 🛡️ Security Features
- **File Validation**: Strict checking for allowed image types (JPG, PNG, TIFF, etc.).
- **Size Limit**: Supports high-resolution images up to **50 MB**.
- **Safe Execution**: Sandboxed execution of external forensic tools.

## 🛠️ Tech Stack
- **Backend**: Python (Flask)
- **Frontend**: HTML5, CSS3, JavaScript (No frameworks needed)
- **AI Core**: PyTorch (EfficientNet)
- **Image Processing**: PIL (Pillow)

---
*Created by [Reham] - 2025*
