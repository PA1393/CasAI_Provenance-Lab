"""
Ingest a folder of Markdown notes (the "CropVault") into the Supabase RAG vault.

This is the chunking half of the pipeline that was missing: it reads Markdown
source files, upserts a row per file into `vault_sources`, splits each file's
body into token-bounded chunks, and inserts them into `vault_chunks` with
`embedding` left NULL. Run the embedding backfill afterwards to fill vectors:

    python scripts/ingest_vault.py --vault-dir /path/to/cropvault
    python scripts/embed_vault_chunks.py

Format is reproduced from the existing rows in the live project so new data is
consistent with what is already there:

  * source_key = sha256(<relative path with BACKSLASHES>)   e.g. "crops\\maize.md"
  * source_rel / source_path columns store the FORWARD-SLASH path
  * metadata.raw_source_rel stores the BACKSLASH path (the hashed string)
  * source_title = the file's basename (e.g. "maize.md")
  * source_type  = "index" for INDEX* files, "regulator" under regulators/, else "source"

Idempotent: re-running upserts each source and REPLACES that source's chunks
(delete-then-insert), so it is safe to run repeatedly and it also cleans up the
earlier hand-seeded chunks (including their mojibake) on first run.

Env (loaded from apps/api/.env): SUPABASE_URL, SUPABASE_SERVICE_KEY.
Optional dependency: tiktoken (accurate token counts). Falls back to an estimate.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path
from typing import Any

# dotenv / supabase are imported lazily inside main() so that --dry-run works
# without the backend dependencies installed.

# ─── token counting ──────────────────────────────────────────────────────────
# text-embedding-3-small uses the cl100k_base tokenizer. Use tiktoken when it is
# installed for exact counts; otherwise fall back to a rough chars/4 estimate.
try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_ENC.encode(text))

except Exception:  # pragma: no cover - tiktoken is optional
    _ENC = None

    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


# ─── source key + classification ─────────────────────────────────────────────

def source_key_for(rel_backslash: str) -> str:
    """SHA-256 of the backslash relative path — matches the existing rows."""
    return hashlib.sha256(rel_backslash.encode("utf-8")).hexdigest()


def classify(rel_forward: str, name: str) -> str:
    if name.upper().startswith("INDEX"):
        return "index"
    if rel_forward.startswith("regulators/"):
        return "regulator"
    return "source"


# ─── frontmatter parsing ─────────────────────────────────────────────────────

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_URL = re.compile(r"https?://[^\s)\]>]+")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). Values are kept as plain strings."""
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip().strip("[]").strip()
    return meta, text[match.end():]


def first_url(body: str, meta: dict[str, str]) -> str | None:
    if meta.get("url"):
        return meta["url"]
    found = _URL.search(body)
    return found.group(0).rstrip(".,") if found else None


# ─── chunking ────────────────────────────────────────────────────────────────

_HEADING = re.compile(r"^#{1,6}\s+(.*\S)\s*$")


def _heading_text(paragraph: str) -> str | None:
    """Return the heading text if this paragraph is a single Markdown heading line."""
    if "\n" in paragraph:
        return None
    m = _HEADING.match(paragraph)
    return m.group(1).strip() if m else None


def chunk_body(body: str, max_tokens: int) -> list[tuple[str, str | None]]:
    """
    Greedily pack paragraphs (blank-line separated) into chunks under max_tokens.
    A single oversized paragraph is hard-split on whitespace.

    Returns (chunk_text, heading) pairs, where heading is the nearest Markdown
    heading at or above the start of that chunk (section context). Heading lines
    are kept inline in chunk_text; the heading is also surfaced separately.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    chunks: list[tuple[str, str | None]] = []
    current: list[str] = []
    current_tokens = 0
    current_heading: str | None = None   # most recent heading seen
    chunk_heading: str | None = None      # heading active when this chunk started

    def flush() -> None:
        nonlocal current, current_tokens
        if current:
            chunks.append(("\n\n".join(current), chunk_heading))
            current = []
            current_tokens = 0

    for para in paragraphs:
        head = _heading_text(para)
        if head is not None:
            current_heading = head
        if not current:                   # starting a new chunk
            chunk_heading = current_heading

        tokens = count_tokens(para)
        if tokens > max_tokens:
            flush()
            words = para.split()
            buf: list[str] = []
            for word in words:
                buf.append(word)
                if count_tokens(" ".join(buf)) >= max_tokens:
                    chunks.append((" ".join(buf), current_heading))
                    buf = []
            if buf:
                chunks.append((" ".join(buf), current_heading))
            continue
        if current_tokens + tokens > max_tokens:
            flush()
            chunk_heading = current_heading
        current.append(para)
        current_tokens += tokens

    flush()
    return chunks


def build_keywords(meta: dict[str, str]) -> list[str]:
    """Derive a de-duplicated tag list from the note's frontmatter."""
    tags: list[str] = []
    for key in ("crop", "organism", "gene_target", "editing_method", "regulator", "region"):
        value = meta.get(key)
        if value:
            tags.append(value)
    for key in ("techniques", "crops"):     # frontmatter inline lists, e.g. [crispr, base-editing]
        value = meta.get(key)
        if value:
            tags.extend(part for part in value.split(","))
    seen: list[str] = []
    for tag in tags:
        tag = tag.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


# ─── main ────────────────────────────────────────────────────────────────────

def read_text(path: Path) -> str:
    """UTF-8 read with BOM tolerance; normalise CRLF -> LF (fixes prior mojibake/CRLF)."""
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        print(f"  ! {path.name}: not valid UTF-8, falling back to latin-1")
        raw = path.read_text(encoding="latin-1")
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Markdown into the RAG vault.")
    parser.add_argument("--vault-dir", required=True, help="Root folder of Markdown notes.")
    parser.add_argument("--batch", default="cropvault_ingest_v1", help="Batch label stored in metadata.")
    parser.add_argument("--max-tokens", type=int, default=250,
                        help="Max tokens per chunk (smaller = more, section-level chunks).")
    parser.add_argument("--keep-frontmatter", action="store_true",
                        help="Keep YAML frontmatter in chunk_text (default: strip it).")
    parser.add_argument("--replace", action="store_true",
                        help="Re-chunk sources that already have chunks (default: skip them, "
                             "so existing embedded chunks are never deleted).")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report; write nothing.")
    args = parser.parse_args()

    vault_dir = Path(args.vault_dir).resolve()
    if not vault_dir.is_dir():
        raise RuntimeError(f"Vault dir not found: {vault_dir}")

    supabase = None
    if not args.dry_run:
        from dotenv import load_dotenv
        from supabase import create_client

        load_dotenv()
        supabase = create_client(
            require_env("SUPABASE_URL"), require_env("SUPABASE_SERVICE_KEY")
        )

    if _ENC is None:
        print("! tiktoken not installed - token counts are estimates (pip install tiktoken)")

    # Which sources already have chunks? Default behaviour SKIPS these so that
    # existing (possibly embedded) chunks are never deleted. Use --replace to
    # deliberately re-chunk them.
    existing_keys: set[str] = set()
    if supabase is not None and not args.replace:
        resp = supabase.table("vault_chunks").select("source_key").execute()
        existing_keys = {r["source_key"] for r in (resp.data or [])}
        print(f"{len(existing_keys)} source(s) already have chunks — will skip (use --replace to rebuild)")

    md_files = sorted(vault_dir.rglob("*.md"))
    print(f"Found {len(md_files)} Markdown files under {vault_dir}")

    total_chunks = 0
    skipped = 0
    for path in md_files:
        rel_forward = path.relative_to(vault_dir).as_posix()          # crops/maize.md
        rel_backslash = rel_forward.replace("/", "\\")                # crops\maize.md
        key = source_key_for(rel_backslash)
        name = path.name

        raw = read_text(path)
        meta, body = split_frontmatter(raw)
        chunk_source = raw if args.keep_frontmatter else body
        url = first_url(body, meta)

        source_row: dict[str, Any] = {
            "source_key": key,
            "source_title": name,
            "source_url": url,
            "source_type": meta.get("type") or classify(rel_forward, name),
            "source_path": rel_forward,
            "source_rel": rel_forward,
            "organism": meta.get("organism") or meta.get("crop"),
            "gene_target": meta.get("gene_target"),
            "editing_method": meta.get("editing_method"),
            "quality_label": meta.get("reliability") or meta.get("quality_label"),
            "metadata": {
                "import_batch": args.batch,
                "raw_source_rel": rel_backslash,
                "raw_source_file": name,
            },
        }

        keywords = build_keywords(meta) or None
        chunks = chunk_body(chunk_source, args.max_tokens)
        chunk_rows = [
            {
                "source_key": key,
                "chunk_index": i,
                "chunk_text": text,
                "token_count": count_tokens(text),
                "heading": heading,
                "keywords": keywords,
                "metadata": {
                    "ingest_batch": args.batch,
                    "source_title": name,
                    "source_path": rel_forward,
                    "source_url": url,
                },
            }
            for i, (text, heading) in enumerate(chunks)
        ]

        # Non-destructive: skip a source that already has chunks unless --replace.
        if key in existing_keys:
            print(f"  {rel_forward:40} -> skip (already has chunks)")
            skipped += 1
            continue

        print(f"  {rel_forward:40} -> {len(chunk_rows)} chunk(s)")
        total_chunks += len(chunk_rows)

        if args.dry_run:
            continue

        assert supabase is not None
        supabase.table("vault_sources").upsert(source_row, on_conflict="source_key").execute()
        # delete() only matters under --replace (existing_keys is empty otherwise),
        # so this never removes chunks we intend to keep.
        supabase.table("vault_chunks").delete().eq("source_key", key).execute()
        if chunk_rows:
            supabase.table("vault_chunks").insert(chunk_rows).execute()

    verb = "would write" if args.dry_run else "wrote"
    print(f"\nDone. {verb} {total_chunks} chunks across {len(md_files) - skipped} sources"
          f" ({skipped} skipped as already-populated).")
    if not args.dry_run and total_chunks:
        print("Next: python scripts/embed_vault_chunks.py  (fills embeddings for new chunks)")


if __name__ == "__main__":
    main()
