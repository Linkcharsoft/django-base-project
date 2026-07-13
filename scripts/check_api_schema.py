#!/usr/bin/env python3
"""Static check: every DRF `@action` must declare `@extend_schema`.

drf-spectacular happily auto-infers a response schema from the viewset's
`serializers` dict, so `manage.py spectacular --validate --fail-on-warn`
passes even when a custom action returns a completely different envelope
(`{"items": [...], "total": N}` vs. the declared serializer). The
generated OpenAPI is silently wrong.

This pre-flight check parses every first-party `views.py` with `ast` and
fails when an `@action` method is missing an explicit `@extend_schema`.
Forces the author to declare request/responses honestly.

Run via `just schema-validate` (wired ahead of the Django command).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# First-party app directories are everything top-level except these.
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "django_base",  # settings + base_utils, no viewsets
    "scripts",
    "logs",
    "progress",
    "docs",
    "templates",
    "media",
    "static",
    "audit",
    ".claude",
}


def is_decorator_named(decorator: ast.expr, name: str) -> bool:
    """True if `decorator` is `@<name>` or `@<name>(...)`, regardless of import alias."""
    node = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(node, ast.Name):
        return node.id == name
    if isinstance(node, ast.Attribute):
        return node.attr == name
    return False


def check_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: could not parse ({exc})"]

    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for item in cls.body:
            if not isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            has_action = any(is_decorator_named(d, "action") for d in item.decorator_list)
            if not has_action:
                continue
            has_extend_schema = any(
                is_decorator_named(d, "extend_schema") for d in item.decorator_list
            )
            if not has_extend_schema:
                findings.append(
                    f"{path}:{item.lineno}: {cls.name}.{item.name} is decorated with "
                    f"@action but missing @extend_schema. Custom actions must declare "
                    f"`request=...` and `responses=...` so the OpenAPI schema reflects "
                    f"the real envelope (see docs/conventions.md → openapi schema)."
                )
    return findings


def discover_view_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in EXCLUDED_DIRS:
            continue
        files.extend(sorted(entry.rglob("views.py")))
    return files


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    files = discover_view_files(repo_root)
    if not files:
        print("[check_api_schema] no first-party views.py found", file=sys.stderr)
        return 0

    all_findings: list[str] = []
    for path in files:
        all_findings.extend(check_file(path))

    if all_findings:
        print("[check_api_schema] FAIL — @action without @extend_schema:", file=sys.stderr)
        for f in all_findings:
            print(f"  {f}", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Fix: add @extend_schema(request=..., responses=...) above each "
            "@action. Use users/views.py as the canonical example.",
            file=sys.stderr,
        )
        return 1

    print(f"[check_api_schema] ok — {len(files)} views.py checked, 0 findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
