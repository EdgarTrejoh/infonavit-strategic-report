from text_normalization import normalize_text_payload, repair_mojibake_text


def test_repair_mojibake_text_restores_common_spanish_accents():
    text = "CrÃ©ditos de adquisiciÃ³n. Â¿CuÃ¡l es el Ã­ndice?"

    assert repair_mojibake_text(text) == "Créditos de adquisición. ¿Cuál es el índice?"


def test_repair_mojibake_text_restores_double_encoded_text():
    text = "CrÃƒÂ©ditos Ã‚Â¿CuÃƒÂ¡l"

    assert repair_mojibake_text(text) == "Créditos ¿Cuál"


def test_normalize_text_payload_repairs_nested_structures():
    payload = {
        "label": "Ãndice SHF de Precios de la Vivienda",
        "items": ["Nuevo LeÃ³n", {"question": "Â¿CuÃ¡l familia?"}],
    }

    assert normalize_text_payload(payload) == {
        "label": "Índice SHF de Precios de la Vivienda",
        "items": ["Nuevo León", {"question": "¿Cuál familia?"}],
    }
