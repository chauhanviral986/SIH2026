from datetime import datetime


# ============================================================
# DATE PARSER
# ============================================================

def _parse_date(value):

    if not value:
        return None

    value = str(
        value
    ).strip()

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d.%m.%y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in formats:

        try:

            return datetime.strptime(
                value,
                fmt,
            )

        except ValueError:
            pass

    return None


# ============================================================
# VALIDATION
# ============================================================

def validate_document(
    fields,
    mrz_result=None,
):

    if not isinstance(
        fields,
        dict,
    ):
        fields = {}

    issues = []
    checks = {}

    document_type = fields.get(
        "document_type",
        "Identity Document",
    )

    name = str(
        fields.get(
            "name",
            "",
        )
        or ""
    ).strip()

    document_number = str(
        fields.get(
            "document_number",
            "",
        )
        or ""
    ).strip()

    # --------------------------------------------------------
    # Name
    # --------------------------------------------------------

    if name:

        checks[
            "name_present"
        ] = True

    else:

        checks[
            "name_present"
        ] = False

        issues.append(
            "Name could not be detected."
        )

    # --------------------------------------------------------
    # Document number
    # --------------------------------------------------------

    if document_number:

        checks[
            "document_number_present"
        ] = True

    else:

        checks[
            "document_number_present"
        ] = False

        issues.append(
            "Document number could not be detected."
        )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    issue_date = _parse_date(
        fields.get(
            "date_of_issue"
        )
    )

    expiry_date = _parse_date(
        fields.get(
            "date_of_expiry"
        )
    )

    dob_date = _parse_date(
        fields.get(
            "date_of_birth"
        )
    )

    today = datetime.now()

    # Issue.
    if issue_date:

        checks[
            "issue_date_valid"
        ] = True

        if issue_date > today:

            issues.append(
                "Issue date is in the future."
            )

    elif fields.get(
        "date_of_issue"
    ):

        checks[
            "issue_date_valid"
        ] = False

        issues.append(
            "Issue date was detected but could not be parsed."
        )

    # Expiry.
    if expiry_date:

        checks[
            "expiry_date_valid"
        ] = True

        if expiry_date < today:

            issues.append(
                "Document appears to be expired."
            )

    elif fields.get(
        "date_of_expiry"
    ):

        checks[
            "expiry_date_valid"
        ] = False

        issues.append(
            "Expiry date was detected but could not be parsed."
        )

    # Date order.
    if (
        issue_date
        and expiry_date
    ):

        if expiry_date < issue_date:

            checks[
                "date_order"
            ] = False

            issues.append(
                "Expiry date is earlier than issue date."
            )

        else:

            checks[
                "date_order"
            ] = True

    # DOB.
    if fields.get(
        "date_of_birth"
    ):

        if dob_date:

            checks[
                "dob_valid"
            ] = True

        else:

            # Aadhaar may provide only YYYY.
            value = str(
                fields.get(
                    "date_of_birth",
                    "",
                )
            )

            if len(value) == 4 and value.isdigit():

                checks[
                    "dob_valid"
                ] = True

            else:

                checks[
                    "dob_valid"
                ] = False

                issues.append(
                    "Date of birth format could not be validated."
                )

    # --------------------------------------------------------
    # MRZ
    # --------------------------------------------------------

    if document_type == "Passport":

        if isinstance(
            mrz_result,
            dict,
        ):

            if mrz_result.get(
                "found"
            ):

                checks[
                    "mrz_found"
                ] = True

                mrz_checks = mrz_result.get(
                    "checks",
                    {},
                )

                checks[
                    "mrz_checks"
                ] = mrz_checks

                valid_count = sum(
                    1
                    for value
                    in mrz_checks.values()
                    if value is True
                )

                checks[
                    "mrz_valid_check_count"
                ] = valid_count

                if valid_count == 0:

                    issues.append(
                        "Passport MRZ detected but check digits could not be confirmed."
                    )

            else:

                checks[
                    "mrz_found"
                ] = False

                issues.append(
                    "Passport MRZ was not fully detected."
                )

        else:

            checks[
                "mrz_found"
            ] = False

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = (
        "WARN"
        if issues
        else "PASS"
    )

    return {
        "status": status,
        "issues": issues,
        "checks": checks,
    }
