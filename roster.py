"""
Character roster registry.

Each entry defines a character's identity + unlock rules + sprite paths.
Only Analyst-01 currently has real sprites - everything else renders as a
silhouette placeholder until real art is dropped into static/sprites/roster/.

Unlock rules are level-based per the "no unlock feats yet" decision.
Class unlocks are also level-based - you pick your first class at Lv 1.

Sprite paths follow: static/sprites/roster/{character_id}/{tier}.png
Tiers per character are indexed 0/1/2 same as the main tier system.
"""

CLASSES = {
    "attacker": {
        "label": "Attackers",
        "color": "#dc2626",
        "tagline": "Red team operators. Breach, escalate, dominate.",
        "unlock_level": 0,   # starter class - always available from the start
    },
    "defender": {
        "label": "Defenders",
        "color": "#2563eb",
        "tagline": "Blue team specialists. Detect, respond, harden.",
        "unlock_level": 0,   # starter class
    },
    "watcher": {
        "label": "Watchers",
        "color": "#9333ea",
        "tagline": "Between worlds. Hybrid operators who see both sides.",
        "unlock_level": 20,  # gated - reward for putting real time in
    },
}


TIER_NAMES_BY_CLASS = {
    "attacker": ["Script Kiddie", "Operator", "Ghost in the Wire"],
    "defender": ["SOC Analyst", "Security Engineer", "Threat Hunter"],
    "watcher":  ["Signal Reader", "Grey Operator", "Void Walker"],
}


def _character(cid, cls, name, unlock_lv, bio, has_real_sprites=False):
    """Helper to keep character defs one-liner clean."""
    tier_names = TIER_NAMES_BY_CLASS.get(cls, TIER_NAMES_BY_CLASS["attacker"])
    return {
        "id": cid,
        "class": cls,
        "name": name,
        "unlock_level": unlock_lv,
        "bio": bio,
        "has_real_sprites": has_real_sprites,
        "tiers": [
            {"name": tier_names[0], "unlock_level": unlock_lv},
            {"name": tier_names[1], "unlock_level": max(unlock_lv, 36)},
            {"name": tier_names[2], "unlock_level": max(unlock_lv, 65)},
        ],
    }


ROSTER = [
    # Attackers - Red team
    _character("analyst_01", "attacker", "Analyst-01",
               unlock_lv=0,
               bio="The one who started it all. Terminal cowboy.",
               has_real_sprites=True),
    _character("cyber_chaser", "attacker", "Cyber Chaser",
               unlock_lv=5,
               bio="Threat hunter with a taste for adversary infrastructure.",
               has_real_sprites=True),
    _character("bunker_kid", "attacker", "Bunker Kid",
               unlock_lv=10,
               bio="No sunlight, no problem. 0day dealer from the underground."),

    # Defenders - Blue team
    _character("jail_tech", "defender", "Jail Tech",
               unlock_lv=0,
               bio="Container escapes are her breakfast. Runtime security specialist."),
    _character("cloud_architect", "defender", "Cloud Architect",
               unlock_lv=8,
               bio="Multi-region resilience. Speaks fluent IAM."),
    _character("isp_operator", "defender", "ISP Operator",
               unlock_lv=15,
               bio="Backbone routing. Sees packets as poetry."),
    _character("cyber_viking", "defender", "Cyber Viking",
               unlock_lv=20,
               bio="Shield-wall of the SOC. Runes on his arms, a hunting axe in "
                   "his hands, and every packet on the wire under watch.",
               has_real_sprites=True),

    # Watchers - Purple/hybrid
    _character("the_signal", "watcher", "The Signal",
               unlock_lv=20,
               bio="Speaks in encrypted packets. Nobody knows their real name."),
    _character("chubby_genius", "watcher", "Chubby Genius",
               unlock_lv=25,
               bio="Snacks in one hand, exploit dev in the other."),
    _character("skinny_legend", "watcher", "Skinny Legend",
               unlock_lv=30,
               bio="Whisper-thin op sec. Purple team lead who wrote the playbook."),
    _character("shell_ghost", "watcher", "Shell Ghost",
               unlock_lv=50,
               bio="Endgame form. The one you become when everything clicks."),
]


def get_character(character_id):
    for c in ROSTER:
        if c["id"] == character_id:
            return c
    return None


def get_characters_by_class(class_id):
    return [c for c in ROSTER if c["class"] == class_id]
