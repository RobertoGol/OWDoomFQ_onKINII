#!/usr/bin/env python3
"""Check Markdown navigation/fences and audited schema-size tables. Standard library only."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP_DIRS = {".git", "node_modules", ".venv", ".cache", "build", "dist", "UZDoomOriginal"}
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
SCALAR_BYTES = {"u8": 1, "u16": 2, "u32": 4, "u64": 8, "f32": 4}


def markdown_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.md") if not SKIP_DIRS.intersection(p.relative_to(root).parts))


def content_lines(text: str) -> list[str]:
    """Exclude fenced code so example headings/fences do not affect navigation."""
    result: list[str] = []
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if fence is None:
            if match:
                token = match.group(1)
                fence = (token[0], len(token))
                result.append("")
            else:
                result.append(line)
        else:
            result.append("")
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1]:
                fence = None
    return result


def slugify(heading: str) -> str:
    heading = re.sub(r"[^\w\s-]", "", heading.strip().lower(), flags=re.UNICODE)
    return re.sub(r"\s", "-", heading)


def anchors(text: str) -> set[str]:
    seen: dict[str, int] = {}
    result: set[str] = set()
    for line in content_lines(text):
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        base = slugify(match.group(1))
        index = seen.get(base, 0)
        seen[base] = index + 1
        result.add(base if index == 0 else f"{base}-{index}")
    return result


def check_fences(text: str) -> bool:
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if not match:
            continue
        token = match.group(1)
        if fence is None:
            fence = (token[0], len(token))
        elif token[0] == fence[0] and len(token) >= fence[1]:
            fence = None
    return fence is None


def schema_sizes(fields: list[dict[str, int | str]]) -> tuple[int, int]:
    packed = native = 0
    max_align = 1
    for field in fields:
        kind = str(field["type"])
        count = int(field["count"])
        if kind not in SCALAR_BYTES or count < 1:
            raise ValueError(f"unsupported field: {field!r}")
        size = SCALAR_BYTES[kind]
        align = size
        max_align = max(max_align, align)
        native = ((native + align - 1) // align) * align + size * count
        packed += size * count
    native = ((native + max_align - 1) // max_align) * max_align
    return packed, native


def check_schema_table(root: Path, errors: list[str]) -> int:
    manifest_path = root / "tools/docs_schemas.json"
    doc_path = root / "ReadmeFilesRU/SERIALIZATION_SPEC.md"
    if not manifest_path.is_file() or not doc_path.is_file():
        errors.append("missing schema manifest or SERIALIZATION_SPEC.md")
        return 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = doc_path.read_text(encoding="utf-8")
    table: dict[str, tuple[int, int]] = {}
    for match in re.finditer(r"^\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", text, re.MULTILINE):
        name, packed, native = match.groups()
        table[name] = (int(packed), int(native))
    for schema in manifest["schemas"]:
        name = schema["name"]
        calculated = schema_sizes(schema["fields"])
        expected = (schema["packed_bytes"], schema["native_x64_bytes"])
        if calculated != expected:
            errors.append(f"{name}: manifest sizes {expected} != calculated {calculated}")
        if table.get(name) != expected:
            errors.append(f"{name}: documentation table {table.get(name)} != audited {expected}")
        if not (root / "ReadmeFilesRU" / schema["document"]).is_file():
            errors.append(f"{name}: missing source document {schema['document']}")
    return len(manifest["schemas"])


def check(root: Path) -> tuple[list[str], int, int]:
    root = root.resolve()
    files = markdown_files(root)
    errors: list[str] = []
    texts = {path: path.read_text(encoding="utf-8") for path in files}
    anchor_cache = {path: anchors(text) for path, text in texts.items()}
    link_count = 0
    for path, text in texts.items():
        rel = path.relative_to(root)
        if not check_fences(text):
            errors.append(f"{rel}: unclosed code fence")
        for match in LINK_RE.finditer(text):
            target = match.group(1).strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not target:
                continue
            link_count += 1
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not destination.exists():
                errors.append(f"{rel}: missing link target {target}")
                continue
            if parsed.fragment and destination.suffix.lower() == ".md":
                if unquote(parsed.fragment) not in anchor_cache.get(destination, set()):
                    errors.append(f"{rel}: missing anchor {target}")
    schema_count = check_schema_table(root, errors)
    return errors, len(files), link_count + schema_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors, file_count, check_count = check(args.root)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(f"Documentation check failed: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"OK: {file_count} Markdown files; {check_count} local links/schema checks; external URLs not fetched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

