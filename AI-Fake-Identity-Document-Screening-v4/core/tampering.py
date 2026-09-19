# core/tampering.py

import cv2
import numpy as np


def analyze_tampering(image):
    """
    Basic image-forensics heuristics.

    These indicators do NOT prove document fraud.
    They only identify image characteristics that may
    deserve additional manual review.
    """

    result = {
        "score": 0.0,
        "status": "PASS",
        "indicators": [],
        "message": "",
    }

    if image is None:
        result["score"] = 10.0
        result["status"] = "WARN"
        result["indicators"].append(
            "No image available for image-forensics analysis."
        )
        result["message"] = (
            "Tampering analysis could not be performed."
        )
        return result

    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY,
            )
        else:
            gray = image.copy()

        # ---------------------------------
        # Blur / sharpness
        # ---------------------------------
        sharpness = float(
            cv2.Laplacian(
                gray,
                cv2.CV_64F,
            ).var()
        )

        # Extremely low sharpness
        if sharpness < 20:
            result["score"] += 5
            result["indicators"].append(
                "Image is unusually blurry."
            )

        # ---------------------------------
        # Noise
        # ---------------------------------
        noise = float(
            np.std(
                gray.astype(np.float32)
                - cv2.GaussianBlur(
                    gray,
                    (3, 3),
                    0,
                ).astype(np.float32)
            )
        )

        if noise > 35:
            result["score"] += 5
            result["indicators"].append(
                "Image contains relatively high local noise."
            )

        # ---------------------------------
        # Edge density
        # ---------------------------------
        edges = cv2.Canny(
            gray,
            50,
            150,
        )

        edge_density = float(
            np.mean(edges > 0)
        )

        if edge_density > 0.35:
            result["score"] += 4
            result["indicators"].append(
                "Image has unusually high edge density."
            )

        # ---------------------------------
        # Status
        # ---------------------------------
        if result["score"] >= 10:
            result["status"] = "WARN"
        else:
            result["status"] = "PASS"

        if result["indicators"]:
            result["message"] = (
                "Some image characteristics require review."
            )
        else:
            result["message"] = (
                "No strong image-forensics indicators detected."
            )

        result["score"] = min(
            20.0,
            result["score"],
        )

        return result

    except Exception as exc:
        return {
            "score": 5.0,
            "status": "WARN",
            "indicators": [
                f"Tampering analysis error: {exc}"
            ],
            "message": (
                "Image-forensics analysis encountered an error."
            ),
        }
