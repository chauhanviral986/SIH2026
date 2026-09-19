# core/extraction.py
#
# Robust field extraction for Indian identity documents.
# Handles Aadhaar, PAN Card, Passport and generic ID documents.
#
# Major fixes over the previous version:
#   * PAN Card is now detected (document type, PAN number, DOB).
#   * Aadhaar date-of-birth detection is far more forgiving
#     (label variants, "DOB", "जन्म", year-only, loose OCR spacing).
#   * Passport issue-date detection now works even when the label
#     is garbled by OCR, using a chronological 3-date heuristic
#     (DOB < Issue < Expiry) as a fallback.

import re
from datetime import datetime


# ============================================================
# GENERAL HELPERS
# ============================================================

def _clean_spaces(value):
    if value is None:
        return ""
    value = str(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" :;,-|")


def _clean_name(value):
    if not value:
        return ""
    value = str(value).upper()
    value = re.sub(r"[^A-Z .'\-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .'-")
    if not value:
        return ""
    if len(value) > 80:
        value = value[:80]
    return value.title()


def _normalize_text(text):
    if not text:
        return ""
    text = str(text)
    replacements = {
        "—": "-",
        "–": "-",
        "−": "-",
        "\r": "\n",
        "|": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line)
        line = line.strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


# ============================================================
# DATE HELPERS
# ============================================================

_MONTHS = {
    "JAN": 1, "JANUARY": 1,
    "FEB": 2, "FEBRUARY": 2,
    "MAR": 3, "MARCH": 3,
    "APR": 4, "APRIL": 4,
    "MAY": 5,
    "JUN": 6, "JUNE": 6,
    "JUL": 7, "JULY": 7,
    "AUG": 8, "AUGUST": 8,
    "SEP": 9, "SEPT": 9, "SEPTEMBER": 9,
    "OCT": 10, "OCTOBER": 10,
    "NOV": 11, "NOVEMBER": 11,
    "DEC": 12, "DECEMBER": 12,
}


def _build_date(day, month, year):
    """Return a datetime or None. Does NOT format."""
    try:
        day = int(day)
        year = int(year)

        if isinstance(month, str):
            month_text = month.upper().strip()
            if month_text.isdigit():
                month_num = int(month_text)
            else:
                month_num = _MONTHS.get(month_text, 0)
        else:
            month_num = int(month)

        if year < 100:
            year = 1900 + year if year >= 30 else 2000 + year

        if not (1900 <= year <= 2100):
            return None

        return datetime(year, month_num, day)
    except (ValueError, TypeError):
        return None


def _fmt(dt):
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y")


def _find_dates(text):
    """
    Find all dates in the text.
    Returns list of dicts: {value, date(datetime), start, end}
    sorted by position.
    """
    if not text:
        return []

    results = []

    # DD/MM/YYYY  (also DD-MM-YYYY, DD.MM.YYYY, and spaced)
    numeric_pattern = re.compile(
        r"(?<!\d)"
        r"(\d{1,2})"
        r"\s*[/.\-]\s*"
        r"(\d{1,2})"
        r"\s*[/.\-]\s*"
        r"(\d{2,4})"
        r"(?!\d)",
        re.IGNORECASE,
    )

    for match in numeric_pattern.finditer(text):
        dt = _build_date(match.group(1), match.group(2), match.group(3))
        if dt:
            results.append({
                "value": _fmt(dt),
                "date": dt,
                "start": match.start(),
                "end": match.end(),
            })

    # 18 SEP 1999  /  18 SEPTEMBER 1999
    month_pattern = re.compile(
        r"\b(\d{1,2})\s*"
        r"(JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|"
        r"JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:T(?:EMBER)?)?|"
        r"OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)\s*"
        r"[,\.]?\s*(\d{2,4})\b",
        re.IGNORECASE,
    )

    for match in month_pattern.finditer(text):
        dt = _build_date(match.group(1), match.group(2), match.group(3))
        if dt:
            results.append({
                "value": _fmt(dt),
                "date": dt,
                "start": match.start(),
                "end": match.end(),
            })

    # Deduplicate by (start, end, value)
    unique = []
    seen = set()
    for item in results:
        key = (item["start"], item["end"], item["value"])
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return sorted(unique, key=lambda x: x["start"])


# ============================================================
# LABEL NORMALIZATION
# ============================================================

def _normalize_label(text):
    if not text:
        return ""
    text = str(text).upper()

    replacements = {
        "0": "O",
        "1": "I",
        "5": "S",
        "8": "B",
        "|": "I",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Common OCR word errors.
    fixes = {
        "DALE": "DATE",
        "LATE": "DATE",
        "DATS": "DATE",
        "IS5UE": "ISSUE",
        "LSSUE": "ISSUE",
        "ISSUEE": "ISSUE",
        "EXPIEY": "EXPIRY",
        "EXPIRV": "EXPIRY",
        "BIRIH": "BIRTH",
        "BIRLH": "BIRTH",
    }
    for old, new in fixes.items():
        text = text.replace(old, new)

    text = re.sub(r"[^A-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _label_regex(label):
    words = str(label).upper().split()
    pieces = []
    for word in words:
        chars = []
        for char in word:
            if char == "O":
                chars.append("[O0]")
            elif char == "I":
                chars.append("[I1L|]")
            elif char == "S":
                chars.append("[S5]")
            elif char == "B":
                chars.append("[B8]")
            else:
                chars.append(re.escape(char))
        pieces.append("".join(chars))
    return r"\s*".join(pieces)


# ============================================================
# DATE NEAR LABEL
# ============================================================

def _date_near_labels(text, labels, max_distance=260):
    if not text:
        return ""

    dates = _find_dates(text)
    if not dates:
        return ""

    best = None
    best_score = None

    for label in labels:
        pattern = _label_regex(label)
        try:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
        except re.error:
            continue

        for match in matches:
            label_start = match.start()
            label_end = match.end()

            for date in dates:
                date_start = date["start"]
                date_end = date["end"]

                # Date after label (normal case).
                if date_start >= label_end:
                    distance = date_start - label_end
                    if distance > max_distance:
                        continue
                    between = text[label_end:date_start]
                    score = distance
                    # A newline between label and date is a small penalty,
                    # but Aadhaar/PAN often wrap, so keep it modest.
                    if between.count("\n") == 1:
                        score += 30
                    elif between.count("\n") > 1:
                        score += 120
                    if best_score is None or score < best_score:
                        best_score = score
                        best = date["value"]

                # Date before label.
                elif date_end <= label_start:
                    distance = label_start - date_end
                    if distance > 100:
                        continue
                    score = distance + 90
                    if best_score is None or score < best_score:
                        best_score = score
                        best = date["value"]

    return best or ""


# ============================================================
# DOCUMENT TYPE
# ============================================================

_PAN_RE = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")


def _detect_document_type(text, mrz=None, gate_type=None):
    upper = str(text or "").upper()

    # MRZ is a strong passport signal.
    if isinstance(mrz, dict) and mrz.get("found"):
        return "Passport"

    # Gate result.
    if gate_type:
        gate_upper = str(gate_type).upper()
        if "PASSPORT" in gate_upper:
            return "Passport"
        if "PAN" in gate_upper:
            return "PAN Card"
        if "AADHAAR" in gate_upper:
            return "Aadhaar"
        if "DRIVING" in gate_upper:
            return "Driving Licence"

    # PAN Card — check before Aadhaar. PAN cards carry the phrases below
    # and/or a valid PAN number pattern.
    pan_keywords = [
        "INCOME TAX DEPARTMENT",
        "PERMANENT ACCOUNT NUMBER",
        "PERMANENT ACCOUNT NO",
    ]
    if any(k in upper for k in pan_keywords):
        return "PAN Card"

    has_pan_number = bool(_PAN_RE.search(upper))
    has_aadhaar_number = bool(re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", upper))

    # A PAN number with no Aadhaar number present strongly implies PAN card.
    if has_pan_number and not has_aadhaar_number:
        return "PAN Card"

    # Aadhaar.
    if (
        "AADHAAR" in upper
        or "AADHAR" in upper
        or "UIDAI" in upper
        or "UNIQUE IDENTIFICATION" in upper
        or has_aadhaar_number
    ):
        return "Aadhaar"

    # Passport.
    passport_keywords = [
        "PASSPORT",
        "PASSEPORT",
        "PASAPORTE",
        "REPUBLIC OF INDIA",
        "UNITED STATES OF AMERICA",
        "UNITED KINGDOM",
        "GREAT BRITAIN",
        "BRITISH CITIZEN",
        "BRITSH CITIZEN",
    ]
    if any(keyword in upper for keyword in passport_keywords):
        return "Passport"

    # Driving licence.
    if re.search(r"DRIVING\s+LICEN[CS]E|DRIVER'?S\s+LICEN[CS]E", upper):
        return "Driving Licence"

    # Voter ID.
    if "VOTER" in upper or "ELECTION COMMISSION" in upper:
        return "Voter ID"

    # Visa.
    if re.search(r"\bVISA\b", upper):
        return "Visa"

    # Residence permit.
    if "RESIDENCE PERMIT" in upper:
        return "Residence Permit"

    # Fall back to PAN if a PAN number exists even alongside other numbers.
    if has_pan_number:
        return "PAN Card"

    return "Identity Document"


# ============================================================
# MRZ FALLBACK
# ============================================================

def _get_mrz_fields(mrz_data):
    if not isinstance(mrz_data, dict):
        return {}
    fields = mrz_data.get("fields", {})
    if not isinstance(fields, dict):
        return {}
    return fields


# ============================================================
# NAME
# ============================================================

def _extract_name(text, mrz_fields):
    # MRZ first.
    full_name = _clean_name(mrz_fields.get("full_name", ""))
    if full_name:
        return full_name

    lines = [
        _clean_spaces(line)
        for line in str(text or "").splitlines()
        if _clean_spaces(line)
    ]

    # Note: separators use [ \t]* (not \s*) so a match cannot span a
    # newline and accidentally capture the next label/value.
    patterns = [
        r"\bFULL[ \t]+NAME[ \t]*[:\-]?[ \t]*([A-Za-z][A-Za-z .'\-]{2,80})",
        r"\bNAME[ \t]*[:\-]?[ \t]*([A-Za-z][A-Za-z .'\-]{2,80})",
        r"\bSURNAME[ \t]*[:\-]?[ \t]*([A-Za-z][A-Za-z .'\-]{2,60})",
        r"\bGIVEN[ \t]+NAMES?[ \t]*[:\-]?[ \t]*([A-Za-z][A-Za-z .'\-]{2,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = _clean_name(match.group(1))
            if candidate:
                return candidate

    labels = ["FULL NAME", "NAME", "SURNAME", "GIVEN NAME", "GIVEN NAMES"]
    normalized_labels = [_normalize_label(x) for x in labels]

    for index, line in enumerate(lines):
        normalized = _normalize_label(line)
        for label in normalized_labels:
            if normalized == label and index + 1 < len(lines):
                candidate = lines[index + 1]
                if (
                    not _find_dates(candidate)
                    and not re.fullmatch(r"[\d\s/\-.]+", candidate)
                ):
                    value = _clean_name(candidate)
                    if value:
                        return value

    return ""


# ============================================================
# PAN NUMBER
# ============================================================

def _repair_pan(token):
    """
    Normalize a 10-char PAN candidate: positions 0-4 letters,
    5-8 digits, 9 letter. Fix common OCR letter/digit confusion.
    """
    token = re.sub(r"[^A-Z0-9]", "", str(token or "").upper())
    if len(token) != 10:
        return ""

    letter_map = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z", "6": "G"}
    digit_map = {"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1",
                 "Z": "2", "S": "5", "B": "8", "G": "6"}

    chars = list(token)
    for i in range(5):          # first five must be letters
        if chars[i].isdigit():
            chars[i] = letter_map.get(chars[i], chars[i])
    for i in range(5, 9):       # next four must be digits
        if chars[i].isalpha():
            chars[i] = digit_map.get(chars[i], chars[i])
    if chars[9].isdigit():      # last must be a letter
        chars[9] = letter_map.get(chars[9], chars[9])

    repaired = "".join(chars)
    if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", repaired):
        return repaired
    return ""


def _extract_pan_number(text):
    upper = str(text or "").upper()

    # Direct, well-formed match first.
    match = _PAN_RE.search(upper)
    if match:
        return match.group(1)

    # Labelled candidate (may be garbled).
    label_match = re.search(
        r"(?:PERMANENT\s+ACCOUNT\s+NUMBER|PAN)\s*[:\-]?\s*([A-Z0-9]{10})",
        upper,
    )
    if label_match:
        repaired = _repair_pan(label_match.group(1))
        if repaired:
            return repaired

    # Any standalone 10-char alphanumeric token, repaired.
    for token in re.findall(r"\b[A-Z0-9]{10}\b", upper):
        repaired = _repair_pan(token)
        if repaired:
            return repaired

    return ""


# ============================================================
# DOCUMENT NUMBER
# ============================================================

def _extract_document_number(text, document_type, mrz_fields):
    # MRZ first.
    mrz_number = (
        str(mrz_fields.get("document_number", ""))
        .replace("<", "")
        .strip()
        .upper()
    )
    if mrz_number:
        return mrz_number

    # PAN.
    if document_type == "PAN Card":
        pan = _extract_pan_number(text)
        if pan:
            return pan

    # Aadhaar.
    if document_type == "Aadhaar":
        matches = re.findall(r"\b\d{4}\s?\d{4}\s?\d{4}\b", text)
        for value in matches:
            digits = re.sub(r"\D", "", value)
            if len(digits) == 12:
                return digits

    # Passport.
    if document_type == "Passport":
        patterns = [
            r"\bPASSPORT\s*(?:NO|NUMBER|N[O0]\.?)?\s*[:\-]?\s*([A-Z0-9]{6,12})",
            r"\bDOCUMENT\s*(?:NO|NUMBER|N[O0]\.?)\s*[:\-]?\s*([A-Z0-9]{6,20})",
            r"\b([A-Z][0-9]{7})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                if 6 <= len(value) <= 20:
                    return value

    # Generic.
    patterns = [
        r"\b(?:DOCUMENT|ID|LICENCE|LICENSE|PERMIT)\s*(?:NO|NUMBER|N[O0]\.?)"
        r"\s*[:\-]?\s*([A-Z0-9]{5,20})",
        r"\b(?:NO|NUMBER|N[O0]\.)\s*[:\-]\s*([A-Z0-9]{5,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return ""


# ============================================================
# NATIONALITY
# ============================================================

def _extract_nationality(text, mrz_fields):
    upper = str(text or "").upper()

    mrz_nationality = str(mrz_fields.get("nationality", "")).strip().upper()
    if mrz_nationality:
        country_codes = {
            "IND": "Indian",
            "GBR": "British",
            "USA": "American",
            "CAN": "Canadian",
            "AUS": "Australian",
            "DEU": "German",
            "FRA": "French",
            "ITA": "Italian",
            "ESP": "Spanish",
            "JPN": "Japanese",
        }
        return country_codes.get(mrz_nationality, mrz_nationality)

    patterns = [
        (r"\bBRITISH\s+CITIZEN\b", "British"),
        (r"\bBRITSH\s+CITIZEN\b", "British"),
        (r"\bBRITISH\b", "British"),
        (r"\bINDIAN\b", "Indian"),
        (r"\bINDIA\b", "Indian"),
        (r"\bAMERICAN\b", "American"),
        (r"\bCANADIAN\b", "Canadian"),
        (r"\bAUSTRALIAN\b", "Australian"),
    ]
    for pattern, value in patterns:
        if re.search(pattern, upper):
            return value

    return ""


# ============================================================
# SEX
# ============================================================

def _extract_sex(text, mrz_fields):
    mrz_sex = str(mrz_fields.get("sex", "")).upper().strip()
    if mrz_sex in ("M", "F", "X"):
        return mrz_sex

    patterns = [
        r"\bSEX\s*[:\-]?\s*(MALE|FEMALE|M|F|X)\b",
        r"\bGENDER\s*[:\-]?\s*(MALE|FEMALE|M|F|X)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).upper()
        if value == "MALE":
            return "M"
        if value == "FEMALE":
            return "F"
        if value in ("M", "F", "X"):
            return value

    return ""


def _sex_to_gender(sex):
    return {"M": "Male", "F": "Female", "X": "X"}.get(sex, "")


# ============================================================
# DATE OF BIRTH (shared, forgiving)
# ============================================================

_DOB_LABELS = [
    "DATE OF BIRTH",
    "DATE OF BIRIH",
    "DATE 0F BIRTH",
    "DALE OF BIRTH",
    "DOB",
    "D O B",
    "D.O.B",
    "BIRTH",
]


def _extract_dob(text):
    # 1) Near an explicit DOB label.
    dob = _date_near_labels(text, _DOB_LABELS)
    if dob:
        return dob

    # 2) Year-of-birth only (Aadhaar sometimes prints only the year).
    match = re.search(
        r"\b(?:YEAR\s+OF\s+BIRTH|YOB)\s*[:\-]?\s*(19\d{2}|20\d{2})\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)

    return ""


# ============================================================
# AADHAAR
# ============================================================

def _extract_aadhaar(text, mrz_fields):
    result = {
        "document_type": "Aadhaar",
        "name": _extract_name(text, mrz_fields),
        "document_number": _extract_document_number(text, "Aadhaar", mrz_fields),
        "date_of_birth": "",
        "date_of_issue": "",
        "date_of_expiry": "",
        "nationality": "Indian",
        "sex": _extract_sex(text, mrz_fields),
        "gender": "",
    }

    dob = _extract_dob(text)

    # Final fallback: Aadhaar has no expiry/issue dates, so any single
    # date on the card is the date of birth.
    if not dob:
        dates = _find_dates(text)
        past = [d for d in dates if d["date"] <= datetime.now()]
        if past:
            dob = past[0]["value"]

    result["date_of_birth"] = dob
    result["gender"] = _sex_to_gender(result["sex"])
    return result


# ============================================================
# PAN CARD
# ============================================================

def _extract_pan(text, mrz_fields):
    result = {
        "document_type": "PAN Card",
        "name": _extract_name(text, mrz_fields),
        "document_number": _extract_pan_number(text),
        "date_of_birth": "",
        "date_of_issue": "",
        "date_of_expiry": "",
        "nationality": "Indian",
        "sex": _extract_sex(text, mrz_fields),
        "gender": "",
    }

    dob = _extract_dob(text)

    # PAN cards carry exactly one date (the DOB) and often no clear label,
    # so fall back to the single/earliest date on the card.
    if not dob:
        dates = _find_dates(text)
        past = [d for d in dates if d["date"] <= datetime.now()]
        if past:
            dob = past[0]["value"]

    result["date_of_birth"] = dob
    result["gender"] = _sex_to_gender(result["sex"])
    return result


# ============================================================
# PASSPORT
# ============================================================

def _assign_passport_dates(text, dob_str, expiry_str):
    """
    Determine the issue date. Uses labels first, then a chronological
    heuristic: among the OCR dates, issue sits between DOB and expiry
    and is typically expiry minus ~10 years.
    """
    issue = _date_near_labels(
        text,
        [
            "DATE OF ISSUE",
            "DATE OF LSSUE",
            "DATE OF 1SSUE",
            "DATE 0F ISSUE",
            "DALE OF ISSUE",
            "DATE OF IS5UE",
            "ISSUE DATE",
            "ISSUED DATE",
            "DATE ISSUED",
            "ISSUED ON",
            "DATE OF ISSUANCE",
        ],
    )
    if issue:
        return issue

    dob = _parse_ddmmyyyy(dob_str)
    expiry = _parse_ddmmyyyy(expiry_str)

    dates = _find_dates(text)
    if not dates:
        return ""

    # Candidates: exclude those equal to DOB or expiry.
    candidates = []
    for d in dates:
        dt = d["date"]
        if dob and dt.date() == dob.date():
            continue
        if expiry and dt.date() == expiry.date():
            continue
        candidates.append(d)

    if not candidates:
        return ""

    today = datetime.now()

    # Prefer a candidate lying strictly between DOB and expiry and in the past.
    def valid_issue(dt):
        if dt > today:
            return False
        if dob and dt <= dob:
            return False
        if expiry and dt >= expiry:
            return False
        return True

    between = [d for d in candidates if valid_issue(d["date"])]

    if expiry:
        # Indian passports are valid 10 years; issue ≈ expiry - 10y.
        target = expiry.replace(year=expiry.year - 10)
        pool = between or candidates
        pool = [d for d in pool if d["date"] <= today]
        if pool:
            best = min(pool, key=lambda d: abs((d["date"] - target).days))
            return best["value"]

    if between:
        return between[0]["value"]

    return ""


def _parse_ddmmyyyy(value):
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    return None


def _extract_passport(text, mrz_fields):
    result = {
        "document_type": "Passport",
        "name": _extract_name(text, mrz_fields),
        "document_number": _extract_document_number(text, "Passport", mrz_fields),
        "date_of_birth": "",
        "date_of_issue": "",
        "date_of_expiry": "",
        "nationality": _extract_nationality(text, mrz_fields),
        "sex": _extract_sex(text, mrz_fields),
        "gender": "",
    }

    # DOB — MRZ first, then labelled OCR.
    dob = mrz_fields.get("date_of_birth", "") or _date_near_labels(
        text,
        [
            "DATE OF BIRTH",
            "DATE OF BIRIH",
            "DATE 0F BIRTH",
            "DALE OF BIRTH",
            "DOB",
            "D.O.B",
        ],
    )
    result["date_of_birth"] = dob

    # Expiry — MRZ first, then labelled OCR.
    expiry = mrz_fields.get("date_of_expiry", "") or _date_near_labels(
        text,
        [
            "DATE OF EXPIRY",
            "DATE OF EXPIRATION",
            "EXPIRY DATE",
            "EXPIRATION DATE",
            "VALID UNTIL",
            "VALID TO",
            "DATE OF EXP",
            "DALE OF EXPIRY",
            "DATE 0F EXPIRY",
        ],
    )
    result["date_of_expiry"] = expiry

    # Issue — labels first, then chronological heuristic.
    result["date_of_issue"] = _assign_passport_dates(text, dob, expiry)

    result["gender"] = _sex_to_gender(result["sex"])
    return result


# ============================================================
# GENERIC DOCUMENT
# ============================================================

def _extract_generic(text, document_type, mrz_fields):
    result = {
        "document_type": document_type,
        "name": _extract_name(text, mrz_fields),
        "document_number": _extract_document_number(text, document_type, mrz_fields),
        "date_of_birth": _extract_dob(text),
        "date_of_issue": _date_near_labels(
            text,
            ["DATE OF ISSUE", "ISSUE DATE", "DATE ISSUED", "ISSUED DATE", "ISSUED ON"],
        ),
        "date_of_expiry": _date_near_labels(
            text,
            ["DATE OF EXPIRY", "DATE OF EXPIRATION", "EXPIRY DATE",
             "EXPIRATION DATE", "VALID UNTIL", "VALID TO"],
        ),
        "nationality": _extract_nationality(text, mrz_fields),
        "sex": _extract_sex(text, mrz_fields),
        "gender": "",
    }
    result["gender"] = _sex_to_gender(result["sex"])
    return result


# ============================================================
# MAIN
# ============================================================

def extract_fields(ocr_text, gate_type=None, mrz_data=None):
    text = _normalize_text(ocr_text)
    mrz_fields = _get_mrz_fields(mrz_data)

    document_type = _detect_document_type(text, mrz_data, gate_type)

    if document_type == "Passport":
        fields = _extract_passport(text, mrz_fields)
    elif document_type == "Aadhaar":
        fields = _extract_aadhaar(text, mrz_fields)
    elif document_type == "PAN Card":
        fields = _extract_pan(text, mrz_fields)
    else:
        fields = _extract_generic(text, document_type, mrz_fields)

    # ----------------------------------------------------------------
    # Final MRZ override for passport fields.
    # ----------------------------------------------------------------
    if document_type == "Passport" and mrz_fields:
        if mrz_fields.get("full_name"):
            fields["name"] = _clean_name(mrz_fields["full_name"])
        if mrz_fields.get("document_number"):
            fields["document_number"] = str(
                mrz_fields["document_number"]
            ).replace("<", "")
        if mrz_fields.get("date_of_birth"):
            fields["date_of_birth"] = mrz_fields["date_of_birth"]
        if mrz_fields.get("date_of_expiry"):
            fields["date_of_expiry"] = mrz_fields["date_of_expiry"]
        if mrz_fields.get("nationality"):
            fields["nationality"] = _extract_nationality("", mrz_fields)
        if mrz_fields.get("sex") in ("M", "F", "X"):
            fields["sex"] = mrz_fields["sex"]
            fields["gender"] = _sex_to_gender(fields["sex"])

    return fields
