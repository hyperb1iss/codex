from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Callable, Dict, Optional, Tuple


def create_output_schema_file(
    schema: Optional[Dict[str, Any]],
) -> Tuple[Optional[str], Callable[[], None]]:
    if schema is None:
        return None, lambda: None

    if not isinstance(schema, dict):
        raise TypeError("output_schema must be a dict")

    schema_dir = tempfile.mkdtemp(prefix="codex-output-schema-")
    schema_path = os.path.join(schema_dir, "schema.json")
    try:
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f)
    except Exception:
        _cleanup_dir(schema_dir)
        raise

    return schema_path, lambda: _cleanup_dir(schema_dir)


def _cleanup_dir(path: str) -> None:
    try:
        import shutil

        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        return
