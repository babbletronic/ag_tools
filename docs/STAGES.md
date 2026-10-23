# Reproducible stage scenes

Install `artifacts/old_shed_builder.zip` using the README instructions at any
stage. All source modules are included. For construction-only experiments, run
from the repository root:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/run_stage.py -- N
```

Replace `N` with 1–9. Open the resulting `artifacts/stage_0N.blend` in Blender.
Each scene includes the constructed components and a sample camera/sun/ground.
These stage scripts use the same code with later features disabled, so the
examples remain executable as fixes are made to shared construction routines.

| Stage | Main modules | Runnable scene and checks |
|---|---|---|
| 1. Footprint / framing | model, geometry, foundation, framing | `stage_01.blend`: plates, corner backing, king/jack/header/sill members, impossible-opening rejection |
| 2. Roof / floor | floor, roof | `stage_02.blend`: joists, boards, birdsmouth rafters, ridge, ties, gable studs |
| 3. Siding | cladding, wood | `stage_03.blend`: subdivided solid courses, rough-opening and roof cuts |
| 4. Door / windows | openings | `stage_04.blend`: hinge pivot, braces, jambs, glass shards, shutters |
| 5. Deformation | wood | `stage_05.blend`: deterministic bow/twist/cup, splits, broken and detached ends |
| 6. Materials | materials | `stage_06.blend`: opaque procedural wood, metal, glass, concrete |
| 7. Visibility | visibility | `stage_07.blend`: independent collection visibility and profile restore |
| 8. Leakage | cladding, wood, model | `stage_08.blend`: physical variable gaps, missing siding, wall overrides |
| 9. UI / persistence | properties, operators, ui, generator | `stage_09.blend`: registered sidebar, settings round-trip, owned generation |
| 10. Production regression | tests/test_production.py | `stage_10.blend`: small dilapidated preset; ownership, rollback, selective updates, bake, material-edit preservation |

Every stage verifies positive volume, closed manifold edges, nondegenerate
faces, and the expected construction members. Stage 10 runs the production
suite instead of `run_stage.py`. The independent lighting test produces
`light_leakage_test.blend`, open/closed PNGs and `light_transport.json`.
The independent install test installs the packaged ZIP into temporary Blender
user directories and reopens the saved stage-10 file in another process.

For direct scripting in Blender's Python Console:

```python
import sys
sys.path.insert(0, '/absolute/path/to/ag_tools')
from old_shed_builder.model import Settings
from old_shed_builder.generator import generate
settings = Settings()
root = generate(settings, stage=3)
# Later stages can replace the same owned model:
root = generate(settings, stage=10, root=root)
```

Use `stage=10` for normal development. The UI always generates the full model.
