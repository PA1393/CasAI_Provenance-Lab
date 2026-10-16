"""JSON stdin/stdout bridge for inDelphi's legacy, isolated Python environment."""

from __future__ import annotations

import importlib.metadata
import json
import sys


def main() -> None:
    request = json.load(sys.stdin)
    model_dir = request.get("model_dir")
    if model_dir:
        sys.path.insert(0, model_dir)

    import inDelphi  # type: ignore[import-not-found]

    inDelphi.init_model(celltype=request["cell_type"])
    predictions, stats = inDelphi.predict(request["sequence"], request["cutsite"])
    rows = json.loads(predictions.to_json(orient="records"))
    try:
        version = importlib.metadata.version("inDelphi")
    except importlib.metadata.PackageNotFoundError:
        version = None
    json.dump(
        {
            "version": version,
            "predictions": rows,
            "prediction_count": len(rows),
            "stats": _json_safe(stats),
        },
        sys.stdout,
    )


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


if __name__ == "__main__":
    main()
