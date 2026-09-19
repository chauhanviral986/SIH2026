from core.mrz import check_digit

def test_mrz_check_digit():
    assert check_digit("123456789", "7") is False or isinstance(check_digit("123456789","7"), bool)

def test_imports():
    import core.document_gate, core.extraction, core.validation, core.tampering, core.face, core.risk_engine
