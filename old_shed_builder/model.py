"""Serializable, Blender-independent building model. All distances are meters."""

from dataclasses import dataclass, field, asdict
import math

WALLS = ("Front", "Rear", "Left", "Right")


@dataclass
class Opening:
    wall: str = "Front"
    position: float = 1.5
    width: float = 0.85
    height: float = 1.9
    bottom: float = 0.0
    enabled: bool = True


@dataclass
class Leakage:
    override: bool = False
    amount: float = 0.35
    gap: float = 0.006
    variation: float = 0.5
    large_probability: float = 0.04
    missing: float = 0.025
    loose: float = 0.06
    separation: float = 0.018


@dataclass
class Settings:
    schema: int = 1
    width: float = 3.2
    length: float = 4.0
    wall_height: float = 2.4
    foundation_height: float = 0.18
    stud_width: float = 0.045
    stud_depth: float = 0.095
    stud_spacing: float = 0.4
    header_depth: float = 0.16
    joist_depth: float = 0.145
    joist_spacing: float = 0.4
    floor_thickness: float = 0.028
    plank_width: float = 0.18
    plank_thickness: float = 0.022
    plank_gap: float = 0.004
    roof_pitch: float = 30.0
    overhang: float = 0.25
    rafter_depth: float = 0.12
    rafter_spacing: float = 0.6
    ridge_thickness: float = 0.045
    collar_ties: bool = True
    sheathing: bool = True
    door_angle: float = 18.0
    glass: bool = True
    broken_glass: bool = True
    shutters: bool = True
    bow: float = 0.012
    twist: float = 3.0
    cup: float = 0.003
    edge: float = 0.002
    split: float = 0.07
    broken: float = 0.035
    loose: float = 0.04
    separation: float = 0.018
    seed: int = 17
    variation: float = 0.7
    aging: float = 0.7
    roughness: float = 0.82
    grain: float = 0.65
    dirt: float = 0.35
    water: float = 0.45
    color_variation: float = 0.25
    leakage: float = 0.35
    leak_gap: float = 0.006
    leak_variation: float = 0.5
    large_gaps: float = 0.04
    missing: float = 0.025
    leak_loose: float = 0.06
    leak_separation: float = 0.018
    leak_seed: int = 41
    dramatic: bool = False
    preserve_edits: bool = True
    door: Opening = field(default_factory=Opening)
    window_a: Opening = field(
        default_factory=lambda: Opening("Left", 1.5, 0.8, 0.7, 1.0)
    )
    window_b: Opening = field(
        default_factory=lambda: Opening("Right", 2.6, 0.8, 0.7, 1.0)
    )
    walls: dict = field(default_factory=lambda: {w: Leakage() for w in WALLS})

    @property
    def floor_z(self):
        return self.foundation_height + self.joist_depth + self.floor_thickness

    def span(self, wall):
        return self.width if wall in ("Front", "Rear") else self.length

    def openings(self, wall):
        return [
            (name, op)
            for name, op in [
                ("door", self.door),
                ("window_a", self.window_a),
                ("window_b", self.window_b),
            ]
            if op.enabled and op.wall == wall
        ]

    def leak(self, wall):
        local = self.walls[wall]
        if local.override:
            return local
        return Leakage(
            False,
            self.leakage,
            self.leak_gap,
            self.leak_variation,
            self.large_gaps,
            self.missing,
            self.leak_loose,
            self.leak_separation,
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        data = dict(data)
        for key in ("door", "window_a", "window_b"):
            if key in data:
                data[key] = Opening(**data[key])
        if "walls" in data:
            data["walls"] = {w: Leakage(**data["walls"].get(w, {})) for w in WALLS}
        return cls(**data)


def validate(s):
    """Reject incoherent construction before creating any scene data."""
    errors = []
    for name, value in s.to_dict().items():
        if isinstance(value, (int, float)) and not math.isfinite(value):
            errors.append(f"{name} must be finite")
    for name, low, high in [
        ("width", 1.5, 15),
        ("length", 1.5, 20),
        ("wall_height", 1.5, 6),
        ("stud_width", 0.025, 0.12),
        ("stud_depth", 0.06, 0.25),
        ("stud_spacing", 0.2, 1.2),
        ("header_depth", 0.08, 0.4),
        ("joist_depth", 0.08, 0.4),
        ("joist_spacing", 0.2, 1),
        ("floor_thickness", 0.015, 0.06),
        ("plank_width", 0.08, 0.35),
        ("plank_thickness", 0.012, 0.06),
        ("roof_pitch", 10, 60),
        ("overhang", 0.05, 0.8),
        ("rafter_depth", 0.06, 0.3),
        ("rafter_spacing", 0.25, 1.2),
        ("ridge_thickness", 0.025, 0.12),
        ("foundation_height", 0.05, 0.8),
    ]:
        if not low <= getattr(s, name) <= high:
            errors.append(f"{name} must be between {low} and {high}")
    for name in (
        "variation",
        "aging",
        "roughness",
        "grain",
        "dirt",
        "water",
        "color_variation",
        "leakage",
        "leak_variation",
        "large_gaps",
        "missing",
        "leak_loose",
        "broken",
        "loose",
    ):
        if not 0 <= getattr(s, name) <= 1:
            errors.append(f"{name} must be in [0,1]")
    for name, limit in [
        ("plank_gap", 0.05),
        ("bow", 0.06),
        ("twist", 12),
        ("cup", 0.02),
        ("edge", 0.008),
        ("split", 0.3),
        ("separation", 0.15),
        ("leak_gap", 0.08),
        ("leak_separation", 0.15),
    ]:
        if not 0 <= getattr(s, name) <= limit:
            errors.append(f"{name} must be in [0,{limit}]")
    if not -170 <= s.door_angle <= 170:
        errors.append("Door angle must be in [-170,170] degrees")
    if s.schema != 1:
        errors.append("Unsupported settings schema")
    if s.seed < 0 or s.leak_seed < 0:
        errors.append("Seeds must be nonnegative")
    if set(s.walls) != set(WALLS):
        errors.append("All four wall leakage settings are required")
    for wall, leak in s.walls.items():
        for name in ("amount", "variation", "large_probability", "missing", "loose"):
            if not 0 <= getattr(leak, name) <= 1:
                errors.append(f"{wall} leakage {name} must be in [0,1]")
        if not 0 <= leak.gap <= 0.08 or not 0 <= leak.separation <= 0.15:
            errors.append(f"{wall} gap or separation is out of bounds")
    if (
        s.rafter_depth / math.cos(math.radians(s.roof_pitch))
        <= s.stud_depth * math.tan(math.radians(s.roof_pitch)) + 0.015
    ):
        errors.append("Rafter depth is too small for this pitch and bearing notch")
    if s.stud_depth < 2 * s.stud_width:
        errors.append("Stud depth must be at least twice stud width for corner backing")
    for wall in WALLS:
        intervals = []
        for name, op in s.openings(wall):
            if not all(
                math.isfinite(v) for v in (op.position, op.width, op.height, op.bottom)
            ):
                errors.append(f"{name}: dimensions must be finite")
                continue
            a, b = op.position - op.width / 2, op.position + op.width / 2
            margin = s.stud_depth + 3 * s.stud_width
            if (
                op.width < 0.3
                or op.height < 0.3
                or a < margin
                or b > s.span(wall) - margin
            ):
                errors.append(f"{name}: opening must fit between corner framing")
            if (
                op.bottom < 0
                or op.bottom + op.height + s.header_depth
                > s.wall_height - 2 * s.stud_width
            ):
                errors.append(f"{name}: opening/header must fit below top plates")
            if name != "door" and op.bottom < 2 * s.stud_width:
                errors.append(f"{name}: window needs room for sill and bottom plate")
            if name == "door" and op.bottom != 0:
                errors.append("Door bottom must be zero (finished floor datum)")
            intervals.append((a - 2 * s.stud_width, b + 2 * s.stud_width, name))
        intervals.sort()
        for a, b in zip(intervals, intervals[1:]):
            if a[1] + s.stud_width > b[0]:
                errors.append(f"{wall}: {a[2]} and {b[2]} framing overlaps")
    for name in ("door", "window_a", "window_b"):
        if getattr(s, name).wall not in WALLS:
            errors.append(f"{name}: unknown wall")
    if errors:
        raise ValueError("\n".join(errors))


def wall_point(s, wall, u, z, outward=0):
    """Wall centerline; u grows along +X on front/rear, +Y on sides."""
    d = s.stud_depth
    if wall == "Front":
        return (u - s.width / 2, -s.length / 2 + d / 2 - outward, z)
    if wall == "Rear":
        return (u - s.width / 2, s.length / 2 - d / 2 + outward, z)
    if wall == "Left":
        return (-s.width / 2 + d / 2 - outward, u - s.length / 2, z)
    return (s.width / 2 - d / 2 + outward, u - s.length / 2, z)


def subtract(interval, cuts):
    segments = [interval]
    for a, b in cuts:
        result = []
        for l, r in segments:
            if b <= l or a >= r:
                result.append((l, r))
            else:
                if a > l:
                    result.append((l, a))
                if b < r:
                    result.append((b, r))
        segments = result
    return [(l, r) for l, r in segments if r - l > 0.001]
