import math
from typing import List, Tuple
from app.tower.model import Node, Member, TowerConfig


def generate_tower(cfg: TowerConfig) -> Tuple[List[Node], List[Member]]:
    if cfg.tower_type == "square":
        return _generate_square(cfg)
    elif cfg.tower_type == "guyed":
        return _generate_guyed(cfg)
    else:
        return _generate_triangular(cfg)


# ── helpers ──────────────────────────────────────────────────────────────────

def _level_radius(cfg: TowerConfig, t: float) -> float:
    """Circumradius at normalised height t∈[0,1] for a triangular section."""
    face_w = cfg.base_width + (cfg.top_width - cfg.base_width) * t
    return face_w / math.sqrt(3)


def _level_radius_sq(cfg: TowerConfig, t: float) -> float:
    """Circumradius for a square section (corner-to-centre)."""
    face_w = cfg.base_width + (cfg.top_width - cfg.base_width) * t
    return face_w * math.sqrt(2) / 2


def _leg_nodes(angles_deg: List[float], R: float, z: float,
               start_id: int) -> Tuple[List[Node], List[int]]:
    nodes, ids = [], []
    for i, ang_deg in enumerate(angles_deg):
        ang = math.radians(ang_deg)
        nodes.append(Node(id=start_id + i,
                          x=R * math.cos(ang),
                          y=R * math.sin(ang),
                          z=z))
        ids.append(start_id + i)
    return nodes, ids


def _x_brace_members(level_nodes: List[List[int]], lv: int,
                      n_legs: int, start_id: int) -> Tuple[List[Member], int]:
    members = []
    mid = start_id
    for face in range(n_legs):
        a, b = face, (face + 1) % n_legs
        members.append(Member(mid,     level_nodes[lv][a],   level_nodes[lv+1][b], 'diagonal'))
        members.append(Member(mid + 1, level_nodes[lv+1][a], level_nodes[lv][b],   'diagonal'))
        mid += 2
    return members, mid


def _horizontal_ring(level_nodes: List[List[int]], lv: int,
                     n_legs: int, start_id: int) -> Tuple[List[Member], int]:
    members = []
    mid = start_id
    for face in range(n_legs):
        a, b = face, (face + 1) % n_legs
        members.append(Member(mid, level_nodes[lv][a], level_nodes[lv][b], 'horizontal'))
        mid += 1
    return members, mid


# ── triangular lattice ────────────────────────────────────────────────────────

def _generate_triangular(cfg: TowerConfig) -> Tuple[List[Node], List[Member]]:
    angles = [90.0, 210.0, 330.0]
    n_legs = 3
    nodes: List[Node] = []
    members: List[Member] = []
    node_id = 0
    member_id = 0
    level_nodes: List[List[int]] = []

    for lv in range(cfg.n_sections + 1):
        t = lv / cfg.n_sections
        z = cfg.height * t
        R = _level_radius(cfg, t)
        new_nodes, ids = _leg_nodes(angles, R, z, node_id)
        nodes.extend(new_nodes)
        level_nodes.append(ids)
        node_id += n_legs

    for lv in range(cfg.n_sections):
        # legs
        for j in range(n_legs):
            members.append(Member(member_id, level_nodes[lv][j], level_nodes[lv+1][j], 'leg'))
            member_id += 1
        # X-bracing
        new_m, member_id = _x_brace_members(level_nodes, lv, n_legs, member_id)
        members.extend(new_m)
        # top horizontal ring
        new_m, member_id = _horizontal_ring(level_nodes, lv + 1, n_legs, member_id)
        members.extend(new_m)

    # base horizontal ring
    new_m, member_id = _horizontal_ring(level_nodes, 0, n_legs, member_id)
    members.extend(new_m)

    return nodes, members


# ── square lattice ────────────────────────────────────────────────────────────

def _generate_square(cfg: TowerConfig) -> Tuple[List[Node], List[Member]]:
    angles = [45.0, 135.0, 225.0, 315.0]
    n_legs = 4
    nodes: List[Node] = []
    members: List[Member] = []
    node_id = 0
    member_id = 0
    level_nodes: List[List[int]] = []

    for lv in range(cfg.n_sections + 1):
        t = lv / cfg.n_sections
        z = cfg.height * t
        R = _level_radius_sq(cfg, t)
        new_nodes, ids = _leg_nodes(angles, R, z, node_id)
        nodes.extend(new_nodes)
        level_nodes.append(ids)
        node_id += n_legs

    for lv in range(cfg.n_sections):
        for j in range(n_legs):
            members.append(Member(member_id, level_nodes[lv][j], level_nodes[lv+1][j], 'leg'))
            member_id += 1
        new_m, member_id = _x_brace_members(level_nodes, lv, n_legs, member_id)
        members.extend(new_m)
        new_m, member_id = _horizontal_ring(level_nodes, lv + 1, n_legs, member_id)
        members.extend(new_m)

    new_m, member_id = _horizontal_ring(level_nodes, 0, n_legs, member_id)
    members.extend(new_m)

    return nodes, members


# ── guyed tower ───────────────────────────────────────────────────────────────

def _generate_guyed(cfg: TowerConfig) -> Tuple[List[Node], List[Member]]:
    """Narrow triangular lattice shaft + guy wires at evenly spaced levels."""
    angles = [90.0, 210.0, 330.0]
    n_legs = 3
    nodes: List[Node] = []
    members: List[Member] = []
    node_id = 0
    member_id = 0
    level_nodes: List[List[int]] = []

    # Shaft uses shaft_width (constant) instead of tapered base/top
    shaft_cfg = TowerConfig(
        tower_type="triangular",
        base_width=cfg.shaft_width,
        top_width=cfg.shaft_width,
        height=cfg.height,
        n_sections=cfg.n_sections,
    )

    for lv in range(cfg.n_sections + 1):
        t = lv / cfg.n_sections
        z = cfg.height * t
        R = _level_radius(shaft_cfg, t)
        new_nodes, ids = _leg_nodes(angles, R, z, node_id)
        nodes.extend(new_nodes)
        level_nodes.append(ids)
        node_id += n_legs

    for lv in range(cfg.n_sections):
        for j in range(n_legs):
            members.append(Member(member_id, level_nodes[lv][j], level_nodes[lv+1][j], 'leg'))
            member_id += 1
        new_m, member_id = _x_brace_members(level_nodes, lv, n_legs, member_id)
        members.extend(new_m)
        new_m, member_id = _horizontal_ring(level_nodes, lv + 1, n_legs, member_id)
        members.extend(new_m)

    new_m, member_id = _horizontal_ring(level_nodes, 0, n_legs, member_id)
    members.extend(new_m)

    # Guy wire anchor nodes (on the ground)
    anchor_angles = [90.0, 210.0, 330.0]
    anchor_ids: List[int] = []
    for ang_deg in anchor_angles:
        ang = math.radians(ang_deg)
        nodes.append(Node(id=node_id,
                          x=cfg.anchor_radius * math.cos(ang),
                          y=cfg.anchor_radius * math.sin(ang),
                          z=0.0))
        anchor_ids.append(node_id)
        node_id += 1

    # Guy wires: at each guy level attach one wire per anchor
    for g in range(1, cfg.n_guy_levels + 1):
        guy_lv = round(g * cfg.n_sections / (cfg.n_guy_levels + 1))
        attachment_node = level_nodes[guy_lv][0]  # attach to leg 0
        for anc_id in anchor_ids:
            members.append(Member(member_id, attachment_node, anc_id, 'guy'))
            member_id += 1

    return nodes, members
