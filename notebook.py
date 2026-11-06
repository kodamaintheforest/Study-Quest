"""
Notebook backend - hierarchical note-taking with per-node markdown files.

Storage layout:
  data/notebook/
    notebook.json                 # Tree structure (parent-child, ordering, titles)
    nodes/
      {uuid}.md                   # One markdown file per node

The tree lives in notebook.json - a flat dict of {node_id: node_metadata}
with parent_id references. Rendering to a tree is a JS concern.

Per-node markdown is in individual files, keyed by UUID so renaming a node
does NOT rename its file (filesystem stays clean, ids never break links).

Atomic writes via os.replace() for both tree and notes - same crash-safety
pattern used in study.py.
"""

import json
import os
import re
import uuid
from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class Notebook:
    """
    A notebook = a tree of nodes + a directory of markdown files per node.

    Node schema:
      {
        "id": "uuid-str",
        "title": "Display name",
        "parent_id": "uuid-str" or None (None = root-level),
        "order": 0,           # sort order among siblings
        "created_at": "iso",
        "updated_at": "iso",
      }
    """

    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.tree_path = os.path.join(root_dir, "notebook.json")
        self.nodes_dir = os.path.join(root_dir, "nodes")
        os.makedirs(self.nodes_dir, exist_ok=True)
        if not os.path.exists(self.tree_path):
            self._save_tree({})

    # ---------- Tree ops ----------

    def _load_tree(self):
        with open(self.tree_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_tree(self, tree):
        tmp = self.tree_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.tree_path)

    def list_nodes(self):
        """Return the whole tree as a flat list, ordered by parent -> siblings."""
        tree = self._load_tree()
        return list(tree.values())

    def create_node(self, title, parent_id=None):
        tree = self._load_tree()
        # Determine order among siblings
        siblings = [n for n in tree.values() if n.get("parent_id") == parent_id]
        order = max([s.get("order", 0) for s in siblings], default=-1) + 1

        node = {
            "id": str(uuid.uuid4()),
            "title": title or "Untitled",
            "parent_id": parent_id,
            "order": order,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        tree[node["id"]] = node
        self._save_tree(tree)
        # create empty markdown file
        self._save_content(node["id"], "")
        return node

    def rename_node(self, node_id, new_title):
        tree = self._load_tree()
        if node_id not in tree:
            return None
        tree[node_id]["title"] = new_title or "Untitled"
        tree[node_id]["updated_at"] = _now_iso()
        self._save_tree(tree)
        return tree[node_id]

    def move_node(self, node_id, new_parent_id, new_order=None):
        tree = self._load_tree()
        if node_id not in tree:
            return None
        # Prevent moving a node into its own descendant (would create a cycle)
        if new_parent_id and self._is_descendant(tree, new_parent_id, node_id):
            return None
        tree[node_id]["parent_id"] = new_parent_id
        if new_order is not None:
            tree[node_id]["order"] = new_order
        tree[node_id]["updated_at"] = _now_iso()
        self._save_tree(tree)
        return tree[node_id]

    def delete_node(self, node_id):
        """Delete node and ALL descendants (and their .md files)."""
        tree = self._load_tree()
        if node_id not in tree:
            return False
        # Collect all descendants + self
        to_delete = self._collect_descendants(tree, node_id) + [node_id]
        for nid in to_delete:
            tree.pop(nid, None)
            md_path = os.path.join(self.nodes_dir, f"{nid}.md")
            if os.path.exists(md_path):
                os.remove(md_path)
        self._save_tree(tree)
        return True

    def _collect_descendants(self, tree, node_id):
        result = []
        stack = [n["id"] for n in tree.values() if n.get("parent_id") == node_id]
        while stack:
            nid = stack.pop()
            result.append(nid)
            stack.extend(n["id"] for n in tree.values() if n.get("parent_id") == nid)
        return result

    def _is_descendant(self, tree, maybe_descendant_id, of_ancestor_id):
        cur = tree.get(maybe_descendant_id)
        while cur:
            if cur.get("parent_id") == of_ancestor_id:
                return True
            cur = tree.get(cur.get("parent_id"))
        return False

    # ---------- Node content ----------

    def get_content(self, node_id):
        path = os.path.join(self.nodes_dir, f"{node_id}.md")
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _save_content(self, node_id, content):
        path = os.path.join(self.nodes_dir, f"{node_id}.md")
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content or "")
        os.replace(tmp, path)

    def save_content(self, node_id, content):
        tree = self._load_tree()
        if node_id not in tree:
            return False
        self._save_content(node_id, content)
        tree[node_id]["updated_at"] = _now_iso()
        self._save_tree(tree)
        return True

    # ---------- Search ----------

    def search(self, query):
        """Case-insensitive substring search across titles AND content.
        Returns [{node_id, title, snippet}] sorted by relevance (title matches first).
        """
        q = (query or "").strip().lower()
        if not q:
            return []
        tree = self._load_tree()
        hits = []
        for nid, node in tree.items():
            title_hit = q in node["title"].lower()
            content = self.get_content(nid)
            content_hit = q in content.lower()
            if not title_hit and not content_hit:
                continue
            # Build a snippet around the first content match
            snippet = ""
            if content_hit:
                idx = content.lower().find(q)
                start = max(0, idx - 40)
                end = min(len(content), idx + len(q) + 60)
                snippet = ("..." if start > 0 else "") + content[start:end].replace("\n", " ") + ("..." if end < len(content) else "")
            hits.append({
                "node_id": nid,
                "title": node["title"],
                "snippet": snippet,
                "title_hit": title_hit,
            })
        # Title matches first, then content matches
        hits.sort(key=lambda h: (not h["title_hit"], h["title"].lower()))
        return hits
