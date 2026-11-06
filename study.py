"""
Study session tracking.

Two files on disk:
  active_session.json  -- 0 or 1 running session. Deleted on stop/discard.
  sessions.jsonl       -- append-only history, one JSON object per line.

JSONL for the history (not one big JSON list) so a partial write can't
corrupt everything. Standard pattern for log-shaped data.
"""
import json
import os
import time
import uuid
from datetime import datetime


def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def load_active(active_path):
    if not os.path.exists(active_path):
        return None
    with open(active_path, encoding="utf-8") as f:
        return json.load(f)


def save_active(active_path, session):
    _ensure_dir(active_path)
    with open(active_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)


def clear_active(active_path):
    if os.path.exists(active_path):
        os.remove(active_path)


def start_session(active_path, nudge_interval_min=30, topic=""):
    if load_active(active_path) is not None:
        raise RuntimeError("A session is already running. Stop it before starting another.")
    session = {
        "id": uuid.uuid4().hex,
        "started_at": time.time(),
        "started_at_iso": datetime.now().isoformat(timespec="seconds"),
        "nudge_interval_sec": max(60, int(nudge_interval_min) * 60),
        "topic": topic.strip(),
        "checkpoints": [],  # list of {t (epoch), note}
        "paused_at": None,       # epoch time of last pause, None if running
        "paused_total_sec": 0,   # cumulative time spent paused, subtracted from duration
    }
    save_active(active_path, session)
    return session


def add_checkpoint(active_path, note):
    session = load_active(active_path)
    if session is None:
        raise RuntimeError("No active session.")
    session["checkpoints"].append({
        "t": time.time(),
        "iso": datetime.now().isoformat(timespec="seconds"),
        "note": note.strip(),
    })
    save_active(active_path, session)
    return session


def pause_session(active_path):
    session = load_active(active_path)
    if session is None:
        raise RuntimeError("No active session.")
    if session.get("paused_at") is not None:
        raise RuntimeError("Session is already paused.")
    session["paused_at"] = time.time()
    save_active(active_path, session)
    return session


def resume_session(active_path):
    session = load_active(active_path)
    if session is None:
        raise RuntimeError("No active session.")
    if session.get("paused_at") is None:
        raise RuntimeError("Session isn't paused.")
    session["paused_total_sec"] = session.get("paused_total_sec", 0) + (time.time() - session["paused_at"])
    session["paused_at"] = None
    save_active(active_path, session)
    return session


def stop_session(active_path, history_path, keep=True, final_note=""):
    """End the running session. If keep=False, discard entirely (don't
    write to history). Returns the finished session dict."""
    session = load_active(active_path)
    if session is None:
        raise RuntimeError("No active session.")

    # If stopped while paused, fold the final pause gap into paused_total_sec
    # first so duration math below is correct without a special case.
    if session.get("paused_at") is not None:
        session["paused_total_sec"] = session.get("paused_total_sec", 0) + (time.time() - session["paused_at"])
        session["paused_at"] = None

    session["ended_at"] = time.time()
    session["ended_at_iso"] = datetime.now().isoformat(timespec="seconds")
    session["duration_sec"] = int(session["ended_at"] - session["started_at"] - session.get("paused_total_sec", 0))
    if final_note.strip():
        session["final_note"] = final_note.strip()

    clear_active(active_path)

    if keep:
        _ensure_dir(history_path)
        with open(history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(session) + "\n")

    return session


def list_history(history_path, limit=100):
    if not os.path.exists(history_path):
        return []
    sessions = []
    with open(history_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    sessions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # skip corrupted lines, don't crash the whole page
    # newest first
    sessions.reverse()
    return sessions[:limit]


def _rewrite_history(history_path, sessions):
    """Atomic rewrite of the history file. Write to temp, fsync, rename -
    guarantees we never end up with a half-written history file if the
    process dies mid-write. Sessions passed in chronological order (oldest
    first) since that's how the file is stored on disk."""
    tmp_path = history_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        for s in sessions:
            f.write(json.dumps(s) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, history_path)  # atomic on POSIX and Windows


def delete_session(history_path, session_id):
    if not os.path.exists(history_path):
        return False
    # Read all, filter by id, rewrite. list_history reverses; we want
    # chronological order back for the file.
    sessions = list_history(history_path, limit=10**9)
    sessions.reverse()
    before = len(sessions)
    sessions = [s for s in sessions if s.get("id") != session_id]
    if len(sessions) == before:
        return False  # nothing matched
    _rewrite_history(history_path, sessions)
    return True


def update_session(history_path, session_id, updates):
    """Merge `updates` dict into the session with matching id. Only allows
    editing safe fields - never lets you rewrite id/started_at/duration
    from the client, so you can't spoof historical hours."""
    if not os.path.exists(history_path):
        return None
    ALLOWED_FIELDS = {"topic", "final_note"}
    safe_updates = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}
    if not safe_updates:
        return None

    sessions = list_history(history_path, limit=10**9)
    sessions.reverse()
    updated = None
    for s in sessions:
        if s.get("id") == session_id:
            s.update(safe_updates)
            updated = s
            break
    if updated is None:
        return None
    _rewrite_history(history_path, sessions)
    return updated
