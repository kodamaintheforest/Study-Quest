import json
import os
import uuid
from datetime import datetime


def _ensure_dir(path):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def _entries_path(md_path):
    """Structured entries live alongside the .md file, same basename + .jsonl.
    e.g. data/diary.md -> data/diary.entries.jsonl"""
    base, _ = os.path.splitext(md_path)
    return base + ".entries.jsonl"


def _rewrite_entries(entries_path, entries):
    """Atomic rewrite, same crash-safe pattern as study.py's history file."""
    _ensure_dir(entries_path)
    tmp_path = entries_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, entries_path)


def _load_entries(entries_path):
    if not os.path.exists(entries_path):
        return []
    entries = []
    with open(entries_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip corrupted lines, don't crash the whole page
    return entries


def _migrate_legacy_md(md_path, entries_path):
    """One-time import: if an old flat .md file exists with content but no
    entries file yet, wrap the whole thing as a single legacy entry so
    nothing gets silently dropped when this file switches to structured
    storage. Runs at most once - after migration the .md file is left alone
    (not deleted) as a backup, but is no longer read from.
    """
    if os.path.exists(entries_path):
        return  # already migrated
    if not os.path.exists(md_path):
        return
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()
    if not raw.strip():
        return
    legacy_entry = {
        "id": uuid.uuid4().hex,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": None,
        "text": raw.strip(),
        "legacy": True,  # flag so the UI can label this as "imported from old format"
    }
    _rewrite_entries(entries_path, [legacy_entry])


def append_entry(md_path, entry_text):
    """Add a new structured entry. Kept the same function name/signature
    used by app.py and study.py's XP-award logging so no call sites break."""
    entries_path = _entries_path(md_path)
    _migrate_legacy_md(md_path, entries_path)
    entries = _load_entries(entries_path)
    entries.append({
        "id": uuid.uuid4().hex,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": None,
        "text": entry_text.strip(),
        "legacy": False,
    })
    _rewrite_entries(entries_path, entries)


def list_entries(md_path):
    """Newest first, matches study.list_history's ordering convention."""
    entries_path = _entries_path(md_path)
    _migrate_legacy_md(md_path, entries_path)
    entries = _load_entries(entries_path)
    entries.reverse()
    return entries


def update_entry(md_path, entry_id, new_text):
    """Edit an existing entry's text in place. Refuses to touch legacy
    entries' structure beyond text - id/created_at stay put so history
    ordering never shifts under you."""
    entries_path = _entries_path(md_path)
    entries = _load_entries(entries_path)
    updated = None
    for e in entries:
        if e.get("id") == entry_id:
            e["text"] = new_text.strip()
            e["updated_at"] = datetime.now().isoformat(timespec="seconds")
            updated = e
            break
    if updated is None:
        return None
    _rewrite_entries(entries_path, entries)
    return updated


def delete_entry(md_path, entry_id):
    entries_path = _entries_path(md_path)
    entries = _load_entries(entries_path)
    before = len(entries)
    entries = [e for e in entries if e.get("id") != entry_id]
    if len(entries) == before:
        return False
    _rewrite_entries(entries_path, entries)
    return True


def read_markdown_as_html(md_path):
    """Back-compat shim for any caller still expecting one big HTML blob
    (e.g. the Knowledge panel on the home page). Renders all entries newest
    first as a single markdown document, same visual behavior as before."""
    import markdown as md
    entries = list_entries(md_path)
    if not entries:
        return ""
    raw = "\n\n".join(
        f"### {e['created_at']}\n{e['text']}" for e in entries
    )
    return md.markdown(raw)
