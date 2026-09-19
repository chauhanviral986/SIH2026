# AI-Based Fake Identity & Document Screening System

Hackathon MVP for problem statement 26188. This is a local screening aid, not an official government verification system and not a definitive forgery detector.

## Technology
Python, Streamlit, EasyOCR, OpenCV, Pillow, NumPy, SQLite, Regex, MRZ-style check digits, image-forensics heuristics, SHA-256.

## Windows setup

Open PowerShell in this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt instead:

```cmd
.venv\Scripts\activate.bat
```

Generate safe synthetic test images:

```powershell
python make_samples.py
```

Run:

```powershell
streamlit run app.py
```

The first EasyOCR run downloads its model. Internet is required for that first model download.

## Demo tests

Use these files from `samples/`:
- clean_synthetic_test.png
- tampered_synthetic_test.png
- blurry_synthetic_test.png
- unsupported_visiting_card.png
- unsupported_random_photo.png

## Architecture

Upload -> Image Quality -> Visual Document Gate -> OCR -> Field Extraction/MRZ -> Validation -> Tampering Indicators -> Face Detection -> Explainable Risk -> SQLite + SHA-256 Audit

## Limitations

- The document gate is a lightweight visual pre-gate, not a trained document classifier.
- OCR can make mistakes; OCR/MRZ mismatches require human review.
- Image-forensics heuristics can produce false positives.
- Face detection is not identity verification.
- No restricted government database is accessed.
- No public blockchain is used; SHA-256 provides a simple audit-integrity mechanism.
- The MVP should never be used as the sole basis for a real-world identity or border decision.

## Security
Do not upload real passports or other sensitive identity documents to development/testing systems. Use synthetic or properly licensed examples.
