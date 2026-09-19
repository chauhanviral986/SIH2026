import re
from datetime import datetime


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_mrz_line(line):

    line = str(line or "").upper().strip()

    replacements = {
        " ": "",
        "\t": "",
        "«": "<",
        "‹": "<",
        "—": "<",
        "–": "<",
        "_": "<",
        "«": "<",
    }

    for old, new in replacements.items():
        line = line.replace(old, new)

    # Keep only valid MRZ characters.
    line = re.sub(
        r"[^A-Z0-9<]",
        "",
        line,
    )

    return line


def repair_digit(value):

    replacements = {
        "O": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "L": "1",
        "Z": "2",
        "S": "5",
        "G": "6",
        "B": "8",
    }

    result = ""

    for char in str(value or ""):
        result += replacements.get(
            char,
            char,
        )

    return result


def repair_second_line(line):

    line = normalize_mrz_line(line)

    # TD3 passport MRZ is normally 44 chars.
    if len(line) > 44:
        line = line[:44]

    return line


# ============================================================
# CHECK DIGIT
# ============================================================

def mrz_check_digit(value):

    weights = [7, 3, 1]
    total = 0

    for index, char in enumerate(
        str(value or "")
    ):

        if char.isdigit():
            number = int(char)

        elif char == "<":
            number = 0

        elif "A" <= char <= "Z":
            number = ord(char) - ord("A") + 10

        else:
            number = 0

        total += number * weights[index % 3]

    return str(total % 10)


# ============================================================
# DATE
# ============================================================

def mrz_date_to_normal(value):

    value = repair_digit(value)

    if not re.fullmatch(
        r"\d{6}",
        value or "",
    ):
        return ""

    try:

        yy = int(value[0:2])
        mm = int(value[2:4])
        dd = int(value[4:6])

        # Standard practical MRZ century rule.
        year = (
            1900 + yy
            if yy >= 50
            else 2000 + yy
        )

        date_value = datetime(
            year,
            mm,
            dd,
        )

        return date_value.strftime(
            "%d/%m/%Y"
        )

    except ValueError:
        return ""


# ============================================================
# SCORING
# ============================================================

def _score_first_line(line):

    score = 0

    if len(line) >= 40:
        score += 2

    if line.startswith("P<"):
        score += 5

    elif line.startswith("P"):
        score += 2

    if "<<" in line:
        score += 2

    if "<" in line:
        score += 1

    letters = sum(
        char.isalpha()
        for char in line
    )

    if letters >= 3:
        score += 1

    return score


def _score_second_line(line):

    score = 0

    if len(line) >= 40:
        score += 2

    if len(line) >= 30:
        score += 1

    digits = sum(
        char.isdigit()
        for char in line
    )

    if digits >= 8:
        score += 3

    if "<" in line:
        score += 1

    return score


# ============================================================
# FIND MRZ LINES
# ============================================================

def _find_first_line(lines):

    candidates = []

    for index, line in enumerate(lines):

        normalized = normalize_mrz_line(
            line
        )

        if len(normalized) < 30:
            continue

        score = _score_first_line(
            normalized
        )

        candidates.append(
            (
                score,
                index,
                normalized,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            x[2].startswith("P<"),
            len(x[2]),
        ),
        reverse=True,
    )

    return candidates[0]


def _find_second_line(
    lines,
    first_index,
):

    candidates = []

    for index, line in enumerate(lines):

        if index <= first_index:
            continue

        normalized = normalize_mrz_line(
            line
        )

        if len(normalized) < 30:
            continue

        score = _score_second_line(
            normalized
        )

        candidates.append(
            (
                score,
                index,
                normalized,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            x[0],
            len(x[2]),
        ),
        reverse=True,
    )

    return candidates[0]


# ============================================================
# NAME
# ============================================================

def _parse_name(raw_name):

    raw_name = str(
        raw_name or ""
    )

    parts = raw_name.split(
        "<<"
    )

    surname = parts[0]

    given = ""

    if len(parts) > 1:
        given = parts[1]

    surname = surname.replace(
        "<",
        " ",
    )

    given = given.replace(
        "<",
        " ",
    )

    surname = re.sub(
        r"\s+",
        " ",
        surname,
    ).strip()

    given = re.sub(
        r"\s+",
        " ",
        given,
    ).strip()

    full_name = " ".join(
        x
        for x in [
            given,
            surname,
        ]
        if x
    )

    return {
        "surname": surname,
        "given_names": given,
        "full_name": full_name,
    }


# ============================================================
# SECOND LINE
# ============================================================

def _parse_second_line(line):

    line = repair_second_line(
        line
    )

    if len(line) < 30:
        return {}

    # Pad to 44 characters so slicing is safe.
    line = line.ljust(
        44,
        "<",
    )

    document_number_raw = line[0:9]

    document_number = (
        document_number_raw
        .replace("<", "")
        .strip()
    )

    document_number_check = line[9]

    nationality = (
        line[10:13]
        .replace("<", "")
    )

    dob_raw = repair_digit(
        line[13:19]
    )

    dob_check = line[19]

    sex = line[20]

    expiry_raw = repair_digit(
        line[21:27]
    )

    expiry_check = line[27]

    optional_data = line[28:42]

    final_check = line[43]

    checks = {
        "document_number": (
            bool(document_number)
            and document_number_check.isdigit()
            and mrz_check_digit(
                document_number_raw
            )
            == document_number_check
        ),

        "date_of_birth": (
            len(dob_raw) == 6
            and dob_raw.isdigit()
            and dob_check.isdigit()
            and mrz_check_digit(
                dob_raw
            )
            == dob_check
        ),

        "expiry_date": (
            len(expiry_raw) == 6
            and expiry_raw.isdigit()
            and expiry_check.isdigit()
            and mrz_check_digit(
                expiry_raw
            )
            == expiry_check
        ),
    }

    return {
        "document_number": document_number,
        "nationality": nationality,
        "date_of_birth_mrz": dob_raw,
        "date_of_birth": mrz_date_to_normal(
            dob_raw
        ),
        "sex": (
            sex
            if sex in (
                "M",
                "F",
                "X",
                "<",
            )
            else ""
        ),
        "date_of_expiry_mrz": expiry_raw,
        "date_of_expiry": mrz_date_to_normal(
            expiry_raw
        ),
        "optional_data": optional_data,
        "checks": checks,
        "raw_line": line,
        "final_check": final_check,
    }


# ============================================================
# TEXT TO LINES
# ============================================================

def _extract_lines(text):

    if not text:
        return []

    lines = []

    for line in str(text).splitlines():

        normalized = normalize_mrz_line(
            line
        )

        if normalized:
            lines.append(
                normalized
            )

    return lines


# ============================================================
# MAIN MRZ PARSER
# ============================================================

def parse_mrz(text):

    empty_result = {
        "found": False,
        "status": "NOT_FOUND",
        "lines": [],
        "fields": {},
        "checks": {},
        "message": (
            "Passport MRZ not detected."
        ),
    }

    lines = _extract_lines(
        text
    )

    if not lines:
        return empty_result

    first = _find_first_line(
        lines
    )

    if first is None:
        return empty_result

    first_score, first_index, first_line = first

    second = _find_second_line(
        lines,
        first_index,
    )

    if second is None:

        return {
            "found": False,
            "status": "PARTIAL",
            "lines": [
                first_line
            ],
            "fields": {},
            "checks": {},
            "message": (
                "Possible MRZ first line detected, "
                "but second line is missing."
            ),
        }

    second_score, second_index, second_line = second

    if (
        first_score < 3
        or second_score < 3
    ):

        return {
            "found": False,
            "status": "PARTIAL",
            "lines": [
                first_line,
                second_line,
            ],
            "fields": {},
            "checks": {},
            "message": (
                "Possible MRZ detected, "
                "but confidence is low."
            ),
        }

    # --------------------------------------------------------
    # First line
    # --------------------------------------------------------

    document_code = first_line[
        0:2
    ]

    name_part = (
        first_line[5:]
        if len(first_line) > 5
        else ""
    )

    name_data = _parse_name(
        name_part
    )

    # --------------------------------------------------------
    # Second line
    # --------------------------------------------------------

    second_data = _parse_second_line(
        second_line
    )

    fields = {
        "document_code": document_code,

        "surname": name_data.get(
            "surname",
            "",
        ),

        "given_names": name_data.get(
            "given_names",
            "",
        ),

        "full_name": name_data.get(
            "full_name",
            "",
        ),

        "document_number": second_data.get(
            "document_number",
            "",
        ),

        "nationality": second_data.get(
            "nationality",
            "",
        ),

        "date_of_birth_mrz": second_data.get(
            "date_of_birth_mrz",
            "",
        ),

        "date_of_birth": second_data.get(
            "date_of_birth",
            "",
        ),

        "sex": second_data.get(
            "sex",
            "",
        ),

        "date_of_expiry_mrz": second_data.get(
            "date_of_expiry_mrz",
            "",
        ),

        "date_of_expiry": second_data.get(
            "date_of_expiry",
            "",
        ),
    }

    checks = second_data.get(
        "checks",
        {},
    )

    valid_checks = sum(
        1
        for value in checks.values()
        if value is True
    )

    if valid_checks >= 2:

        status = "PASS"

        message = (
            "Passport MRZ detected and "
            "multiple check digits are valid."
        )

    elif valid_checks == 1:

        status = "WARN"

        message = (
            "Passport MRZ detected with "
            "partial check-digit validation."
        )

    else:

        status = "WARN"

        message = (
            "Passport MRZ detected, but "
            "check-digit validation could not "
            "be confirmed."
        )

    return {
        "found": True,
        "status": status,
        "lines": [
            first_line,
            second_line,
        ],
        "fields": fields,
        "checks": checks,
        "message": message,
    }


# ============================================================
# COMPATIBILITY
# ============================================================

detect_mrz = parse_mrz
validate_mrz = parse_mrz
