# core/risk_engine.py

from config import RISK_THRESHOLDS


def _has_value(value):
    if value is None:
        return False
    value = str(value).strip()
    return bool(value) and value.lower() != "not detected"


def calculate_risk(
    fields,
    validation,
    face_result,
    mrz_result,
    tampering_result,
):
    score = 0.0
    reasons = []

    document_type = fields.get("document_type", "Identity Document")

    # ---------------------------------
    # Missing fields
    # ---------------------------------
    if not _has_value(fields.get("name")):
        score += 10
        reasons.append("Name was not detected.")

    if not _has_value(fields.get("document_number")):
        score += 15
        reasons.append("Document number was not detected.")

    # ---------------------------------
    # Date of birth (all document types)
    # ---------------------------------
    dob = fields.get("date_of_birth") or fields.get("date_of_birth_mrz")
    if not _has_value(dob):
        score += 8
        reasons.append("Date of birth was not detected.")

    # ---------------------------------
    # Validation
    # ---------------------------------
    for issue in validation.get("issues", []):
        score += 8
        reasons.append(issue)

    # ---------------------------------
    # Face
    # ---------------------------------
    face_count = face_result.get("count", face_result.get("face_count", 0))

    if face_count == 0:
        score += 8
        reasons.append("No face detected in the document image.")
    elif face_count > 1:
        score += 10
        reasons.append("Multiple faces detected.")

    # ---------------------------------
    # MRZ (passport only)
    # ---------------------------------
    if document_type == "Passport" and not mrz_result.get("found"):
        score += 10
        reasons.append("Passport MRZ was not fully detected.")

    # ---------------------------------
    # Tampering
    # ---------------------------------
    tampering_score = float(tampering_result.get("score", 0))
    score += tampering_score

    for reason in tampering_result.get("indicators", []):
        reasons.append(reason)

    # ---------------------------------
    # Clamp
    # ---------------------------------
    score = min(100.0, max(0.0, score))

    # ---------------------------------
    # Risk level
    # ---------------------------------
    if score <= RISK_THRESHOLDS["LOW_MAX"]:
        level = "LOW"
    elif score <= RISK_THRESHOLDS["MEDIUM_MAX"]:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "score": round(score, 2),
        "risk_score": round(score, 2),
        "level": level,
        "risk_level": level,
        "reasons": reasons,
    }
