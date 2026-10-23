# Old Shed Builder architecture

Target: Blender 4.3.2, Python bundled with Blender. Dimensions are meters.

## Coordinates and construction
X is width, Y is length (front = negative Y), Z is up. Footprint measures the
outside of structural framing. Foundation starts at Z=0. Finished floor datum
is foundation height + joist depth + floorboard thickness. Wall heights are
measured from this datum to the top of the double top plate. Gable ridge runs
along Y. Openings are measured from each wall's negative X/Y endpoint; their
position is the center of the rough opening. Opening sizes are clear framing
sizes, before jambs. Door bottom is the finished floor.

Front/rear walls own corners. Side plates stop at their inside faces. Corner
backing studs provide nailing surfaces. Headers bear on jack studs; king studs
continue to the plates. Sills sit immediately below window rough openings.

## Persistent data model
`model.Settings` is the serializable source of truth, with three `Opening`
records and four `Leakage` overrides. Scene RNA settings are the editable UI;
each generator root saves its last successful settings as versioned JSON.
Each root has a unique owner ID. Objects carry owner, component, semantic key,
and an initial geometry/transform fingerprint. A rebuild creates replacement
components first, then swaps only owned objects. An explicit preserve flag or
changed fingerprint retains user-edited objects by semantic key. Unrelated
objects and user collection links must survive. Changing structural dimensions
requires rebuilding dependent components; material-only updates do not rebuild
geometry. Baking copies meshes and materials into a separate collection.

## Collection tree (per generator)
- Old Shed <id> (root Empty and private collections)
  - Foundation / Floor
  - Front / Rear / Left / Right
    - Framing
    - Cladding
    - Fixtures
  - Roof
    - Framing
    - Covering

Visibility is composed from wall, component, and global viewport/render flags.
It never changes geometry. Camera profiles store visibility only and may be
restored explicitly or applied automatically from the active scene camera.

## Modules
- model.py: versioned defaults, validation, coordinates, opening intervals
- geometry.py: mesh primitives, member orientation, semantic IDs
- foundation.py / floor.py / framing.py / cladding.py / roof.py / openings.py
- wood.py: subdivided solid boards with continuous deformation fields
- materials.py: procedural wood, metal, glass
- visibility.py: composed viewport/render visibility and camera profiles
- generator.py: transactional selective rebuild, ownership, bake
- properties.py / operators.py / ui.py: Blender API and persistent sidebar

## Staged verification
Each stage extends `tests/run_stage.py`, runs in background Blender, and saves
`artifacts/stage_XX.blend`. Stages 1–10 cover framing, floor/roof, siding,
fixtures, deformation, materials, visibility, leakage, UI/persistence, and
production regression tests. Generated scenes and installable ZIPs are build
artifacts, not source. Use `python scripts/package.py` to package the add-on.

This is a scenic mesh generator, not an engineered building design or a
structural load analysis. Preserved manual geometry can become incompatible
with later dimensions; rebuild reports retained edits rather than discarding them.
