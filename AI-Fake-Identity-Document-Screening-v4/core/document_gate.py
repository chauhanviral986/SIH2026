# document_gate.py

import cv2
import numpy as np


def document_gate(image):
    """
    Basic image/document suitability check.

    This does NOT prove that a document is genuine.
    It only checks whether the image is suitable
    for further OCR and screening.
    """

    result = {
        "accepted": False,
        "document_type": "Unknown",
        "confidence": 0.0,
        "message": "",
        "checks": {},
    }

    # -----------------------------
    # Check image
    # -----------------------------
    if image is None:
        result["message"] = "No image was supplied."
        return result

    if not isinstance(image, np.ndarray):
        result["message"] = "Invalid image format."
        return result

    if image.size == 0:
        result["message"] = "Uploaded image is empty."
        return result

    # -----------------------------
    # Dimensions
    # -----------------------------
    height, width = image.shape[:2]

    result["checks"]["width"] = width
    result["checks"]["height"] = height

    if width < 400 or height < 250:
        result["message"] = (
            "Image resolution is too low. "
            "Please upload a clearer document image."
        )
        result["checks"]["resolution"] = False
        return result

    result["checks"]["resolution"] = True

    # -----------------------------
    # Aspect ratio
    # -----------------------------
    aspect_ratio = width / height

    result["checks"]["aspect_ratio"] = round(aspect_ratio, 2)

    if aspect_ratio < 0.45 or aspect_ratio > 2.8:
        result["message"] = (
            "Image shape is not suitable for document screening."
        )
        result["checks"]["shape"] = False
        return result

    result["checks"]["shape"] = True

    # -----------------------------
    # Convert to grayscale
    # -----------------------------
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
    except Exception:
        result["message"] = "Unable to process image."
        return result

    # -----------------------------
    # Brightness
    # -----------------------------
    brightness = float(np.mean(gray))

    result["checks"]["brightness"] = round(brightness, 2)

    if brightness < 20:
        result["message"] = (
            "Image is too dark. Please upload a brighter document."
        )
        result["checks"]["brightness_ok"] = False
        return result

    if brightness > 245:
        result["message"] = (
            "Image is overexposed. Please upload a clearer document."
        )
        result["checks"]["brightness_ok"] = False
        return result

    result["checks"]["brightness_ok"] = True

    # -----------------------------
    # Edge detection
    # -----------------------------
    try:
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        edge_ratio = float(np.mean(edges > 0))
    except Exception:
        edge_ratio = 0.0

    result["checks"]["edge_ratio"] = round(edge_ratio, 4)

    if edge_ratio < 0.001:
        result["message"] = (
            "Very few document/text edges detected."
        )
        result["checks"]["content_detected"] = False
        return result

    result["checks"]["content_detected"] = True

    # -----------------------------
    # Sharpness
    # -----------------------------
    try:
        sharpness = float(
            cv2.Laplacian(gray, cv2.CV_64F).var()
        )
    except Exception:
        sharpness = 0.0

    result["checks"]["sharpness"] = round(sharpness, 2)

    if sharpness < 15:
        result["checks"]["sharpness_ok"] = False
    else:
        result["checks"]["sharpness_ok"] = True

    # -----------------------------
    # Generic document type
    # -----------------------------
    result["document_type"] = "Identity Document"

    # -----------------------------
    # Confidence
    # -----------------------------
    confidence = 0.0

    if result["checks"].get("resolution"):
        confidence += 0.25

    if result["checks"].get("shape"):
        confidence += 0.20

    if result["checks"].get("brightness_ok"):
        confidence += 0.20

    if result["checks"].get("content_detected"):
        confidence += 0.20

    if result["checks"].get("sharpness_ok"):
        confidence += 0.15

    result["confidence"] = round(confidence, 2)

    # -----------------------------
    # Accept
    # -----------------------------
    result["accepted"] = True

    if not result["checks"].get("sharpness_ok"):
        result["message"] = (
            "Image accepted, but it may be blurry. "
            "OCR accuracy may be reduced."
        )
    else:
        result["message"] = (
            "Document image accepted for further screening."
        )

    return result