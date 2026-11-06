"""
Home registry.

Each home entry defines its identity, unlock rules, description, and
pointer to a scene definition. Scene definitions live separately in
static/scenes/{home_id}.json as data so we can hand-tune the isometric
layout without touching Python.

Homes are ranked by tier (0-5) roughly matching the progression:
  Tier 0: Mom's basement (starter)
  Tier 1: Small apartment
  Tier 2: Decent home
  Tier 3: Bigger home
  Tier 4: Mr Nobody / signature homes
  Tier 5: Invisible Home / endgame

Unlock levels are proportional to the Tyranitar-style curve. Homes are
about milestones - hitting a home unlock should feel like a real reward.
"""

HOMES = [
    {
        "id": "moms_basement",
        "name": "Mom's Basement",
        "tier": 0,
        "unlock_level": 0,
        "description": "Where every hacker starts. Concrete floors, mismatched furniture, a single desk with too many monitors.",
        "has_real_art": False,
    },
    {
        "id": "small_apartment",
        "name": "Small Apartment",
        "tier": 1,
        "unlock_level": 15,
        "description": "First place of your own. Studio layout, city view, still ramen for dinner.",
        "has_real_art": False,
    },
    {
        "id": "decent_home",
        "name": "Decent Home",
        "tier": 2,
        "unlock_level": 30,
        "description": "You made it out. Suburban, two bedrooms, actual couch.",
        "has_real_art": False,
    },
    {
        "id": "bigger_home",
        "name": "Bigger Home",
        "tier": 3,
        "unlock_level": 50,
        "description": "Space to think. Multiple rooms, dedicated home office, backyard.",
        "has_real_art": False,
    },
    {
        "id": "mr_nobody",
        "name": "Mr. Nobody's Place",
        "tier": 4,
        "unlock_level": 70,
        "description": "Off-grid, quiet, undocumented. The way you like it.",
        "has_real_art": False,
    },
    {
        "id": "middle_of_nowhere",
        "name": "Middle of Nowhere",
        "tier": 4,
        "unlock_level": 85,
        "description": "Too much house for one person. Perfect.",
        "has_real_art": False,
    },
    {
        "id": "invisible_home",
        "name": "The Invisible Home",
        "tier": 5,
        "unlock_level": 100,
        "description": "Glass hall in the wilderness. All-black minimalist interior, pool, second-floor bedroom loft. Inspired by Joshua Tree.",
        "has_real_art": False,  # will flip to True when scene art lands
    },
]


def get_home(home_id):
    for h in HOMES:
        if h["id"] == home_id:
            return h
    return None


def default_home_id():
    """Home everyone starts with."""
    return "moms_basement"
