import easyocr
import numpy as np


class OCRService:

    def __init__(self, languages=None):
        if languages is None:
            languages = ["en"]

        self.languages = languages

        self.reader = easyocr.Reader(
            languages,
            gpu=False,
        )

    def read(self, image):

        if image is None:
            return {
                "text": "",
                "items": [],
                "mean_confidence": 0.0,
            }

        try:
            results = self.reader.readtext(
                image,
                detail=1,
                paragraph=False,
            )
        except Exception as exc:
            return {
                "text": "",
                "items": [],
                "mean_confidence": 0.0,
                "error": str(exc),
            }

        items = []
        texts = []
        confidences = []

        for result in results:

            if len(result) < 3:
                continue

            bbox, text, confidence = result

            text = str(text).strip()

            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            if not text:
                continue

            texts.append(text)
            confidences.append(confidence)

            items.append(
                {
                    "text": text,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                    "bbox": bbox,
                }
            )

        mean_confidence = (
            float(np.mean(confidences))
            if confidences
            else 0.0
        )

        return {
            "text": "\n".join(texts),
            "items": items,
            "mean_confidence": round(
                mean_confidence,
                4,
            ),
        }
