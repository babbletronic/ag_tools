"""Use a temporary BLENDER_USER_SCRIPTS/CONFIG directory when running this test."""

import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import bpy

result = bpy.ops.preferences.addon_install(
    filepath=str(ROOT / "artifacts" / "old_shed_builder.zip")
)
assert result == {"FINISHED"}, result
result = bpy.ops.preferences.addon_enable(module="old_shed_builder")
assert result == {"FINISHED"}, result
import old_shed_builder

assert "/tmp/" in old_shed_builder.__file__, old_shed_builder.__file__
from old_shed_builder import properties, generator, visibility
from old_shed_builder.model import validate

scene = bpy.data.scenes.new("New scene defaults")
s = properties.from_rna(scene.old_shed_settings)
validate(s)
assert s.window_a.wall == "Left" and s.window_b.wall == "Right"
bpy.data.scenes.remove(scene)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "artifacts" / "stage_10.blend"))
root = bpy.context.scene.old_shed_root
assert root and root["shed_root"]
settings = properties.from_rna(bpy.context.scene.old_shed_settings)
assert abs(settings.leakage - 0.7) < 1e-6
assert settings.walls["Rear"].override
assert "Exterior" in json.loads(root["shed_profiles"])
assert len(generator.owned(root)) > 300
validate(settings)
count = len(generator.owned(root))
generator.generate(settings, root=root)
assert root["shed_preserved_count"] == 0, root["shed_preserved_count"]
assert len(generator.owned(root)) == count
visibility.set_part(root, "roof_covering", viewport=False, render=True)
assert not visibility.state(root)["roof_covering"]["viewport"]
visibility.restore_profile(root, "Exterior")
print("ZIP INSTALL, NEW SCENE DEFAULTS, FRESH-PROCESS PERSISTENCE PASS")
