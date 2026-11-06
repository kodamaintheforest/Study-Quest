from flask import Flask, jsonify, request, render_template, send_from_directory
import json
import os
import uuid

from character import Character, DIFFICULTY_XP, CERT_CATALOG, CERT_STATUSES
import tools_data
import journal
import study
import roster
import homes
import notebook
import todos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CHAR_PATH = os.path.join(DATA_DIR, "character.json")
TOOLS_PATH = os.path.join(DATA_DIR, "tools_state.json")
KNOWLEDGE_PATH = os.path.join(DATA_DIR, "knowledge.md")
DIARY_PATH = os.path.join(DATA_DIR, "diary.md")
STUDY_ACTIVE_PATH = os.path.join(DATA_DIR, "active_session.json")
STUDY_HISTORY_PATH = os.path.join(DATA_DIR, "sessions.jsonl")
TODOS_PATH = os.path.join(DATA_DIR, "todos.json")

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)


def load_tools_state():
    if not os.path.exists(TOOLS_PATH):
        state = tools_data.build_initial_state()
        save_tools_state(state)
        return state
    with open(TOOLS_PATH) as f:
        return json.load(f)


def save_tools_state(state):
    with open(TOOLS_PATH, "w") as f:
        json.dump(state, f, indent=2)


def effective_level(char):
    """Level used for unlock checks. Admin mode reports an unreachable
    level so every gate downstream opens, without touching real XP/level -
    flip admin_mode off and everything reverts to the true progress
    instantly, nothing was ever written to stats/certs/XP."""
    return 10**9 if char.admin_mode else char.level


def character_payload(char):
    equipped = roster.get_character(char.equipped_character_id)
    display_name = equipped["name"] if equipped else char.name
    return {
        "name": display_name,
        "level": char.level,
        "tier": char.tier,
        "tier_index": char.tier_index,
        "total_xp": char.total_xp,
        "xp_into_level": char.xp_into_level,
        "xp_for_next_level": char.xp_for_next_level,  # variable now, not always 100
        "red_stats": char.red_stats,
        "blue_stats": char.blue_stats,
        "certs": char.certs,
        "equipped_character_id": char.equipped_character_id,
        "equipped_tier_override": char.equipped_tier_override,
        "equipped_home_id": char.equipped_home_id,
        "admin_mode": char.admin_mode,
    }


@app.route("/")
def index():
    char = Character.load(CHAR_PATH)
    return render_template("index.html", tier_index=char.tier_index)


@app.route("/api/admin/toggle", methods=["POST"])
def admin_toggle():
    char = Character.load(CHAR_PATH)
    char.admin_mode = not char.admin_mode
    char.save(CHAR_PATH)
    return jsonify({"admin_mode": char.admin_mode})


@app.route("/api/state")
def get_state():
    char = Character.load(CHAR_PATH)
    return jsonify({
        "character": character_payload(char),
        "tools": load_tools_state(),
        "knowledge_html": journal.read_markdown_as_html(KNOWLEDGE_PATH),
        "difficulty_xp": DIFFICULTY_XP,
        "cert_catalog": CERT_CATALOG,
        "cert_statuses": list(CERT_STATUSES),
    })


@app.route("/api/apply_skill", methods=["POST"])
def apply_skill():
    body = request.get_json(force=True)
    team = body.get("team")
    stat = body.get("stat")
    difficulty = body.get("difficulty", "medium")
    bonus = body.get("bonus", 0)
    note = (body.get("note") or "").strip()

    char = Character.load(CHAR_PATH)
    try:
        result = char.add_skill(team, stat, difficulty, bonus)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    char.save(CHAR_PATH)

    if note:
        journal.append_entry(
            KNOWLEDGE_PATH,
            f"**[{team.upper()} / {stat}]** ({difficulty}, +{result['amount']} XP) — {note}",
        )

    return jsonify({
        "character": character_payload(char),
        "result": result,
        "knowledge_html": journal.read_markdown_as_html(KNOWLEDGE_PATH),
    })


@app.route("/api/admin/set_stat", methods=["POST"])
def admin_set_stat():
    body = request.get_json(force=True)
    team = body.get("team")
    stat = body.get("stat")
    value = body.get("value", 0)

    char = Character.load(CHAR_PATH)
    try:
        char.set_stat(team, stat, value)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    char.save(CHAR_PATH)
    return jsonify({"character": character_payload(char)})


@app.route("/api/certs/add", methods=["POST"])
def add_cert():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    status = body.get("status", "earned")
    date_earned = body.get("date_earned")
    notes = (body.get("notes") or "").strip()
    xp_override = body.get("xp_override")

    if not name:
        return jsonify({"error": "cert name required"}), 400

    char = Character.load(CHAR_PATH)
    try:
        result = char.add_cert(name, status=status, date_earned=date_earned,
                                notes=notes, xp_override=xp_override)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    char.save(CHAR_PATH)

    if status == "earned" and result["xp_awarded"] > 0:
        entry = f"**[CERT EARNED]** {name} (+{result['xp_awarded']} XP)"
        if notes:
            entry += f" — {notes}"
        journal.append_entry(KNOWLEDGE_PATH, entry)

    return jsonify({
        "character": character_payload(char),
        "result": result,
        "knowledge_html": journal.read_markdown_as_html(KNOWLEDGE_PATH),
    })


@app.route("/api/certs/remove", methods=["POST"])
def remove_cert():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "cert name required"}), 400
    char = Character.load(CHAR_PATH)
    char.remove_cert(name)
    char.save(CHAR_PATH)
    return jsonify({"character": character_payload(char)})


@app.route("/api/tools/toggle", methods=["POST"])
def toggle_tool():
    body = request.get_json(force=True)
    team = body.get("team")
    category = body.get("category")
    tool = body.get("tool")

    state = load_tools_state()
    try:
        current = state[team][category][tool]
        state[team][category][tool] = not current
    except KeyError:
        return jsonify({"error": "Unknown team/category/tool"}), 400
    save_tools_state(state)
    return jsonify({"tools": state})


@app.route("/api/diary", methods=["POST"])
def submit_diary():
    text = (request.get_json(force=True).get("text") or "").strip()
    if text:
        journal.append_entry(DIARY_PATH, text)
    return jsonify({"ok": True})


@app.route("/api/diary/entries")
def diary_entries():
    return jsonify({"entries": journal.list_entries(DIARY_PATH)})


@app.route("/api/diary/update", methods=["POST"])
def diary_update():
    body = request.get_json(force=True) or {}
    entry_id = body.get("id")
    text = (body.get("text") or "").strip()
    if not entry_id or not text:
        return jsonify({"error": "id and text required"}), 400
    updated = journal.update_entry(DIARY_PATH, entry_id, text)
    if updated is None:
        return jsonify({"error": "entry not found"}), 404
    return jsonify({"entry": updated})


@app.route("/api/diary/delete", methods=["POST"])
def diary_delete():
    body = request.get_json(force=True) or {}
    entry_id = body.get("id")
    if not entry_id:
        return jsonify({"error": "id required"}), 400
    if not journal.delete_entry(DIARY_PATH, entry_id):
        return jsonify({"error": "entry not found"}), 404
    return jsonify({"ok": True})


@app.route("/diary")
def diary_history():
    char = Character.load(CHAR_PATH)
    return render_template(
        "diary.html",
        tier_suffix=["neutral", "red", "green"][char.tier_index],
        tier_index=char.tier_index,
    )


# ---------------- Study Mode ----------------

@app.route("/api/study/status")
def study_status():
    return jsonify({"active": study.load_active(STUDY_ACTIVE_PATH)})


@app.route("/api/study/start", methods=["POST"])
def study_start():
    body = request.get_json(force=True) or {}
    try:
        session = study.start_session(
            STUDY_ACTIVE_PATH,
            nudge_interval_min=body.get("nudge_interval_min", 30),
            topic=body.get("topic", ""),
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 409
    return jsonify({"active": session})


@app.route("/api/study/checkpoint", methods=["POST"])
def study_checkpoint():
    note = (request.get_json(force=True) or {}).get("note", "").strip()
    if not note:
        return jsonify({"error": "checkpoint note required"}), 400
    try:
        session = study.add_checkpoint(STUDY_ACTIVE_PATH, note)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"active": session})


@app.route("/api/study/pause", methods=["POST"])
def study_pause():
    try:
        session = study.pause_session(STUDY_ACTIVE_PATH)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"active": session})


@app.route("/api/study/resume", methods=["POST"])
def study_resume():
    try:
        session = study.resume_session(STUDY_ACTIVE_PATH)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"active": session})


@app.route("/api/study/stop", methods=["POST"])
def study_stop():
    body = request.get_json(force=True) or {}
    keep = bool(body.get("keep", True))
    final_note = body.get("final_note", "")
    xp_award = body.get("xp_award")  # optional: {"team": "red", "stat": "Recon", "amount": 25}

    try:
        session = study.stop_session(STUDY_ACTIVE_PATH, STUDY_HISTORY_PATH,
                                      keep=keep, final_note=final_note)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400

    result = {"session": session, "xp_result": None}

    # If caller asked to also grant XP, run it through the normal Character
    # code path so leveling/tier-change logic stays in one place.
    if xp_award and keep:
        char = Character.load(CHAR_PATH)
        try:
            xp_result = char.add_skill(
                team=xp_award["team"],
                stat=xp_award["stat"],
                difficulty="easy",
                bonus=max(0, int(xp_award.get("amount", 0)) - 10),  # bonus above the easy base
            )
        except (KeyError, ValueError) as e:
            return jsonify({"error": f"invalid xp_award: {e}"}), 400
        char.save(CHAR_PATH)

        # Also log to Knowledge so it appears in the study trail
        duration_min = session["duration_sec"] // 60
        topic = session.get("topic") or "(no topic)"
        journal.append_entry(
            KNOWLEDGE_PATH,
            f"**[STUDY SESSION]** {duration_min} min on *{topic}* "
            f"(+{xp_result['amount']} XP to {xp_award['team']}/{xp_award['stat']})",
        )
        result["xp_result"] = xp_result
        result["character"] = character_payload(char)
        result["knowledge_html"] = journal.read_markdown_as_html(KNOWLEDGE_PATH)

    return jsonify(result)


@app.route("/api/study/history")
def study_history_api():
    return jsonify({"sessions": study.list_history(STUDY_HISTORY_PATH)})


@app.route("/api/study/delete", methods=["POST"])
def study_delete():
    body = request.get_json(force=True) or {}
    session_id = body.get("id")
    if not session_id:
        return jsonify({"error": "session id required"}), 400
    if not study.delete_session(STUDY_HISTORY_PATH, session_id):
        return jsonify({"error": "session not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/study/update", methods=["POST"])
def study_update():
    body = request.get_json(force=True) or {}
    session_id = body.get("id")
    if not session_id:
        return jsonify({"error": "session id required"}), 400
    updates = {k: body[k] for k in ("topic", "final_note") if k in body}
    if not updates:
        return jsonify({"error": "no editable fields provided"}), 400
    updated = study.update_session(STUDY_HISTORY_PATH, session_id, updates)
    if updated is None:
        return jsonify({"error": "session not found or nothing to update"}), 404
    return jsonify({"session": updated})


@app.route("/study")
def study_page():
    char = Character.load(CHAR_PATH)
    return render_template(
        "study.html",
        tier_index=char.tier_index,
        red_stats=list(char.red_stats.keys()),
        blue_stats=list(char.blue_stats.keys()),
    )


# ---------------- Roster / Character Select ----------------

def _annotate_unlock_state(char):
    """Merge the roster registry with the current character's level to
    produce a locked/unlocked view per class + character + tier."""
    lvl = effective_level(char)
    classes_out = []
    for class_id, meta in roster.CLASSES.items():
        class_locked = lvl < meta["unlock_level"]
        chars_out = []
        for c in roster.get_characters_by_class(class_id):
            char_locked = lvl < c["unlock_level"] or class_locked
            tiers_out = []
            for i, t in enumerate(c["tiers"]):
                tiers_out.append({
                    "index": i,
                    "name": t["name"],
                    "unlock_level": t["unlock_level"],
                    "locked": lvl < t["unlock_level"] or char_locked,
                })
            chars_out.append({
                **c,
                "locked": char_locked,
                "tiers": tiers_out,
            })
        classes_out.append({
            "id": class_id,
            **meta,
            "locked": class_locked,
            "characters": chars_out,
        })
    return classes_out


@app.route("/roster")
def roster_page():
    char = Character.load(CHAR_PATH)
    return render_template("roster.html", tier_index=char.tier_index)


@app.route("/api/roster")
def roster_api():
    char = Character.load(CHAR_PATH)
    return jsonify({
        "classes": _annotate_unlock_state(char),
        "equipped": {
            "character_id": char.equipped_character_id,
            "tier_override": char.equipped_tier_override,
            "level": char.level,
        },
    })


@app.route("/api/roster/equip", methods=["POST"])
def roster_equip():
    body = request.get_json(force=True) or {}
    char_id = body.get("character_id")
    tier_override = body.get("tier_override")  # int 0/1/2 or None for auto

    target = roster.get_character(char_id) if char_id else None
    if target is None:
        return jsonify({"error": "unknown character"}), 400

    if not target.get("has_real_sprites"):
        return jsonify({"error": f"{target['name']} art hasn't landed yet - coming soon"}), 400

    char = Character.load(CHAR_PATH)
    # Enforce unlock rules server-side - don't trust the client's UI
    if effective_level(char) < target["unlock_level"]:
        return jsonify({"error": f"{target['name']} unlocks at Lv {target['unlock_level']}"}), 403
    class_meta = roster.CLASSES.get(target["class"])
    if class_meta and effective_level(char) < class_meta["unlock_level"]:
        return jsonify({"error": f"{class_meta['label']} class unlocks at Lv {class_meta['unlock_level']}"}), 403

    if tier_override is not None:
        try:
            tier_override = int(tier_override)
        except (TypeError, ValueError):
            return jsonify({"error": "tier_override must be 0, 1, or 2"}), 400
        if tier_override not in (0, 1, 2):
            return jsonify({"error": "tier_override must be 0, 1, or 2"}), 400
        if effective_level(char) < target["tiers"][tier_override]["unlock_level"]:
            return jsonify({"error": f"tier locked until Lv {target['tiers'][tier_override]['unlock_level']}"}), 403

    char.equipped_character_id = char_id
    char.equipped_tier_override = tier_override
    char.save(CHAR_PATH)

    return jsonify({
        "character": character_payload(char),
        "equipped_character": target,
    })


# ---------------- Homes ----------------

def _annotate_home_unlock_state(char):
    lvl = effective_level(char)
    out = []
    for h in homes.HOMES:
        out.append({
            **h,
            "locked": lvl < h["unlock_level"],
        })
    return out


@app.route("/homes")
def homes_page():
    char = Character.load(CHAR_PATH)
    return render_template("homes.html", tier_index=char.tier_index)


@app.route("/api/homes")
def homes_api():
    char = Character.load(CHAR_PATH)
    return jsonify({
        "homes": _annotate_home_unlock_state(char),
        "equipped_home_id": char.equipped_home_id,
        "level": char.level,
    })


@app.route("/api/homes/equip", methods=["POST"])
def homes_equip():
    body = request.get_json(force=True) or {}
    home_id = body.get("home_id")
    target = homes.get_home(home_id) if home_id else None
    if target is None:
        return jsonify({"error": "unknown home"}), 400

    char = Character.load(CHAR_PATH)
    if effective_level(char) < target["unlock_level"]:
        return jsonify({"error": f"{target['name']} unlocks at Lv {target['unlock_level']}"}), 403

    char.equipped_home_id = home_id
    char.save(CHAR_PATH)
    return jsonify({
        "character": character_payload(char),
        "equipped_home": target,
    })


# ---------------- Notebook ----------------

NB_ROOT = os.path.join(DATA_DIR, "notebook")
nb = notebook.Notebook(NB_ROOT)


@app.route("/notebook")
def notebook_page():
    return render_template("notebook.html")


@app.route("/api/notebook/tree")
def notebook_tree():
    return jsonify({"nodes": nb.list_nodes()})


@app.route("/api/notebook/node", methods=["POST"])
def notebook_create_node():
    body = request.get_json(force=True) or {}
    title = (body.get("title") or "Untitled").strip()
    parent_id = body.get("parent_id")
    node = nb.create_node(title, parent_id)
    return jsonify({"node": node})


@app.route("/api/notebook/node/<node_id>", methods=["GET"])
def notebook_get_node(node_id):
    tree = nb._load_tree()
    if node_id not in tree:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "node": tree[node_id],
        "content": nb.get_content(node_id),
    })


@app.route("/api/notebook/node/<node_id>", methods=["PUT"])
def notebook_update_node(node_id):
    body = request.get_json(force=True) or {}
    # Whitelist: only title, content, parent_id, order are updatable
    if "title" in body:
        nb.rename_node(node_id, body["title"])
    if "content" in body:
        nb.save_content(node_id, body["content"])
    if "parent_id" in body or "order" in body:
        nb.move_node(node_id, body.get("parent_id"), body.get("order"))
    tree = nb._load_tree()
    if node_id not in tree:
        return jsonify({"error": "not found"}), 404
    return jsonify({"node": tree[node_id]})


@app.route("/api/notebook/node/<node_id>", methods=["DELETE"])
def notebook_delete_node(node_id):
    ok = nb.delete_node(node_id)
    if not ok:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/notebook/search")
def notebook_search():
    q = request.args.get("q", "")
    return jsonify({"hits": nb.search(q)})


NB_IMAGES_DIR = os.path.join(NB_ROOT, "images")
ALLOWED_IMG_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


@app.route("/api/notebook/image", methods=["POST"])
def notebook_upload_image():
    f = request.files.get("image")
    if f is None or not f.filename:
        return jsonify({"error": "no image provided"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED_IMG_EXT:
        return jsonify({"error": f"unsupported image type: {ext}"}), 400
    os.makedirs(NB_IMAGES_DIR, exist_ok=True)
    image_id = f"{uuid.uuid4().hex}.{ext}"
    f.save(os.path.join(NB_IMAGES_DIR, image_id))
    return jsonify({"url": f"/api/notebook/image/{image_id}"})


@app.route("/api/notebook/image/<image_id>")
def notebook_get_image(image_id):
    # image_id is generated server-side (uuid.ext) and never trusted from a
    # client-supplied path, but this route takes it straight from the URL,
    # so guard against path traversal ("../../etc/passwd" etc) explicitly
    # rather than relying on send_from_directory alone.
    if "/" in image_id or "\\" in image_id or ".." in image_id:
        return jsonify({"error": "invalid image id"}), 400
    return send_from_directory(NB_IMAGES_DIR, image_id)


# ---------------- Todo List ----------------

@app.route("/todos")
def todos_page():
    char = Character.load(CHAR_PATH)
    return render_template("todos.html", tier_index=char.tier_index, sections=todos.SECTIONS)


@app.route("/api/todos")
def todos_list():
    return jsonify({"todos": todos.list_todos(TODOS_PATH), "sections": todos.SECTIONS})


@app.route("/api/todos", methods=["POST"])
def todos_add():
    body = request.get_json(force=True) or {}
    try:
        todo = todos.add_todo(TODOS_PATH, body.get("section", ""), body.get("text", ""))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"todo": todo})


@app.route("/api/todos/toggle", methods=["POST"])
def todos_toggle():
    body = request.get_json(force=True) or {}
    todo = todos.toggle_todo(TODOS_PATH, body.get("id"))
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"todo": todo})


@app.route("/api/todos/update", methods=["POST"])
def todos_update():
    body = request.get_json(force=True) or {}
    try:
        todo = todos.update_todo(TODOS_PATH, body.get("id"), text=body.get("text"), section=body.get("section"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"todo": todo})


@app.route("/api/todos/delete", methods=["POST"])
def todos_delete():
    body = request.get_json(force=True) or {}
    if not todos.delete_todo(TODOS_PATH, body.get("id")):
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/todos/clear_completed", methods=["POST"])
def todos_clear_completed():
    body = request.get_json(force=True) or {}
    count = todos.clear_completed(TODOS_PATH, section=body.get("section"))
    return jsonify({"cleared": count})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
