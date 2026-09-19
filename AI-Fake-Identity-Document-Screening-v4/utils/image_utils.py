# utils/image_utils.py

import hashlib
import io

import cv2
import numpy as np

from PIL import Image, ImageOps

from config import MAX_IMAGE_DIM


def load_image(raw_bytes):
    """
    Convert uploaded image bytes into OpenCV BGR image.
    """

    if not raw_bytes:
        raise ValueError(
            "Empty image data."
        )

    image = Image.open(
        io.BytesIO(raw_bytes)
    )

    image = ImageOps.exif_transpose(
        image
    )

    image = image.convert("RGB")

    # Resize very large images.
    width, height = image.size

    max_dimension = max(
        width,
        height,
    )

    if max_dimension > MAX_IMAGE_DIM:
        scale = (
            MAX_IMAGE_DIM
            / max_dimension
        )

        new_size = (
            int(width * scale),
            int(height * scale),
        )

        image = image.resize(
            new_size,
            Image.LANCZOS,
        )

    rgb = np.array(image)

    bgr = cv2.cvtColor(
        rgb,
        cv2.COLOR_RGB2BGR,
    )

    return bgr


def image_quality_report(image):
    if image is None:
        return {
            "width": 0,
            "height": 0,
            "brightness": 0,
            "sharpness": 0,
            "accepted": False,
            "reasons": [
                "No image supplied."
            ],
        }

    height, width = image.shape[:2]

    if len(image.shape) == 3:
        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )
    else:
        gray = image

    brightness = float(
        np.mean(gray)
    )

    sharpness = float(
        cv2.Laplacian(
            gray,
            cv2.CV_64F,
        ).var()
    )

    reasons = []
    accepted = True

    if width < 400 or height < 250:
        accepted = False
        reasons.append(
            "Resolution is too low."
        )

    if brightness < 20:
        accepted = False
        reasons.append(
            "Image is too dark."
        )

    if brightness > 245:
        accepted = False
        reasons.append(
            "Image is overexposed."
        )

    if sharpness < 15:
        reasons.append(
            "Image may be blurry."
        )

    return {
        "width": width,
        "height": height,
        "brightness": round(
            brightness,
            2,
        ),
        "sharpness": round(
            sharpness,
            2,
        ),
        "accepted": accepted,
        "reasons": reasons,
    }


def sha256_bytes(raw_bytes):
    return hashlib.sha256(
        raw_bytes
    ).hexdigest()