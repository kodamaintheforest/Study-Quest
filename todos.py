"""
Sectioned todo list. Local/private - no auth, no sharing, single JSON file.

Stored as one JSON array (not JSONL) because todos get toggled/reordered
constantly, unlike append-only logs like study sessions. Rewritten
atomically on every change via the same tmp-then-rename pattern used
elsewhere in this app.
"""
import json
import os
import time
import uuid

SECTIONS = ["chores", "school work", "projects", "assignments", "work", "misc", "game time"]


def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []  # corrupted file - don't crash the page, just start empty


def _save(path, todos):
    _ensure_dir(path)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def list_todos(path):
    return _load(path)


def add_todo(path, section, text):
    if section not in SECTIONS:
        raise ValueError(f"unknown section: {section}")
    text = text.strip()
    if not text:
        raise ValueError("text required")
    todos = _load(path)
    todo = {
        "id": uuid.uuid4().hex,
        "section": section,
        "text": text,
        "done": False,
        "created_at": time.time(),
    }
    todos.append(todo)
    _save(path, todos)
    return todo


def toggle_todo(path, todo_id):
    todos = _load(path)
    updated = None
    for t in todos:
        if t["id"] == todo_id:
            t["done"] = not t["done"]
            updated = t
            break
    if updated is None:
        return None
    _save(path, todos)
    return updated


def update_todo(path, todo_id, text=None, section=None):
    todos = _load(path)
    updated = None
    for t in todos:
        if t["id"] == todo_id:
            if text is not None:
                text = text.strip()
                if not text:
                    raise ValueError("text required")
                t["text"] = text
            if section is not None:
                if section not in SECTIONS:
                    raise ValueError(f"unknown section: {section}")
                t["section"] = section
            updated = t
            break
    if updated is None:
        return None
    _save(path, todos)
    return updated


def delete_todo(path, todo_id):
    todos = _load(path)
    before = len(todos)
    todos = [t for t in todos if t["id"] != todo_id]
    if len(todos) == before:
        return False
    _save(path, todos)
    return True


def clear_completed(path, section=None):
    """Delete all done=True todos, optionally scoped to one section."""
    todos = _load(path)
    before = len(todos)
    todos = [t for t in todos if not (t["done"] and (section is None or t["section"] == section))]
    _save(path, todos)
    return before - len(todos)
