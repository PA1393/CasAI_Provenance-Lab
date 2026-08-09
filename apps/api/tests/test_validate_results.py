from app.modules.simulation.validate import validate_results


def _good_result() -> dict:
    return {
        "on_target_score": 0.82,
        "off_target_score": 0.14,
        "edited_sequence": "ACGTACGTACGT",
        "edited_positions": [4, 7],
    }


# --- happy path ---


def test_valid_result_returns_no_problems() -> None:
    assert validate_results(_good_result(), sequence_length=12) == []


def test_valid_result_with_empty_edited_positions() -> None:
    result = _good_result()
    result["edited_positions"] = []
    assert validate_results(result, sequence_length=12) == []


# --- on_target_score ---


def test_on_target_score_missing() -> None:
    result = _good_result()
    del result["on_target_score"]
    problems = validate_results(result, sequence_length=12)
    assert any("on_target_score" in p for p in problems)


def test_on_target_score_out_of_range() -> None:
    result = _good_result()
    result["on_target_score"] = 1.5
    problems = validate_results(result, sequence_length=12)
    assert any("on_target_score" in p and "0, 1" in p for p in problems)


def test_on_target_score_negative() -> None:
    result = _good_result()
    result["on_target_score"] = -0.1
    problems = validate_results(result, sequence_length=12)
    assert any("on_target_score" in p for p in problems)


# --- off_target_score ---


def test_off_target_score_missing() -> None:
    result = _good_result()
    del result["off_target_score"]
    problems = validate_results(result, sequence_length=12)
    assert any("off_target_score" in p for p in problems)


def test_off_target_score_out_of_range() -> None:
    result = _good_result()
    result["off_target_score"] = 2.0
    problems = validate_results(result, sequence_length=12)
    assert any("off_target_score" in p for p in problems)


# --- edited_sequence ---


def test_edited_sequence_missing() -> None:
    result = _good_result()
    del result["edited_sequence"]
    problems = validate_results(result, sequence_length=12)
    assert any("edited_sequence" in p for p in problems)


def test_edited_sequence_empty() -> None:
    result = _good_result()
    result["edited_sequence"] = ""
    problems = validate_results(result, sequence_length=12)
    assert any("edited_sequence" in p for p in problems)


def test_edited_sequence_has_non_acgt_bases() -> None:
    result = _good_result()
    result["edited_sequence"] = "ACGTNXYZ"
    problems = validate_results(result, sequence_length=12)
    assert any("non-ACGT" in p for p in problems)


def test_edited_sequence_accepts_lowercase() -> None:
    result = _good_result()
    result["edited_sequence"] = "acgtacgt"
    assert validate_results(result, sequence_length=12) == []


# --- edited_positions ---


def test_edited_positions_out_of_range_high() -> None:
    result = _good_result()
    result["edited_positions"] = [4, 999]
    problems = validate_results(result, sequence_length=12)
    assert any("999" in p and "out of range" in p for p in problems)


def test_edited_positions_out_of_range_low() -> None:
    result = _good_result()
    result["edited_positions"] = [0, 4]
    problems = validate_results(result, sequence_length=12)
    assert any("0" in p and "out of range" in p for p in problems)


def test_edited_positions_negative() -> None:
    result = _good_result()
    result["edited_positions"] = [-1]
    problems = validate_results(result, sequence_length=12)
    assert any("out of range" in p for p in problems)


def test_edited_positions_wrong_type() -> None:
    result = _good_result()
    result["edited_positions"] = "not-a-list"
    problems = validate_results(result, sequence_length=12)
    assert any("edited_positions must be a list" in p for p in problems)


def test_edited_positions_non_int_entry() -> None:
    result = _good_result()
    result["edited_positions"] = [4, "seven"]
    problems = validate_results(result, sequence_length=12)
    assert any("must be an int" in p for p in problems)


# --- multiple problems reported at once ---


def test_multiple_problems_all_reported() -> None:
    result = {
        "on_target_score": 1.7,
        "off_target_score": -0.2,
        "edited_sequence": "ACGZ",
        "edited_positions": [99],
    }
    problems = validate_results(result, sequence_length=12)
    assert len(problems) >= 4
