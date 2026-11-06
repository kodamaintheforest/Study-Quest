import json
import os

# Logarithmic level curve: xp_to_reach_level(n) = round(50 * n^1.6)
# This means each level costs progressively more XP. Tier evolutions at
# 36 (Red Teamer) and 65 (Ghost in the Wire) - Tyranitar-style: brutal
# grind, monster payoff. Level 36 ≈ 15k XP, level 65 ≈ 40k XP.
LEVEL_XP_COEFFICIENT = 50
LEVEL_XP_EXPONENT = 1.6
TIER_THRESHOLDS = [36, 65]
TIER_NAMES = ["Script Kiddie", "Red Teamer", "Ghost in the Wire"]

DIFFICULTY_XP = {"easy": 10, "medium": 25, "hard": 50}

# Preset cert catalog with XP awards. Add new ones freely - just add to
# this dict, no code change needed. Certs that fire earlier in the curve
# are meaningful jumps; certs later on are appropriately proportional.
CERT_CATALOG = {
    "CompTIA Security+":  {"xp": 500,  "team_hint": "blue"},
    "CompTIA Network+":   {"xp": 500,  "team_hint": "blue"},
    "CompTIA CySA+":      {"xp": 500,  "team_hint": "blue"},
    "CompTIA PenTest+":   {"xp": 750,  "team_hint": "red"},
    "CompTIA CASP+":      {"xp": 1000, "team_hint": "blue"},
    "CEH":                {"xp": 1000, "team_hint": "red"},
    "eJPT":               {"xp": 600,  "team_hint": "red"},
    "PNPT":               {"xp": 1500, "team_hint": "red"},
    "OSCP":               {"xp": 2500, "team_hint": "red"},
    "OSEP":               {"xp": 3500, "team_hint": "red"},
    "OSED":               {"xp": 3500, "team_hint": "red"},
    "CISSP":              {"xp": 2500, "team_hint": "blue"},
    "GCIH":               {"xp": 1500, "team_hint": "blue"},
    "GCFA":               {"xp": 2000, "team_hint": "blue"},
    "SC-200 (Azure)":     {"xp": 800,  "team_hint": "blue"},
    "AZ-500 (Azure)":     {"xp": 1000, "team_hint": "blue"},
}

# Valid cert statuses. Only "earned" awards XP.
CERT_STATUSES = ("earned", "in_progress", "planned")

DEFAULT_RED_STATS = {
    "Recon": 0,
    "Exploitation": 0,
    "Privilege Escalation": 0,
    "C2 / Persistence": 0,
    "Evasion": 0,
}

DEFAULT_BLUE_STATS = {
    "Log Analysis": 0,
    "Detection Engineering": 0,
    "Incident Response": 0,
    "Threat Hunting": 0,
    "Hardening": 0,
}


def xp_required_for_level(n):
    """Total cumulative XP needed to be AT level n."""
    if n <= 0:
        return 0
    return round(LEVEL_XP_COEFFICIENT * (n ** LEVEL_XP_EXPONENT))


def level_from_xp(total_xp):
    """Inverse: highest level fully paid for by given total XP."""
    if total_xp <= 0:
        return 0
    # closed-form inverse of the power curve, then floor
    lvl = int((total_xp / LEVEL_XP_COEFFICIENT) ** (1 / LEVEL_XP_EXPONENT))
    # correct for rounding errors at boundaries
    while xp_required_for_level(lvl + 1) <= total_xp:
        lvl += 1
    while lvl > 0 and xp_required_for_level(lvl) > total_xp:
        lvl -= 1
    return lvl


class Character:
    def __init__(self, name="Analyst-01", red_stats=None, blue_stats=None, certs=None,
                 equipped_character_id="analyst_01", equipped_tier_override=None,
                 equipped_home_id="moms_basement", admin_mode=False):
        self.name = name
        self.red_stats = red_stats if red_stats is not None else dict(DEFAULT_RED_STATS)
        self.blue_stats = blue_stats if blue_stats is not None else dict(DEFAULT_BLUE_STATS)
        # certs is a list of dicts: {name, status, date_earned, xp_awarded, notes}
        self.certs = certs if certs is not None else []
        # Roster equip state. equipped_tier_override lets user manually pin
        # a tier lower than their level allows (nostalgia / cosmetic). None
        # means "auto - use the tier the current level unlocks."
        self.equipped_character_id = equipped_character_id
        self.equipped_tier_override = equipped_tier_override
        # Home equip state. Defaults to moms_basement (starter). Cosmetic only.
        self.equipped_home_id = equipped_home_id
        # Superuser toggle - bypasses level-gated unlock checks so every
        # character/home/tier is viewable/equippable regardless of level.
        # Purely an access flag, never touches XP or level, so flipping it
        # off doesn't lose or change any earned progress.
        self.admin_mode = admin_mode

    @property
    def total_xp(self):
        stat_xp = sum(self.red_stats.values()) + sum(self.blue_stats.values())
        cert_xp = sum(c.get("xp_awarded", 0) for c in self.certs if c.get("status") == "earned")
        return stat_xp + cert_xp

    @property
    def level(self):
        return level_from_xp(self.total_xp)

    @property
    def xp_into_level(self):
        """XP earned since reaching current level."""
        return self.total_xp - xp_required_for_level(self.level)

    @property
    def xp_for_next_level(self):
        """XP needed to level up from current level to next."""
        return xp_required_for_level(self.level + 1) - xp_required_for_level(self.level)

    @property
    def tier_index(self):
        lvl = self.level
        for i, threshold in enumerate(TIER_THRESHOLDS):
            if lvl < threshold:
                return i
        return len(TIER_THRESHOLDS)

    @property
    def tier(self):
        return TIER_NAMES[self.tier_index]

    def _stats_for(self, team):
        if team not in ("red", "blue"):
            raise ValueError(f"team must be 'red' or 'blue', got {team!r}")
        return self.red_stats if team == "red" else self.blue_stats

    def add_skill(self, team, stat, difficulty="medium", bonus=0):
        stats = self._stats_for(team)
        if stat not in stats:
            raise ValueError(f"Unknown {team} stat: {stat}")
        if difficulty not in DIFFICULTY_XP:
            raise ValueError(f"Unknown difficulty: {difficulty}")

        amount = DIFFICULTY_XP[difficulty] + max(0, int(bonus))
        old_level, old_tier = self.level, self.tier
        stats[stat] += amount

        return {
            "amount": amount,
            "leveled_up": self.level > old_level,
            "tier_changed": self.tier != old_tier,
        }

    def set_stat(self, team, stat, value):
        # Admin override - direct write, no XP math, for fixing mistakes.
        stats = self._stats_for(team)
        if stat not in stats:
            raise ValueError(f"Unknown {team} stat: {stat}")
        stats[stat] = max(0, int(value))

    def add_cert(self, name, status="earned", date_earned=None, notes="", xp_override=None):
        """Add or update a cert. If status is 'earned' and cert has an XP
        value in CERT_CATALOG (or xp_override provided), that XP counts
        toward level. Returns level_up/tier_change info like add_skill."""
        if status not in CERT_STATUSES:
            raise ValueError(f"Unknown status: {status}")

        old_level, old_tier = self.level, self.tier

        # If cert already exists, update it in place instead of duplicating
        existing = next((c for c in self.certs if c["name"] == name), None)
        catalog_entry = CERT_CATALOG.get(name, {})
        xp_awarded = 0
        if status == "earned":
            xp_awarded = int(xp_override) if xp_override is not None else catalog_entry.get("xp", 0)

        cert_data = {
            "name": name,
            "status": status,
            "date_earned": date_earned if status == "earned" else None,
            "xp_awarded": xp_awarded,
            "notes": notes,
        }
        if existing:
            existing.update(cert_data)
        else:
            self.certs.append(cert_data)

        return {
            "xp_awarded": xp_awarded,
            "leveled_up": self.level > old_level,
            "tier_changed": self.tier != old_tier,
        }

    def remove_cert(self, name):
        self.certs = [c for c in self.certs if c["name"] != name]

    def to_dict(self):
        return {
            "name": self.name,
            "red_stats": self.red_stats,
            "blue_stats": self.blue_stats,
            "certs": self.certs,
            "equipped_character_id": self.equipped_character_id,
            "equipped_tier_override": self.equipped_tier_override,
            "equipped_home_id": self.equipped_home_id,
            "admin_mode": self.admin_mode,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            red_stats=data["red_stats"],
            blue_stats=data["blue_stats"],
            certs=data.get("certs", []),
            equipped_character_id=data.get("equipped_character_id", "analyst_01"),
            equipped_tier_override=data.get("equipped_tier_override"),
            equipped_home_id=data.get("equipped_home_id", "moms_basement"),
            admin_mode=data.get("admin_mode", False),
        )

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path):
        if not os.path.exists(path):
            return cls()
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
