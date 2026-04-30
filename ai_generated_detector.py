import torch
from PIL import Image
from transformers import pipeline


_detector = None


def get_ai_image_detector():
    global _detector

    if _detector is None:
        device = 0 if torch.cuda.is_available() else -1

        _detector = pipeline(
            task="image-classification",
            model="Ateeqq/ai-vs-human-image-detector",
            device=device
        )

    return _detector


def detect_ai_generated_image(image_path: str) -> dict:
    try:
        detector = get_ai_image_detector()

        image = Image.open(image_path).convert("RGB")
        results = detector(image)

        top = results[0]
        label = top.get("label", "Unknown")
        score = float(top.get("score", 0))

        label_lower = label.lower()

        if "ai" in label_lower or "fake" in label_lower or "generated" in label_lower:
            verdict = "Likely AI-Generated" if score >= 0.75 else "Possibly AI-Generated"
        else:
            verdict = "Likely Real / Camera Image" if score >= 0.60 else "Uncertain"

        return {
            "success": True,
            "verdict": verdict,
            "label": label,
            "score": round(score * 100, 2),
            "raw_results": results[:3]
        }

    except Exception as e:
        return {
            "success": False,
            "verdict": "AI Detector Error",
            "label": "Error",
            "score": 0,
            "raw_results": [],
            "error": str(e)
        }
