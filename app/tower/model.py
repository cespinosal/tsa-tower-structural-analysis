from dataclasses import dataclass, field
from typing import List


@dataclass
class Node:
    id: int
    x: float
    y: float
    z: float


@dataclass
class Member:
    id: int
    node_i: int
    node_j: int
    member_type: str  # 'leg', 'diagonal', 'horizontal', 'guy'
    profile: str = ""


@dataclass
class TowerConfig:
    tower_type: str = "triangular"   # triangular | square | guyed
    base_width: float = 4.0          # m — face width at base
    top_width: float = 2.0           # m — face width at top
    height: float = 30.0             # m
    n_sections: int = 8
    # Guyed-specific
    shaft_width: float = 1.0         # m — shaft face width (guyed only)
    n_guy_levels: int = 3
    anchor_radius: float = 15.0      # m — distance from center to guy anchor

    def update(self, data: dict) -> None:
        for key, val in data.items():
            if hasattr(self, key):
                try:
                    setattr(self, key, type(getattr(self, key))(val))
                except (TypeError, ValueError):
                    pass
