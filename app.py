import os
import uuid
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict, Tuple, Any, Optional

from flask import Flask, request, jsonify, send_file, render_template
from PIL import Image, ExifTags, ImageChops
from werkzeug.utils import secure_filename

# AI Detection Module
try:
    from ai_model import quick_predict
    AI_AVAILABLE = True
    print("✅ AI Detection Module imported successfully")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI Detection not available: {e}")
    
# AI-Generated Image Detector Module
try:
    from ai_generated_detector import detect_ai_generated_image
    AI_GENERATED_DETECTOR_AVAILABLE = True
    print("✅ AI-Generated Image Detector imported successfully")
except ImportError as e:
    AI_GENERATED_DETECTOR_AVAILABLE = False
    print(f"⚠️ AI-Generated Image Detector not available: {e}")

# PDF Generation - Using browser print-to-PDF
PDF_AVAILABLE = True  # Always available via browser print

# =========================
# App Configuration
# =========================
app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# File Upload Configuration
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'gif'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

import numpy as np
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.float32):
            return float(obj)
        return super(NumpyEncoder, self).default(obj)


def validate_file(file) -> Tuple[bool, str]:
    """Validate uploaded file type and size"""
    if not file or file.filename == '':
        return False, "No file selected"
    
    # Check file extension
    filename = file.filename.lower()
    if '.' not in filename:
        return False, "File must have an extension"
    
    ext = filename.rsplit('.', 1)[1]
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS).upper()}"
    
    # Check file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        current_mb = file_size / (1024 * 1024)
        return False, f"File too large ({current_mb:.1f}MB). Maximum allowed: {max_mb:.0f}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, "Valid file"

# =========================
# Helper: Safe tool execution
# =========================
def safe_run(cmd, timeout=60):
    exe = cmd[0]
    if shutil.which(exe) is None:
        return {"available": False, "returncode": None, "stdout": "", "stderr": "Tool not available"}

    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        return {
            "available": True,
            "returncode": p.returncode,
            "stdout": p.stdout or "",
            "stderr": p.stderr or "",
        }
    except Exception as e:
        return {"available": True, "returncode": -1, "stdout": "", "stderr": str(e)}


# =========================
# EXIF helpers
# =========================
def _rational_to_float(value) -> Optional[float]:
    try:
        if isinstance(value, tuple) and len(value) == 2:
            num, den = value
            return float(num) / float(den) if den else None
        return float(value)
    except Exception:
        return None

def _gps_to_degrees(gps_coord) -> Optional[float]:
    try:
        d = _rational_to_float(gps_coord[0])
        m = _rational_to_float(gps_coord[1])
        s = _rational_to_float(gps_coord[2])
        if None in (d, m, s):
            return None
        return d + (m / 60) + (s / 3600)
    except Exception:
        return None

# =========================
# ELA: Error Level Analysis
# =========================
def perform_ela(image_path: str, output_path: str, quality: int = 90):
    try:
        tmp_ela = output_path + ".tmp.jpg"
        im = Image.open(image_path).convert("RGB")
        im.save(tmp_ela, "JPEG", quality=quality)
        
        resaved_im = Image.open(tmp_ela)
        ela_im = ImageChops.difference(im, resaved_im)
        
        extrema = ela_im.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
        scale = 255.0 / max_diff
        
        ela_im = ela_im.point(lambda i: i * scale)
        ela_im.save(output_path)
        
        if os.path.exists(tmp_ela):
            os.remove(tmp_ela)
        return True
    except Exception as e:
        print(f"ELA Error: {e}")
        return False


# =========================
# EXIF via exiftool (NEW)
# =========================
def extract_exif_with_exiftool(image_path: str) -> Dict[str, Any]:
    result = {
        "camera_make": None,
        "camera_model": None,
        "datetime_original": None,
        "gps": {"present": False, "latitude": None, "longitude": None},
        "source": "exiftool",
        "all_tags": {},
        "tag_count": 0,
        "has_camera_info": False,
        "file_info": {},
        "image_info": {},
        "software_info": None,
        "note": None
    }

    try:
        cmd = ["exiftool", "-json", "-G1", image_path]
        exif_result = safe_run(cmd, timeout=30)
        
        if not exif_result["available"] or exif_result["returncode"] != 0:
            return extract_exif_with_pil(image_path)
        
        exif_data_list = json.loads(exif_result["stdout"])
        exif_data = exif_data_list[0]
        
        result["all_tags"] = exif_data
        result["tag_count"] = len([k for k in exif_data if k != "SourceFile"])
        
        # ========== FILE INFO (مثل اللي شفته) ==========
        file_keys = ["System:File Name", "System:File Size", "System:File Modification Date/Time",
                    "File:File Type", "File:MIME Type", "File:Image Width", "File:Image Height"]
        for key in file_keys:
            clean_key = key.replace("System:", "").replace("File:", "").replace(" ", "_")
            if key in exif_data:
                result["file_info"][clean_key] = str(exif_data[key])
        
        # ========== DATE ==========
        date_priority = [
            "System:File Modification Date/Time",
            "File:FileModifyDate", 
            "EXIF:ModifyDate",
            "EXIF:DateTimeOriginal"
        ]
        for key in date_priority:
            if key in exif_data:
                result["datetime_original"] = str(exif_data[key])
                break
        
        # ========== IMAGE INFO ==========
        img_keys = ["Composite:Image Size", "Composite:Megapixels", "JFIF:JFIFVersion"]
        for key in img_keys:
            if key in exif_data:
                result["image_info"][key] = str(exif_data[key])
        
        # ========== SOFTWARE/CAMERA ==========
        for key, value in exif_data.items():
            key_lower = key.lower()
            if any(x in key_lower for x in ["make", "camera"]):
                result["camera_make"] = str(value)
                result["has_camera_info"] = True
            elif any(x in key_lower for x in ["model"]):
                result["camera_model"] = str(value)
                result["has_camera_info"] = True
            elif "software" in key_lower:
                result["software_info"] = str(value)
        
        if "JFIF:JFIFVersion" in exif_data and not result["has_camera_info"]:
            result["camera_make"] = "JPEG Compressor"
            result["camera_model"] = "Software Generated"
            result["note"] = "Compressed image (JFIF format)"
        
        return result

    except Exception as e:
        result["note"] = f"Error: {e}"
        return result

# =========================
# EXIF via PIL fallback
# =========================
def extract_exif_with_pil(image_path: str) -> Dict[str, Any]:
    result = {
        "camera_make": None,
        "camera_model": None,
        "datetime_original": None,
        "gps": {"present": False, "latitude": None, "longitude": None},
        "source": "PIL",
        "all_tags": {},
        "tag_count": 0,
        "has_camera_info": False,
        "file_info": {},
        "image_info": {},
        "software_info": None,
        "note": None,
    }

    try:
        img = Image.open(image_path)
        exif = img.getexif()

        if not exif:
            result["note"] = "No EXIF metadata found."
            return result

        tags = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
        result["all_tags"] = {str(k): str(v) for k, v in tags.items()}
        result["tag_count"] = len(tags)

        result["camera_make"] = tags.get("Make")
        result["camera_model"] = tags.get("Model")
        result["datetime_original"] = tags.get("DateTimeOriginal") or tags.get("DateTime")
        result["has_camera_info"] = bool(result["camera_make"] or result["camera_model"])

        gps_info = tags.get("GPSInfo")
        if gps_info:
            gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_info.items()}
            result["gps"]["present"] = True

            lat = lon = None
            if "GPSLatitude" in gps_tags and "GPSLatitudeRef" in gps_tags:
                lat = _gps_to_degrees(gps_tags["GPSLatitude"])
                if lat is not None and gps_tags["GPSLatitudeRef"] == "S":
                    lat = -lat

            if "GPSLongitude" in gps_tags and "GPSLongitudeRef" in gps_tags:
                lon = _gps_to_degrees(gps_tags["GPSLongitude"])
                if lon is not None and gps_tags["GPSLongitudeRef"] == "W":
                    lon = -lon

            result["gps"]["latitude"] = lat
            result["gps"]["longitude"] = lon

        return result

    except Exception as e:
        result["note"] = f"PIL EXIF error: {e}"
        return result

# =========================
# Hidden data detection
# =========================
def detect_hidden_data(image_path: str, report_id: str) -> Tuple[str, str, Optional[str]]:
    report_path = os.path.join(REPORTS_DIR, report_id)
    payload_file = os.path.join(report_path, "payload.bin")

    # Try steghide (often requires password, but we try empty)
    safe_run(["steghide", "extract", "-sf", image_path, "-p", "", "-xf", payload_file])

    if os.path.exists(payload_file) and os.path.getsize(payload_file) > 0:
        return "DETECTED", "Hidden data successfully extracted using Steghide.", "payload.bin"

    # Try binwalk
    bw = safe_run(["binwalk", "-e", image_path, "-C", report_path])
    if bw["available"]:
        extracted_dir_name = f"_{os.path.basename(image_path)}.extracted"
        extracted_dir = os.path.join(report_path, extracted_dir_name)
        if os.path.isdir(extracted_dir):
            files = os.listdir(extracted_dir)
            if files:
                # Zip the extracted directory for download
                zip_name = f"extracted_files_{report_id}.zip"
                zip_path = os.path.join(report_path, zip_name)
                shutil.make_archive(zip_path.replace('.zip', ''), 'zip', extracted_dir)
                return "DETECTED", "Embedded files found and extracted within the image.", zip_name

    return "NOT_DETECTED", "No obvious hidden data found in this image.", None

def run_stegsleuth_analysis(image_path: str) -> dict:
    tool_dir = os.path.join(BASE_DIR, "tools", "stegsleuth")
    script_path = os.path.join(tool_dir, "stegsleuth.py")
    assets_dir = os.path.join(tool_dir, "assets")

    if not os.path.exists(script_path):
        return {
            "available": False,
            "detected": False,
            "verdict": "NOT_AVAILABLE",
            "hidden_stream_detected": False,
            "strong_hidden_stream": False,
            "summary": "StegSleuth script not found.",
            "error": ""
        }

    os.makedirs(assets_dir, exist_ok=True)

    for item in os.listdir(assets_dir):
        item_path = os.path.join(assets_dir, item)

        if os.path.isfile(item_path):
            os.remove(item_path)

    safe_name = secure_filename(os.path.basename(image_path))
    copied_path = os.path.join(assets_dir, safe_name)

    shutil.copy2(image_path, copied_path)

    commands = "list assets\nselect 1\nanalyze\nexit\n"

    try:
        process = subprocess.run(
            [sys.executable, script_path],
            input=commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tool_dir,
            timeout=180
        )

        output = (process.stdout or "") + "\n" + (process.stderr or "")
        output_lower = output.lower()

        no_reliable_detection = (
            "no reliable hidden data detected" in output_lower or
            "likely compression/noise artifact" in output_lower or
            "no reliable hidden payload indicators" in output_lower
        )

        high_confidence_detection = (
            "confidence: high" in output_lower or
            "known file signature found" in output_lower
        )

        medium_confidence_detection = (
            "confidence: medium" in output_lower and
            "balanced lsb stream" in output_lower
        )

        detected = high_confidence_detection or medium_confidence_detection

        if no_reliable_detection:
            detected = False

        return {
            "available": True,
            "detected": detected,
            "verdict": "DETECTED" if detected else "NOT_DETECTED",
            "hidden_stream_detected": high_confidence_detection or medium_confidence_detection,
            "strong_hidden_stream": high_confidence_detection,
            "summary": output[:6000],
            "error": process.stderr[:1500]
        }

    except Exception as e:
        return {
            "available": True,
            "detected": False,
            "verdict": "ERROR",
            "hidden_stream_detected": False,
            "strong_hidden_stream": False,
            "summary": "",
            "error": str(e)
        }
def run_steghide_check(image_path: str, report_path: str) -> dict:
    try:
        temp_dir = tempfile.mkdtemp()
        extracted_temp = os.path.join(temp_dir, "extracted_test")
        output_file = os.path.join(report_path, "extracted_payload")

        process = subprocess.run(
            [
                "steghide",
                "extract",
                "-sf",
                image_path,
                "-p",
                "",
                "-xf",
                extracted_temp,
                "-f"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        output = (process.stdout or "") + (process.stderr or "")

        detected = (
            "wrote extracted data" in output.lower()
            or "written extracted data" in output.lower()
            or "extracting" in output.lower()
            or os.path.exists(extracted_temp)
        )

        if detected and os.path.exists(extracted_temp):
            shutil.copy2(extracted_temp, output_file)

            return {
                "detected": True,
                "summary": output.strip(),
                "payload_path": output_file,
                "payload_filename": "extracted_payload"
            }

        return {
            "detected": False,
            "summary": output.strip(),
            "payload_path": None,
            "payload_filename": None
        }

    except Exception as e:
        return {
            "detected": False,
            "summary": str(e),
            "payload_path": None,
            "payload_filename": None
        }
# =========================
# Routes
# =========================
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/gui/analyze", methods=["POST"])

def gui_analyze():

    # =========================
    # Validate Upload
    # =========================
    if "image" not in request.files:
        return render_template("index.html", error="No image uploaded")

    image = request.files["image"]

    is_valid, message = validate_file(image)

    if not is_valid:
        return render_template("index.html", error=message)

    # =========================
    # Create Report Workspace
    # =========================
    report_id = uuid.uuid4().hex[:12]
    report_path = os.path.join(REPORTS_DIR, report_id)

    os.makedirs(report_path, exist_ok=True)

    filename = secure_filename(image.filename)
    image_path = os.path.join(report_path, filename)

    image.save(image_path)

    # =========================
    # Generate Grayscale Copy
    # =========================
    grayscale_filename = f"gray_{secure_filename(image.filename)}"
    grayscale_path = os.path.join(report_path, grayscale_filename)

    try:
        with Image.open(image_path) as img:
            gray_img = img.convert("L")
            gray_img.save(grayscale_path)

    except Exception:
        grayscale_filename = None

    # =========================
    # Error Level Analysis
    # =========================
    ela_filename = "ela_heatmap.jpg"
    ela_path = os.path.join(report_path, ela_filename)

    ela_success = perform_ela(image_path, ela_path)

    # =========================
    # Metadata Extraction
    # =========================
    metadata = extract_exif_with_exiftool(image_path)

    # =========================
    # Traditional Hidden Payload Detection
    # =========================
    status, explanation, payload_filename = detect_hidden_data(
        image_path,
        report_id
    )

    # =========================
    # StegSleuth Analysis
    # =========================
    stegsleuth_result = run_stegsleuth_analysis(image_path)

    # =========================
    # Extract full EXIF block from StegSleuth output
    # =========================
    full_stegsleuth_exif = ""

    if stegsleuth_result.get("summary"):
        summary_text = stegsleuth_result.get("summary", "")

        if "[*] Exif Data" in summary_text:
            exif_part = summary_text.split("[*] Exif Data", 1)[1]

            if "[*] Extracted Text From Image" in exif_part:
                exif_part = exif_part.split(
                    "[*] Extracted Text From Image",
                    1
                )[0]

            full_stegsleuth_exif = exif_part.strip()
    # =========================
    # Steghide Validation
    # =========================
    steghide_result = run_steghide_check(image_path, report_path)

    if steghide_result.get("detected"):
        status = "DETECTED"
        explanation = "Steghide detected embedded hidden payload."

    # =========================
    # Legacy AI Steganography Model
    # (Used only for stego indicators)
    # =========================
    ai_result = None

    model_path = os.path.join(
        BASE_DIR,
        "models",
        "best_stego_efficientnet_b4.pth"
    )

    model_exists = os.path.exists(model_path)

    if AI_AVAILABLE:
        try:
            ai_result = quick_predict(
                image_path,
                model_path if model_exists else None
            )

        except Exception as e:
            ai_result = {
                "success": False,
                "confidence": 0,
                "verdict": "Analysis Error",
                "verdict_en": "Analysis Error",
                "error": str(e)
            }

    else:
        ai_result = {
            "success": False,
            "confidence": 0,
            "verdict": "AI Not Available",
            "verdict_en": "AI Not Available",
            "model_available": False
        }

    # =========================
    # Dedicated AI-Generated Image Detector
    # Fully separate from payload verdict
    # =========================
    ai_generated_result = {
        "success": False,
        "verdict": "Unknown",
        "label": "Unavailable",
        "score": 0,
        "raw_results": []
    }

    if AI_GENERATED_DETECTOR_AVAILABLE:

        try:
            ai_generated_result = detect_ai_generated_image(
                image_path
            )

        except Exception as e:
            ai_generated_result = {
                "success": False,
                "verdict": "AI Detector Error",
                "label": "Error",
                "score": 0,
                "raw_results": [],
                "error": str(e)
            }

    # =========================
    # AI Generated Verdict
    # Separate visual authenticity only
    # =========================
    ai_generated_verdict = ai_generated_result.get(
        "verdict",
        "Unknown"
    )

    # =========================
    # Legacy AI Variables
    # =========================
    is_ai_suspicious = (
        ai_result.get("is_manipulated", False)
        if ai_result else False
    )

    ai_verdict = (
        ai_result.get("verdict", "Clean")
        if ai_result else "Clean"
    )

    ai_confidence = (
        ai_result.get("confidence", 0)
        if ai_result else 0
    )

    # =========================
    # Traditional Detection Status
    # =========================
    status_traditional = status

    # =========================
    # Statistical Indicators
    # =========================
    chi_score = (
        ai_result.get("chi_square_prob", 0)
        if ai_result else 0
    )

    entropy_score = (
        ai_result.get("lsb_entropy", 0)
        if ai_result else 0
    )

    noise_score = (
        ai_result.get("noise_density", 0)
        if ai_result else 0
    )

    certainty_score = (
        ai_result.get("certainty", 0)
        if ai_result else 0
    )

    ml_score = (
        ai_result.get("ml_probability", 0)
        if ai_result else 0
    )

    strong_hidden_stream = stegsleuth_result.get(
        "strong_hidden_stream",
        False
    )

    # =========================
    # Manual Analysis Score
    # =========================
    manual_score = 0
    manual_reasons = []
    # AI statistical indicators removed from final verdict
    lsb_strong = False
    lsb_very_strong = False
    
    # =========================
    # StegSleuth Evidence
    # =========================
    if stegsleuth_result.get("detected"):

        if entropy_score < 0.85:
            manual_score += 90
            manual_reasons.append(
                "StegSleuth detected suspicious patterns with structured low-entropy hidden bitstream characteristics."
            )

        else:
            manual_score += 20
            manual_reasons.append(
                "StegSleuth detected weak suspicious patterns, but evidence is not conclusive."
            )


    # =========================
    # Traditional Forensic Evidence
    # =========================
    if status_traditional == "DETECTED":
        manual_score += 120
        manual_reasons.append(
            "Traditional forensic tools confirmed hidden payload or embedded data."
        )

    # =========================
    # Weak EXIF Indicators
    # =========================
    if metadata.get("note") == "No EXIF metadata found.":
        manual_score += 5
        manual_reasons.append("EXIF metadata is missing.")

    if not metadata.get("camera_make"):
        manual_score += 3
        manual_reasons.append("Camera make is missing.")

    if not metadata.get("camera_model"):
        manual_score += 3
        manual_reasons.append("Camera model is missing.")

    if not metadata.get("datetime_original"):
        manual_score += 5
        manual_reasons.append("Original capture date is missing.")

    # =========================
    # Strong Confirmation Logic
    # =========================
    strong_stegsleuth = (
        stegsleuth_result.get("detected")
        and (
            status_traditional == "DETECTED"
            or (
                strong_hidden_stream
                and status_traditional == "DETECTED"
            )
        )
    )

    # =========================
    # FINAL VERDICT
    # Hidden Payload / Malicious File ONLY
    # AI-Generated result does NOT affect this
    # =========================

    if status_traditional == "DETECTED":
        overall_verdict = "CRITICAL / HIDDEN PAYLOAD CONFIRMED"
        overall_badge = "red"
        final_source = "Traditional Forensic Tools"
        unified_explanation = (
            "Traditional forensic tools confirmed hidden or embedded payloads inside the image."
        )

    elif strong_hidden_stream:
        overall_verdict = "SUSPICIOUS / STEGSLEUTH FLAG ONLY"
        overall_badge = "orange"
        final_source = "StegSleuth Warning"
        unified_explanation = (
            "StegSleuth detected possible hidden bitstream patterns, but no payload was extracted "
            "and no traditional forensic tool confirmed hidden data."
        )

    elif stegsleuth_result.get("detected"):
        overall_verdict = "LOW RISK / WEAK STEGSLEUTH WARNING"
        overall_badge = "green"
        final_source = "Manual Forensic Analysis"
        unified_explanation = (
            "StegSleuth reported weak suspicious patterns, but no traditional forensic confirmation was found."
        )

    elif manual_score >= 40:
        overall_verdict = "SUSPICIOUS / MANUAL FORENSIC INDICATORS"
        overall_badge = "orange"
        final_source = "Manual Forensic Analysis"
        unified_explanation = (
            "Manual forensic indicators were found, but no confirmed hidden payload was extracted."
        )

    else:
        overall_verdict = "ANALYSIS COMPLETE / CLEAN"
        overall_badge = "green"
        final_source = "Manual Forensic Analysis"
        unified_explanation = (
            "No confirmed hidden payload or strong forensic evidence was found."
        )

    # =========================
    # Manual Analysis Summary
    # =========================
    manual_analysis = {
        "score": manual_score,
        "reasons": manual_reasons,
        "final_source": final_source,
        "stegsleuth_detected": stegsleuth_result.get(
            "detected",
            False
        ),
        "lsb_strong": lsb_strong,
        "lsb_very_strong": lsb_very_strong,
        "strong_stegsleuth_confirmed": strong_stegsleuth
    }

    # =========================
    # Theme Colors
    # =========================
    theme_colors = {
        "red": {
            "bg": "#fef2f2",
            "border": "#fca5a5",
            "text": "#991b1b"
        },

        "orange": {
            "bg": "#fff7ed",
            "border": "#fdba74",
            "text": "#9a3412"
        },

        "green": {
            "bg": "#f0fdf4",
            "border": "#86efac",
            "text": "#166534"
        }
    }

    colors = theme_colors.get(
        overall_badge,
        theme_colors["green"]
    )
    # =========================
    # AI REPORT SECTION 
    # =========================
    ai_report_section = f"""
4) AI-Generated Image Analysis
AI Image Verdict: {ai_generated_verdict}
Model Label: {ai_generated_result.get("label", "Unknown") if ai_generated_result else "Unknown"}
AI Detector Score: {ai_generated_result.get("score", 0) if ai_generated_result else 0}%

Purpose:
This module only estimates whether the image was generated by AI.
It is fully separated from hidden payload, steganography,
and malware detection.

AI-generated image detection does NOT affect the final forensic
payload verdict.
"""

    # =========================
    # REPORT DATA
    # =========================
    report_data = {
        "report_id": report_id,
        "generated_at": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "input_filename": secure_filename(image.filename),
        "image_url": f"/report/{report_id}/file/{secure_filename(image.filename)}",
        "file_size": os.path.getsize(image_path),

        # Metadata
        "metadata": metadata,
        "exif_source": metadata.get("source", "unknown"),
        "exif_tag_count": metadata.get("tag_count", 0),
        "exif_note": metadata.get("note"),
        "has_camera_info": metadata.get("has_camera_info", False),

        # Analysis Results
        "status": status,
        "explanation": explanation,
        "stegsleuth_result": stegsleuth_result,
        "full_stegsleuth_exif": full_stegsleuth_exif,
        "steghide_result": steghide_result,
        "ela_image": (
            f"/report/{report_id}/file/{ela_filename}"
            if ela_success else None
        ),
        "grayscale_image": (
            f"/report/{report_id}/file/{grayscale_filename}"
            if grayscale_filename else None
        ),

        # Final Verdict
        "plain_badge_class": overall_badge,
        "plain_overall": overall_verdict,
        "plain_hidden_answer": (
            "Yes, content detected"
            if overall_badge != "green"
            else "None"
        ),
        "plain_hidden_explain": unified_explanation,
        "plain_tampering_explain": (
            "Authentic"
            if metadata.get("has_camera_info")
            else "Possible software processing"
        ),
        "plain_signals": (
            "Digital fingerprint verified"
            if metadata.get("tag_count", 0) > 10
            else "Limited metadata"
        ),
        "plain_note": (
            "Automated analysis - manual review recommended for critical cases."
        ),

        # AI Visual Classification ONLY
        "ai_result": ai_result,
        "ai_generated_result": ai_generated_result,
        "ai_available": AI_AVAILABLE,
        "ai_confidence": ai_confidence,
        "ai_verdict": ai_verdict,
        "ai_generated_verdict": ai_generated_verdict,
        "ai_is_manipulated": is_ai_suspicious,
        "ai_report_section": ai_report_section,

        # Manual Results
        "manual_analysis": manual_analysis,
        "final_decision_source": final_source,

        # Theme
        "theme_bg": colors["bg"],
        "theme_border": colors["border"],
        "theme_text": colors["text"],

        # Downloads
        "payload_url": (
            f"/report/{report_id}/payload"
            if payload_filename else None
        ),
        "html_url": f"/report/{report_id}/html",
        "steghide_payload_url": (
            f"/report/{report_id}/file/extracted_payload"
            if steghide_result and steghide_result.get("detected")
            else None
        ),
        "json_url": f"/report/{report_id}/json",
        "download_url": f"/report/{report_id}/download",
        "pdf_url": f"/report/{report_id}/pdf"
        
    }

    # =========================
    # Save JSON Report
    # =========================
    with open(
        os.path.join(report_path, "analysis.json"),
        "w"
    ) as f:
        json.dump(
            report_data,
            f,
            indent=2,
            cls=NumpyEncoder
        )

    # =========================
    # Save HTML Report
    # =========================
    html_content = render_template(
        "report_template.html",
        **report_data
    )

    with open(
        os.path.join(report_path, "report.html"),
        "w",
        encoding="utf-8"
    ) as f:
        f.write(html_content)

    # =========================
    # Final UI Render
    # =========================
    return render_template(
        "result.html",
        **report_data
    )
@app.route("/report/<rid>/file/<filename>")
def view_file(rid, filename):
    return send_file(os.path.join(REPORTS_DIR, rid, filename))

@app.route("/report/<rid>/html")
def view_html(rid):
    return send_file(os.path.join(REPORTS_DIR, rid, "report.html"))

@app.route("/report/<rid>/json")
def view_json(rid):
    return send_file(os.path.join(REPORTS_DIR, rid, "analysis.json"))

@app.route("/report/<rid>/download")
def download_report(rid):
    path = os.path.join(REPORTS_DIR, rid, "report.html")
    return send_file(path, as_attachment=True, download_name=f"forensic_report_{rid}.html")

@app.route("/report/<rid>/payload")
def download_payload(rid):
    # Find any .bin or .zip file that was extracted
    report_path = os.path.join(REPORTS_DIR, rid)
    if not os.path.exists(report_path):
        return jsonify({"error": "Report not found"}), 404
    
    files = os.listdir(report_path)
    payload_file = None
    for f in files:
        if f.endswith(".zip") or f == "payload.bin":
            payload_file = f
            break
            
    if payload_file:
        return send_file(os.path.join(report_path, payload_file), as_attachment=True)
    return jsonify({"error": "No payload found"}), 404

@app.route("/report/<rid>/pdf")
def download_pdf(rid):
    """Serve HTML report with print dialog for PDF export"""
    html_path = os.path.join(REPORTS_DIR, rid, "report.html")
    
    if not os.path.exists(html_path):
        return jsonify({"error": "Report not found"}), 404
    
    # Read HTML and inject print script
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Add auto-print script before closing body tag
    print_script = """
    <script>
        window.onload = function() {
            // Set document title for PDF filename
            document.title = 'Forensic_Report_""" + rid + """';
            // Trigger print dialog
            setTimeout(function() {
                window.print();
            }, 800);
        };
    </script>
    """
    
    html_content = html_content.replace('</body>', print_script + '</body>')
    
    from flask import Response
    return Response(html_content, mimetype='text/html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
