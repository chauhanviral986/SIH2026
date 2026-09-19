# core/face.py

import cv2
import numpy as np


def analyze_faces(image):
    """
    Detect faces using OpenCV Haar Cascade.
    This function only detects faces.
    It does not perform biometric identity matching.
    """

    if image is None:
        return {
            "status": "ERROR",
            "count": 0,
            "face_count": 0,
            "boxes": [],
            "message": "No image supplied.",
        }

    try:
        if len(image.shape) == 2:
            gray = image
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.equalizeHist(gray)

        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        if cascade.empty():
            return {
                "status": "ERROR",
                "count": 0,
                "face_count": 0,
                "boxes": [],
                "message": "Face detector could not be loaded.",
            }

        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(40, 40),
        )

        boxes = []

        for x, y, w, h in faces:
            boxes.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h),
                }
            )

        count = len(boxes)

        if count == 1:
            status = "PASS"
            message = "One face detected."
        elif count > 1:
            status = "WARN"
            message = "Multiple faces detected."
        else:
            status = "NOT_FOUND"
            message = "No face detected."

        return {
            "status": status,
            "count": count,
            "face_count": count,
            "boxes": boxes,
            "message": message,
        }

    except Exception as exc:
        return {
            "status": "ERROR",
            "count": 0,
            "face_count": 0,
            "boxes": [],
            "message": f"Face detection error: {exc}",
        }
