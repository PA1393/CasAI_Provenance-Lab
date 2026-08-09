# Validate Results — deterministic post-hoc sanity check on a run's result payload.
# Runs after the engine + scoring produce a result; makes sure the numbers are
# in-range, the edited sequence is well-formed DNA, and edit positions fall inside
# the target sequence. Returns a list of human-readable problem strings so callers
# can log/emit them via provenance. Empty list means the result is valid.

from __future__ import annotations

_ACGT = set("ACGT")


def _in_unit_range(value: object) -> bool:
    """True if *value* is a real number in [0, 1]."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return 0.0 <= float(value) <= 1.0


def validate_results(result: dict, sequence_length: int) -> list[str]:
    """Validate a simulation result dict against basic biology + range invariants.

    Checks:
      * ``on_target_score`` present and in [0, 1]
      * ``off_target_score`` present and in [0, 1]
      * ``edited_sequence`` present, non-empty, and composed only of A/C/G/T
      * every position in ``edited_positions`` is a 1-indexed bp in
        ``1 <= p <= sequence_length``

    Returns an empty list when everything is fine, else a list of readable
    problem strings. Never raises — this is meant to be called defensively on
    whatever the results pipeline produced.
    """
    problems: list[str] = []

    # --- on-target score ---
    if "on_target_score" not in result:
        problems.append("on_target_score missing")
    elif not _in_unit_range(result["on_target_score"]):
        problems.append(
            f"on_target_score must be in [0, 1] (got {result['on_target_score']!r})"
        )

    # --- off-target score ---
    if "off_target_score" not in result:
        problems.append("off_target_score missing")
    elif not _in_unit_range(result["off_target_score"]):
        problems.append(
            f"off_target_score must be in [0, 1] (got {result['off_target_score']!r})"
        )

    # --- edited sequence ---
    edited = result.get("edited_sequence")
    if not edited or not isinstance(edited, str):
        problems.append("edited_sequence missing or empty")
    else:
        bad = set(edited.upper()) - _ACGT
        if bad:
            problems.append(
                f"edited_sequence contains non-ACGT base(s): {sorted(bad)}"
            )

    # --- edited positions ---
    positions = result.get("edited_positions", [])
    if positions is None:
        positions = []
    if not isinstance(positions, (list, tuple)):
        problems.append(f"edited_positions must be a list (got {type(positions).__name__})")
    else:
        for p in positions:
            if not isinstance(p, int) or isinstance(p, bool):
                problems.append(f"edited_positions entry must be an int (got {p!r})")
                continue
            if not (1 <= p <= sequence_length):
                problems.append(
                    f"edited_positions entry {p} out of range 1..{sequence_length}"
                )

    return problems
