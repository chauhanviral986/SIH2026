# app.py

import streamlit as st

from document_gate.document_gate import document_gate

from config import RISK_THRESHOLDS

from utils.image_utils import (
    load_image,
    image_quality_report,
    sha256_bytes,
)

from core.ocr import OCRService
from core.extraction import extract_fields
from core.face import analyze_faces
from core.mrz import parse_mrz
from core.validation import validate_document
from core.risk_engine import calculate_risk
from core.tampering import analyze_tampering

from database.database import (
    init_db,
    save_screening,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Identity Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #64748b;
        font-size: 17px;
        margin-bottom: 25px;
    }

    .info-box {
        padding: 15px;
        border-radius: 10px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
    }

    .risk-box {
        padding: 20px;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        text-align: center;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

init_db()


# ============================================================
# OCR SERVICE
# ============================================================

@st.cache_resource
def get_ocr_service():
    return OCRService(["en"])


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_field(fields, *keys, default="Not detected"):
    """
    Safely get a field using multiple possible key names.
    """

    if not isinstance(fields, dict):
        return default

    for key in keys:
        value = fields.get(key)

        if value is not None:
            value = str(value).strip()

            if value:
                return value

    return default


def normalize_fields(fields, mrz_result=None):
    """
    Normalize extracted fields so the UI can always display
    Name, document number, DOB, dates, nationality and sex.
    """

    if not isinstance(fields, dict):
        fields = {}

    if not isinstance(mrz_result, dict):
        mrz_result = {}

    mrz_fields = mrz_result.get("fields", {})

    if not isinstance(mrz_fields, dict):
        mrz_fields = {}

    # ---------------------------------------------------------
    # NAME
    # ---------------------------------------------------------

    name = get_field(
        fields,
        "name",
        "full_name",
        "fullName",
        "holder_name",
        "person_name",
        "surname",
        "given_name",
        default="",
    )

    if not name:
        name = get_field(
            mrz_fields,
            "name",
            "full_name",
            "fullName",
            "holder_name",
            default="",
        )

    # ---------------------------------------------------------
    # DOCUMENT NUMBER
    # ---------------------------------------------------------

    document_number = get_field(
        fields,
        "document_number",
        "document_no",
        "document_num",
        "passport_number",
        "passport_no",
        "id_number",
        "id_no",
        "number",
        default="",
    )

    if not document_number:
        document_number = get_field(
            mrz_fields,
            "document_number",
            "document_no",
            "passport_number",
            "passport_no",
            "number",
            default="",
        )

    # ---------------------------------------------------------
    # DATE OF BIRTH
    # ---------------------------------------------------------

    date_of_birth = get_field(
        fields,
        "date_of_birth",
        "dob",
        "birth_date",
        "birthdate",
        "date_of_birth_mrz",
        default="",
    )

    if not date_of_birth:
        date_of_birth = get_field(
            mrz_fields,
            "date_of_birth",
            "dob",
            "birth_date",
            default="",
        )

    # ---------------------------------------------------------
    # DATE OF ISSUE
    # ---------------------------------------------------------

    date_of_issue = get_field(
        fields,
        "date_of_issue",
        "issue_date",
        "issued_date",
        "date_issued",
        default="",
    )

    # ---------------------------------------------------------
    # DATE OF EXPIRY
    # ---------------------------------------------------------

    date_of_expiry = get_field(
        fields,
        "date_of_expiry",
        "expiry_date",
        "expiration_date",
        "expires",
        "date_of_expiry_mrz",
        default="",
    )

    if not date_of_expiry:
        date_of_expiry = get_field(
            mrz_fields,
            "date_of_expiry",
            "expiry_date",
            "expiration_date",
            default="",
        )

    # ---------------------------------------------------------
    # NATIONALITY
    # ---------------------------------------------------------

    nationality = get_field(
        fields,
        "nationality",
        "country",
        "citizenship",
        default="",
    )

    if not nationality:
        nationality = get_field(
            mrz_fields,
            "nationality",
            "country",
            "citizenship",
            default="",
        )

    # ---------------------------------------------------------
    # SEX
    # ---------------------------------------------------------

    sex = get_field(
        fields,
        "sex",
        "gender",
        default="",
    )

    if not sex:
        sex = get_field(
            mrz_fields,
            "sex",
            "gender",
            default="",
        )

    # ---------------------------------------------------------
    # DOCUMENT TYPE
    # ---------------------------------------------------------

    document_type = get_field(
        fields,
        "document_type",
        "type",
        "doc_type",
        default="Unknown",
    )

    return {
        "document_type": document_type,
        "name": name or "Not detected",
        "document_number": document_number or "Not detected",
        "date_of_birth": date_of_birth or "Not detected",
        "date_of_issue": date_of_issue or "Not detected",
        "date_of_expiry": date_of_expiry or "Not detected",
        "nationality": nationality or "Not detected",
        "sex": sex or "Not detected",
    }


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🛡️ AI-Based Fake Identity & Document Screening System</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
    AI-assisted identity document screening using OCR,
    MRZ analysis, face detection, validation and image-forensics indicators.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Screening Settings")

    st.write(
        "Upload an identity document and run the screening pipeline."
    )

    st.divider()

    st.info(
        """
        **Pipeline**

        1. Image Quality
        2. Document Gate
        3. OCR
        4. Field Extraction
        5. Face Detection
        6. MRZ Analysis
        7. Image Forensics
        8. Validation
        9. Risk Indicators
        """
    )


# ============================================================
# UPLOAD
# ============================================================

st.subheader("📄 Upload Identity Document")

uploaded_file = st.file_uploader(
    "Upload document image",
    type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
    ],
)

person_photo = st.file_uploader(
    "Optional person photo",
    type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
    ],
)


if uploaded_file is None:

    st.info(
        "Please upload an identity document image to start screening."
    )

    st.stop()


# ============================================================
# READ IMAGE
# ============================================================

raw_bytes = uploaded_file.getvalue()

file_hash = sha256_bytes(
    raw_bytes
)

try:

    image = load_image(
        raw_bytes
    )

except Exception as exc:

    st.error(
        f"Unable to read image: {exc}"
    )

    st.stop()


# ============================================================
# SHOW IMAGE
# ============================================================

left, right = st.columns(
    [1, 1]
)

with left:

    st.subheader("📷 Uploaded Document")

    st.image(
        image,
        caption=uploaded_file.name,
        width='stretch',
    )

with right:

    st.subheader("🔐 File Information")

    st.write(
        f"**File:** {uploaded_file.name}"
    )

    st.write(
        f"**Size:** {len(raw_bytes) / 1024:.2f} KB"
    )

    st.write(
        f"**SHA-256:** `{file_hash[:32]}...`"
    )


# ============================================================
# RUN SCREENING
# ============================================================

if st.button(
    "🔍 Start AI Screening",
    type="primary",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Running document screening..."
        ):

            # ==================================================
            # 1. IMAGE QUALITY
            # ==================================================

            quality = image_quality_report(
                image
            )


            # ==================================================
            # 2. DOCUMENT GATE
            # ==================================================

            gate = document_gate(
                image
            )

            if not isinstance(gate, dict):
                gate = {
                    "accepted": True,
                    "confidence": 0,
                    "message": str(gate),
                    "document_type": "Unknown",
                }


            # ==================================================
            # 3. OCR
            # ==================================================

            ocr_service = get_ocr_service()

            ocr_result = ocr_service.read(
                image
            )

            if not isinstance(ocr_result, dict):
                ocr_result = {
                    "text": str(ocr_result),
                    "mean_confidence": 0,
                }

            ocr_text = ocr_result.get(
                "text",
                "",
            )


            # ==================================================
            # 4. MRZ
            # ==================================================

            mrz_result = parse_mrz(
                ocr_text
            )

            if not isinstance(mrz_result, dict):
                mrz_result = {
                    "status": "NOT_FOUND",
                    "message": str(mrz_result),
                    "lines": [],
                    "fields": {},
                    "checks": {},
                }


            # ==================================================
            # 5. FIELD EXTRACTION
            # ==================================================

            fields = extract_fields(
                ocr_text,
                gate.get(
                    "document_type",
                    "Unknown",
                ),
                mrz_result,
            )

            if not isinstance(fields, dict):
                fields = {}


            # ==================================================
            # NORMALIZE FIELDS
            # ==================================================

            display_fields = normalize_fields(
                fields,
                mrz_result,
            )


            # ==================================================
            # 6. FACE DETECTION
            # ==================================================

            face_result = analyze_faces(
                image
            )

            if not isinstance(face_result, dict):
                face_result = {
                    "count": 0,
                    "status": "UNKNOWN",
                    "message": str(face_result),
                }


            # ==================================================
            # 7. TAMPERING
            # ==================================================

            tampering_result = analyze_tampering(
                image
            )

            if not isinstance(tampering_result, dict):
                tampering_result = {
                    "score": 0,
                    "message": str(tampering_result),
                    "indicators": [],
                }


            # ==================================================
            # 8. VALIDATION
            # ==================================================

            validation = validate_document(
                fields,
                mrz_result,
            )

            if not isinstance(validation, dict):
                validation = {
                    "status": "UNKNOWN",
                    "issues": [
                        str(validation)
                    ],
                }


            # ==================================================
            # 9. RISK
            # ==================================================

            risk = calculate_risk(
                fields,
                validation,
                face_result,
                mrz_result,
                tampering_result,
            )

            if not isinstance(risk, dict):
                risk = {
                    "score": 0,
                    "level": "UNKNOWN",
                    "reasons": [],
                }


            # ==================================================
            # FINAL RESULT
            # ==================================================

            screening_result = {

                "file_name": uploaded_file.name,

                "file_hash": file_hash,

                "quality": quality,

                "gate": gate,

                "ocr": ocr_result,

                "fields": fields,

                "display_fields": display_fields,

                "face": face_result,

                "mrz": mrz_result,

                "tampering": tampering_result,

                "validation": validation,

                "risk": risk,
            }


            st.session_state[
                "screening_result"
            ] = screening_result


            # ==================================================
            # DATABASE
            # ==================================================

            save_screening(
                {
                    "file_name": uploaded_file.name,

                    "file_hash": file_hash,

                    "document_type": display_fields.get(
                        "document_type",
                        "",
                    ),

                    "name": display_fields.get(
                        "name",
                        "",
                    ),

                    "document_number": display_fields.get(
                        "document_number",
                        "",
                    ),

                    "risk_score": risk.get(
                        "score",
                        0,
                    ),

                    "risk_level": risk.get(
                        "level",
                        "",
                    ),

                    "result": screening_result,
                }
            )


        st.success(
            "Screening completed successfully."
        )

    except Exception as exc:

        st.error(
            f"Screening failed: {exc}"
        )

        st.exception(
            exc
        )

        st.stop()


# ============================================================
# DISPLAY RESULT
# ============================================================

if (
    "screening_result"
    not in st.session_state
):

    st.info(
        "Click **Start AI Screening** to analyze the uploaded document."
    )

    st.stop()


# ============================================================
# LOAD RESULTS
# ============================================================

result = st.session_state[
    "screening_result"
]

quality = result.get(
    "quality",
    {},
)

gate = result.get(
    "gate",
    {},
)

ocr_result = result.get(
    "ocr",
    {},
)

fields = result.get(
    "fields",
    {},
)

display_fields = result.get(
    "display_fields",
    normalize_fields(fields),
)

face_result = result.get(
    "face",
    {},
)

mrz_result = result.get(
    "mrz",
    {},
)

tampering_result = result.get(
    "tampering",
    {},
)

validation = result.get(
    "validation",
    {},
)

risk = result.get(
    "risk",
    {},
)


# ============================================================
# TOP SUMMARY
# ============================================================

st.divider()

st.subheader(
    "📊 Screening Summary"
)

col1, col2, col3, col4 = st.columns(
    4
)

with col1:

    st.metric(
        "Document Type",
        display_fields.get(
            "document_type",
            "Unknown",
        ),
    )

with col2:

    st.metric(
        "Face Count",
        face_result.get(
            "count",
            0,
        ),
    )

with col3:

    try:
        score = float(
            risk.get(
                "score",
                0,
            )
        )
    except:
        score = 0

    st.metric(
        "Risk Score",
        f"{score:.0f}/100",
    )

with col4:

    st.metric(
        "Risk Level",
        risk.get(
            "level",
            "UNKNOWN",
        ),
    )


# ============================================================
# IMPORTANT: EXTRACTED IDENTITY INFORMATION
# ============================================================

st.divider()

st.subheader(
    "🪪 Extracted Identity Information"
)

# ------------------------------------------------------------
# ROW 1
# ------------------------------------------------------------

c1, c2, c3 = st.columns(
    3
)

with c1:

    st.markdown(
        "**👤 Full Name**"
    )

    st.info(
        display_fields.get(
            "name",
            "Not detected",
        )
    )

with c2:

    st.markdown(
        "**🪪 Document Number**"
    )

    st.info(
        display_fields.get(
            "document_number",
            "Not detected",
        )
    )

with c3:

    st.markdown(
        "**📄 Document Type**"
    )

    st.info(
        display_fields.get(
            "document_type",
            "Not detected",
        )
    )


# ------------------------------------------------------------
# ROW 2
# ------------------------------------------------------------

c1, c2, c3 = st.columns(
    3
)

with c1:

    st.markdown(
        "**🎂 Date of Birth**"
    )

    st.info(
        display_fields.get(
            "date_of_birth",
            "Not detected",
        )
    )

with c2:

    st.markdown(
        "**📅 Date of Issue**"
    )

    st.info(
        display_fields.get(
            "date_of_issue",
            "Not detected",
        )
    )

with c3:

    st.markdown(
        "**⏳ Date of Expiry**"
    )

    st.info(
        display_fields.get(
            "date_of_expiry",
            "Not detected",
        )
    )


# ------------------------------------------------------------
# ROW 3
# ------------------------------------------------------------

c1, c2 = st.columns(
    2
)

with c1:

    st.markdown(
        "**🌍 Nationality**"
    )

    st.info(
        display_fields.get(
            "nationality",
            "Not detected",
        )
    )

with c2:

    st.markdown(
        "**⚧ Sex / Gender**"
    )

    st.info(
        display_fields.get(
            "sex",
            "Not detected",
        )
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "📋 Extracted Fields",
        "🔤 OCR",
        "🛂 MRZ",
        "🔐 Security",
        "⚠️ Risk & Validation",
    ]
)


# ============================================================
# TAB 1
# ============================================================

with tabs[0]:

    st.subheader(
        "Extracted Identity Information"
    )

    # --------------------------------------------------------
    # Main normalized fields
    # --------------------------------------------------------

    st.write(
        "### Identity Fields"
    )

    field_col1, field_col2 = st.columns(
        2
    )

    with field_col1:

        st.write(
            f"**Document Type:** "
            f"{display_fields.get('document_type', 'Not detected')}"
        )

        st.write(
            f"**Full Name:** "
            f"{display_fields.get('name', 'Not detected')}"
        )

        st.write(
            f"**Document Number:** "
            f"{display_fields.get('document_number', 'Not detected')}"
        )

        st.write(
            f"**Date of Birth:** "
            f"{display_fields.get('date_of_birth', 'Not detected')}"
        )

    with field_col2:

        st.write(
            f"**Date of Issue:** "
            f"{display_fields.get('date_of_issue', 'Not detected')}"
        )

        st.write(
            f"**Date of Expiry:** "
            f"{display_fields.get('date_of_expiry', 'Not detected')}"
        )

        st.write(
            f"**Nationality:** "
            f"{display_fields.get('nationality', 'Not detected')}"
        )

        st.write(
            f"**Sex / Gender:** "
            f"{display_fields.get('sex', 'Not detected')}"
        )


    # --------------------------------------------------------
    # Raw extraction result
    # --------------------------------------------------------

    st.divider()

    st.write(
        "### Raw Extraction Result"
    )

    if fields:

        st.json(
            fields
        )

    else:

        st.warning(
            "No fields were returned by the extraction module."
        )


# ============================================================
# TAB 2
# ============================================================

with tabs[1]:

    st.subheader(
        "OCR Result"
    )

    try:

        confidence = float(
            ocr_result.get(
                "mean_confidence",
                0,
            )
        )

    except:

        confidence = 0


    if confidence <= 1:

        confidence_display = confidence * 100

    else:

        confidence_display = confidence


    st.metric(
        "OCR Confidence",
        f"{confidence_display:.1f}%",
    )


    if ocr_result.get(
        "text"
    ):

        st.text_area(
            "Detected Text",
            ocr_result["text"],
            height=350,
        )

    else:

        st.warning(
            "No text was detected by OCR."
        )


# ============================================================
# TAB 3
# ============================================================

with tabs[2]:

    st.subheader(
        "Passport MRZ Analysis"
    )

    st.write(
        f"**Status:** "
        f"{mrz_result.get('status', 'NOT_FOUND')}"
    )

    st.write(
        mrz_result.get(
            "message",
            "",
        )
    )


    if mrz_result.get(
        "lines"
    ):

        st.write(
            "**Detected MRZ Lines**"
        )

        for line in mrz_result[
            "lines"
        ]:

            st.code(
                line
            )


    if mrz_result.get(
        "fields"
    ):

        st.write(
            "**MRZ Fields**"
        )

        st.json(
            mrz_result["fields"]
        )


    if mrz_result.get(
        "checks"
    ):

        st.write(
            "**Check Digit Results**"
        )

        st.json(
            mrz_result["checks"]
        )


# ============================================================
# TAB 4
# ============================================================

with tabs[3]:

    st.subheader(
        "Security Analysis"
    )


    st.write(
        "### 📷 Image Quality"
    )

    st.json(
        quality
    )


    st.write(
        "### 🚪 Document Gate"
    )

    st.write(
        f"Accepted: **{gate.get('accepted', gate.get('passed', False))}**"
    )

    try:

        gate_confidence = float(
            gate.get(
                "confidence",
                0,
            )
        )

        if gate_confidence <= 1:
            gate_confidence *= 100

    except:

        gate_confidence = 0


    st.write(
        f"Gate Confidence: **{gate_confidence:.1f}%**"
    )

    st.write(
        gate.get(
            "message",
            "",
        )
    )


    st.write(
        "### 👤 Face Detection"
    )

    st.write(
        f"Status: **{face_result.get('status', 'UNKNOWN')}**"
    )

    st.write(
        face_result.get(
            "message",
            "",
        )
    )


    st.write(
        "### 🧪 Image Forensics"
    )

    try:

        tampering_score = float(
            tampering_result.get(
                "score",
                0,
            )
        )

    except:

        tampering_score = 0


    st.write(
        f"Indicator Score: **{tampering_score:.1f}**"
    )

    st.write(
        tampering_result.get(
            "message",
            "",
        )
    )


    if tampering_result.get(
        "indicators"
    ):

        for indicator in tampering_result[
            "indicators"
        ]:

            st.warning(
                indicator
            )


# ============================================================
# TAB 5
# ============================================================

with tabs[4]:

    st.subheader(
        "Risk & Validation"
    )


    try:

        score = float(
            risk.get(
                "score",
                0,
            )
        )

    except:

        score = 0


    level = risk.get(
        "level",
        "UNKNOWN",
    )


    st.metric(
        "Screening Risk Indicator",
        f"{score:.0f}/100",
    )


    if level == "LOW":

        st.success(
            "LOW — Few risk indicators were detected."
        )

    elif level == "MEDIUM":

        st.warning(
            "MEDIUM — Some indicators require manual review."
        )

    else:

        st.error(
            "HIGH — Multiple risk indicators require manual review."
        )


    # ========================================================
    # VALIDATION
    # ========================================================

    st.write(
        "### ✅ Validation"
    )

    validation_status = validation.get(
        "status",
        "UNKNOWN",
    )

    st.write(
        f"Status: **{validation_status}**"
    )


    # ========================================================
    # SHOW NAME + FIELDS AFTER VALIDATION
    # ========================================================

    st.write(
        "### 🪪 Identity Fields After Validation"
    )

    v1, v2 = st.columns(
        2
    )

    with v1:

        st.write(
            f"**Name:** "
            f"{display_fields.get('name', 'Not detected')}"
        )

        st.write(
            f"**Document Number:** "
            f"{display_fields.get('document_number', 'Not detected')}"
        )

        st.write(
            f"**Date of Birth:** "
            f"{display_fields.get('date_of_birth', 'Not detected')}"
        )

        st.write(
            f"**Nationality:** "
            f"{display_fields.get('nationality', 'Not detected')}"
        )

    with v2:

        st.write(
            f"**Document Type:** "
            f"{display_fields.get('document_type', 'Not detected')}"
        )

        st.write(
            f"**Date of Issue:** "
            f"{display_fields.get('date_of_issue', 'Not detected')}"
        )

        st.write(
            f"**Date of Expiry:** "
            f"{display_fields.get('date_of_expiry', 'Not detected')}"
        )

        st.write(
            f"**Sex / Gender:** "
            f"{display_fields.get('sex', 'Not detected')}"
        )


    # ========================================================
    # VALIDATION ISSUES
    # ========================================================

    if validation.get(
        "issues"
    ):

        st.write(
            "### Validation Issues"
        )

        for issue in validation[
            "issues"
        ]:

            st.warning(
                str(issue)
            )

    else:

        st.success(
            "No validation issues detected."
        )


    # ========================================================
    # RISK REASONS
    # ========================================================

    st.write(
        "### Risk Reasons"
    )

    if risk.get(
        "reasons"
    ):

        for reason in risk[
            "reasons"
        ]:

            st.write(
                f"- {reason}"
            )

    else:

        st.write(
            "No significant risk indicators."
        )


# ============================================================
# OPTIONAL PERSON PHOTO
# ============================================================

if person_photo is not None:

    st.divider()

    st.subheader(
        "👤 Optional Person Photo"
    )

    photo_bytes = person_photo.getvalue()

    try:

        person_image = load_image(
            photo_bytes
        )

        st.image(
            person_image,
            caption="Uploaded Person Photo",
            use_container_width=True,
        )

        person_face = analyze_faces(
            person_image
        )

        st.write(
            f"Detected faces: "
            f"**{person_face.get('count', 0)}**"
        )

        st.info(
            "Biometric identity matching is not enabled in this MVP. "
            "The uploaded photo is only checked for face presence."
        )

    except Exception as exc:

        st.error(
            f"Unable to process person photo: {exc}"
        )


# ============================================================
# AUDIT INFORMATION
# ============================================================

st.divider()

st.subheader(
    "🔏 Audit Information"
)

st.write(
    f"**SHA-256 File Hash:** `{file_hash}`"
)

st.write(
    "**Screening Type:** AI-assisted document screening"
)

st.caption(
    """
    Disclaimer: This application provides automated screening
    indicators for demonstration and decision-support purposes.
    It does not establish that a document is genuine or fraudulent
    and should not replace authorized manual verification.
    """
)
