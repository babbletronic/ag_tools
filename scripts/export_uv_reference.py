"""Export the actual connected board UVs as a small, reviewable SVG diagram."""

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from old_shed_builder import wood, uvs

root = bpy.data.objects.new("UV reference", None)
bpy.context.scene.collection.objects.link(root)
ctx = SimpleNamespace(root=root, owner="uv-reference", component="cladding", objects=[])
board = wood.board(
    ctx,
    "reference.board",
    2,
    0.25,
    0.04,
    bpy.context.scene.collection,
    (0, 0, 0),
    (1, 0, 0),
    (0, 1, 0),
)
uvs.unwrap(board)
layer = board.data.uv_layers["UVMap"]
labels = board.data.attributes["shed_uv_face"]
colors = ["#f3dfd3", "#eee4ac", "#d9e7da", "#d1e5e7", "#dce0ed", "#e6dced"]
names = ["front", "top", "back", "bottom", "left", "right"]
scale = 420
x0 = 60
y0 = 340
svg = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="400" viewBox="0 0 1000 400">',
    '<rect width="1000" height="400" fill="white"/>',
    '<text x="500" y="35" text-anchor="middle" font-family="sans-serif" font-size="20">Connected timber UV net — before atlas scaling</text>',
]
bounds = {i: [] for i in range(6)}
for face in board.data.polygons:
    label = labels.data[face.index].value
    points = [tuple(layer.data[i].uv) for i in face.loop_indices]
    bounds[label].extend(points)
    poly = " ".join(f"{x0+x*scale:.3f},{y0-y*scale:.3f}" for x, y in points)
    svg.append(
        f'<polygon points="{poly}" fill="{colors[label]}" stroke="#9d9d9d" stroke-width="0.35"/>'
    )
for label, points in bounds.items():
    x = (min(p[0] for p in points) + max(p[0] for p in points)) / 2
    y = (min(p[1] for p in points) + max(p[1] for p in points)) / 2
    xx, yy = x0 + x * scale, y0 - y * scale
    rotate = f' transform="rotate(-90 {xx} {yy})"' if label in (4, 5) else ""
    size = 22 if label in (0, 2) else 12
    svg.append(
        f'<text x="{xx}" y="{yy}" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="{size}"{rotate}>{names[label]}</text>'
    )
svg.append("</svg>")
path = ROOT / "docs" / "images" / "board_uv_net.svg"
path.parent.mkdir(exist_ok=True)
path.write_text("\n".join(svg) + "\n")
print(path)
