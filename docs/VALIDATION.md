# Validation results

Validated in the supplied cloud environment with **Blender 4.3.2**, Cycles CPU,
and four render threads. No additional runtime Python packages are required.

## Completed checks

- **Stages 1–9:** all passed. Each saved its own `.blend` test scene.
  Solid mesh counts were 83, 231, 363, 421, 421, 421, 421, 420, and 420.
  Every generated solid had manifold edges, positive signed volume, and
  nondegenerate faces. Required members and stage-specific behavior were checked.
- **Production suite: 16 tests passed**, zero failed/skipped. Coverage includes
  deterministic repeated builds and data cleanup; preserved mesh/material/hinge
  edits; animated doors on all four walls; unrelated object and collection-link
  preservation; root transforms; compatible partial updates; rejection of
  incompatible changes; injected construction-failure rollback; normals and
  physical board thickness; heavy damage; clear rough openings and header
  bearing; independent camera profiles; per-wall leakage isolation; independent
  mesh baking; invalid input rejection; registered operators; and a larger preset.
- **Add-on lifecycle:** register, unregister, and re-register passed.
- **Packaged ZIP installation:** passed using Blender's actual Install/Enable
  operators with isolated user directories. No source-path import substitution.
- **Fresh-process persistence:** passed. A new Blender process enabled the
  installed add-on, reopened `stage_10.blend`, recovered nested settings and
  profiles, and rebuilt without falsely identifying saved objects as edited.
  New scenes also received valid independent defaults for both windows.
- **Cycles light transport:** passed using an enclosed shed with door/windows
  disabled, zero base gaps, and zero wood deformation for the closed reference.
  Of 4,753 exterior-to-interior wall probes, the closed wall blocked all rays;
  opening geometric siding gaps left **748 unblocked**. In a sunlight-only
  interior render, mean diagnostic image RGB rose from **0.001587** to
  **0.016499** (about **10.4×**). This is an image comparison, not an irradiance
  measurement. There are no transparent siding materials or interior helper lights.
- **Visual inspection:** Cycles exterior and cutaway renders were inspected.
  Gable closure, ridge clearance, and rafter penetrations were corrected during
  the staged work. Sample scenes and renders are provided under `artifacts/`.

## Reproduction and evidence

Commands are in the README and stage guide. Evidence files:

- `artifacts/validation/production.log`
- `artifacts/validation/stages.log`
- `artifacts/validation/install_and_persistence.log`
- `artifacts/validation/light_transport.log`
- `artifacts/light_transport.json`
- `artifacts/leakage_closed.png`, `artifacts/leakage_open.png`

## Practical limits

The supplied Blender build cannot use OpenImageDenoise. Samples and lighting
checks therefore use Cycles CPU without denoising; the add-on does not change
an existing user's render settings. Supported API behavior was exercised in
background Blender; interactive panel clicks and other Blender versions were
not independently certified.

Preserved manual objects are intentionally not refitted to new dimensions.
Deformation is bounded and solids are verified, but arbitrary damage settings
are not checked by a global collision solver. The result is scenic construction,
not structural engineering analysis. Camera profiles control the active scene
camera through global collection visibility, not simultaneous per-camera or
per-view-layer exclusions.
