# Old Shed Builder — parameter guide

For **version 1.1.0**, Blender 4.3+. Open the 3D View sidebar with **N**, then choose **Old Shed**. This guide follows the panel order and describes the actual generated geometry and materials.

## Contents

- [Using the builder and choosing an update](#using-the-builder-and-choosing-an-update)
- [Dimensions](#dimensions)
- [Framing](#framing)
- [Cladding, random gaps, and crooked boards](#cladding-random-gaps-and-crooked-boards)
- [Roof](#roof)
- [Wood deformation](#wood-deformation)
- [Materials](#materials)
- [Door and windows](#door-and-windows)
- [Light leakage](#light-leakage)
- [Cinematic visibility](#cinematic-visibility)
- [UVs and image textures](#uvs-and-image-textures)
- [Suggested starting points](#suggested-starting-points)
- [Troubleshooting](#troubleshooting)

Distances below are **meters**: `0.001` = 1 mm, `0.01` = 1 cm, `0.1` = 10 cm. Blender may display length fields in your scene's chosen units. Angles are degrees. Unless marked otherwise, strength and probability controls run from **0 to 1**; a probability of `0.1` means 10% before any master-strength scaling. Probabilities are independent decisions, so a small shed will not necessarily contain exactly that percentage of damaged boards.

Defaults below are the initial settings, **not** the Small Dilapidated Shed preset. The generator validates combinations of dimensions, so two values individually inside their ranges can still be incompatible.

## Using the builder and choosing an update

Changing a geometry or material field does **not** immediately rebuild the shed. Change several fields, return to **Object Mode**, then press **Update Parameters** or **Generate / Rebuild**. Visibility toggles are the exception: they apply immediately.

| Control | What it does and when to use it |
| --- | --- |
| Active shed | Chooses the generated root Empty to edit and loads its saved settings into the panel. Move or rotate this root to position the complete shed. |
| Load Selected Shed | Select any generated shed component, then click this to load its owning shed. Useful in scenes with multiple sheds. |
| New Shed | Generates an independent shed using the current panel settings. It does not reset the settings first. |
| Generate / Rebuild | Creates a shed if none is active; otherwise requests a full rebuild. It ignores the Update scope selector but still respects Preserve User Edits. |
| Update scope | Selects what Update Parameters may replace; see the table below. |
| Update Parameters | Applies the current settings using the selected scope. Incompatible changes report an error rather than silently leaving dependent parts mismatched. |
| Preserve User Edits | On by default. Retains edited meshes, UVs, transforms, material assignments/graphs, and other detected authored changes. An edited door/window fixture preserves its complete assembly. Preserved pieces may retain old dimensions or UVs after a rebuild. |
| Randomize Weathering | Advances both Seed and Leak seed, then rebuilds. Keeps the control strengths, but produces another deterministic arrangement of deformation, damage, board colors, and leakage. |
| Reset Weathering | Sets Variation and global Leakage to 0, disables wall leakage overrides, sets Aging to 0.12 and Roughness to 0.6, and clears Dirt, Water, Broken, Loose, Missing, and Leak loose. Rebuilds immediately. **It does not clear Plank gap, Gap randomizer, Crooked, Color variation, or Broken glass.** |
| Small Dilapidated Shed | Replaces the panel settings with a complete preset and rebuilds the active shed. This also resets dimensions/openings; it is not merely a weathering-strength adjustment. Use New Shed first if you want to keep a separate original. |
| Bake to Editable Meshes | Creates a separate evaluated mesh/material snapshot, retaining UVs. The baked collection starts hidden. Hide the generated collection and enable the baked collection when ready to use the snapshot. This button does not bake textures to images. |

| Scope | Supported changes |
| --- | --- |
| All components | Any parameter. Use for dimensions, openings, shared plank settings, wood deformation, and Seed. |
| Framing only | Window header height and Collar ties. Other structural dimensions affect additional components and need All components. |
| Wall cladding only | Gap randomizer, Gap random weight, Crooked, and all global/per-wall Light leakage settings. Plank width, Plank thickness, and Plank gap still need All components because other surfaces use them. |
| Materials only | Aging, Roughness, Grain, Dirt, Water, and Color variation. Keeps meshes and UV packing. |

Use All components when changing settings from several categories together. An older shed without version 1.1 UV metadata needs one full rebuild before partial updates.

Preservation detects changes, including shared material changes that can mark many objects as edited. Check the reported retained-object count if a parameter appears ineffective. Disable preservation only when you want to replace those edits. A deleted generated board returns on rebuilding; deletion is not saved as a generator instruction. Save your `.blend` before major experiments.

## Dimensions

The shed is centered in X/Y. **Front = negative Y**, **Rear = positive Y**, **Left = negative X**, **Right = positive X**. Width runs along X; length and the roof ridge run along Y. These names stay attached to the shed when you rotate its root.

| Parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Width | 3.2 m; 1.5–15 | Outside-to-outside width of structural framing. Cladding and overhang extend beyond it. Increasing width also increases the roof span and ridge rise at the same pitch. |
| Length | 4 m; 1.5–20 | Outside-to-outside framing length. Longer sheds acquire more framing bays and longer siding/roof boards. Opening centers remain at their entered distances; they do not automatically recenter. |
| Wall height | 2.4 m; 1.5–6 | Finished floor to the **top of the double top plate**, not ground to ridge. Raising it adds wall courses and more room above openings. |
| Foundation height | 0.18 m; 0.05–0.8 | Height of the six foundation piers. Raises the joists and everything above them. It does not add more piers as the footprint grows. |

Finished floor elevation is `Foundation height + Joist depth + Floor thickness`. Defaults give `0.18 + 0.145 + 0.028 = 0.353 m`. The top of the wall is then 2.753 m above the generator's ground datum; the roof extends higher.

## Framing

| Parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Stud width | 0.045 m; 0.025–0.12 | Narrow timber dimension along a wall. Also supplies joist/rafter thickness and **door header height**. Increasing it makes several structural parts heavier and reduces available room beside openings. |
| Stud depth | 0.095 m; 0.06–0.25 | Timber dimension through the wall. Must be at least twice Stud width to fit corner backing. For example, Stud width 0.06 needs Stud depth at least 0.12. |
| Stud spacing | 0.4 m; 0.2–1.2 | Nominal spacing of ordinary studs. Smaller values add supports and shorten unsupported siding spans. Corners and openings add their own members, so the final layout is not a single uninterrupted grid. |
| Window header height | 0.16 m; 0.08–0.4 | Vertical size of the header above each window. Larger values need more room between the rough opening and top plates. The door instead uses Stud width. |
| Joist depth | 0.145 m; 0.08–0.4 | Vertical height of floor joists and perimeter rim members. Raises the finished floor. Joist **thickness** remains Stud width. |
| Joist spacing | 0.4 m; 0.2–1 | Nominal floor-support spacing along the length. The generator divides the available span into equal bays, so actual spacing can be smaller. More joists also provide more floorboard deformation supports. |
| Floor thickness | 0.028 m; 0.015–0.06 | Floorboard thickness. Raises the finished floor and changes the thickness-relative limits on floorboard bow/cup. |

These dimensions create visible construction geometry; they are not engineering load calculations.

## Cladding, random gaps, and crooked boards

| Parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Plank width | 0.18 m; 0.08–0.35 | Vertical height of a normal siding course. Also sets nominal floorboard and roof-board widths; those layouts adjust widths to fit their spans. Narrower planks make more objects and more seams. |
| Plank thickness | 0.022 m; 0.012–0.06 | Thickness of siding and roof covering boards. Floorboards use Floor thickness; roof sheathing uses its own fixed 18 mm thickness. Thicker planks permit larger bow/cup before their safety caps apply. |
| Plank gap | 0.004 m; 0–0.05 | Base construction spacing between siding courses and between floorboards. Leakage can add siding spacing; the gap randomizer can reduce siding gaps below this base. Roof skins use their own fitted seams. |
| Gap randomizer | 0; 0–1 | Blends ordinary siding spacing with a random value between zero and the calculated maximum. At 0, the ordinary leakage-spacing formula applies; at 1, fully randomized spacing applies. Intermediate values blend the two. |
| Gap random weight | 1; 0.05–8 | Bias of the random gap distribution. Below 1 favors small gaps, 1 gives a uniform distribution, above 1 favors larger gaps. It affects leakage variation even with Gap randomizer at 0. |
| Crooked | 0; 0–1 | Rotates siding within the wall plane using available clearance above/below it. At 0 it adds no tilt; at 1 it uses the solver's full safe angle in a seeded direction. It can shift a board slightly vertically to balance the space. |

### How gap controls work together

The maximum available gap depends on **Plank gap**, **Leak gap**, **Leakage**, **Leak variation**, and occasional **Large gaps** events. Gap randomizer and Gap random weight choose how that available space is used; they do not define a new distance in meters.

Ignoring a large-gap event, the maximum is:

`Plank gap + Leak gap × effective Leakage × (1 + Leak variation)`

Effective Leakage is the wall's amount, multiplied by 1.8 if Dramatic is on. Gaps are capped at 35% of Plank width normally, or 65% with Dramatic.

With defaults, the maximum is `0.004 + 0.006 × 0.35 × 1.5 = 0.00715 m`, about **7.15 mm**. Set Gap randomizer to 1 to sample between zero and that maximum. At weight 0.5, the average random fraction is about one-third of the maximum; at 1 it is one-half; at 2 it is two-thirds. Individual gaps still vary.

Internally, the weighted fraction is `random^(1 / weight)`. At Gap randomizer 0, ordinary spacing is the base gap plus a varied leakage addition, rather than a zero-to-maximum sample. At Leakage 0, full gap randomization still varies the base Plank gap. If both base and leakage-added gap are zero, the randomizer cannot create space by itself. **Leak seed** chooses the gap pattern.

### Getting visible crookedness

Crooked needs room. Start with Gap randomizer 1, Gap random weight 1, Crooked 0.7, and a few millimeters of base/additional gap. Increase gap distances if long boards barely tilt. A few millimeters over several meters produces only a small visible angle.

The fitting pass considers neighboring siding silhouettes, openings, and roof/floor bounds. It leaves a small clearance, allows up to 5 mm fitting inset at each end, and limits rotation to 12°. Boards are fitted sequentially, so not every board can use both neighboring gaps completely. Missing boards can free more space. Preserved edited siding acts as a fixed neighbor.

Crooked is independent of **Variation** and affects wall siding only. It does not tilt studs, rafters, floorboards, or door assemblies. It is a local fitting operation, not a collision solver for every object in the scene.

## Roof

| Parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Roof pitch | 30°; 10–60 | Slope above horizontal. Higher values raise the ridge and steepen both roof planes. Pitch, Stud depth, and Rafter depth must allow a valid birdsmouth bearing notch. |
| Overhang | 0.25 m; 0.05–0.8 | Horizontal extension beyond the wall footprint at eaves and gable ends. Increases the roof footprint without enlarging the room. |
| Rafter depth | 0.12 m; 0.06–0.3 | Deep dimension of the sloped rafters. Increase it if the bearing notch is too deep for the chosen pitch/wall depth. Rafter thickness uses Stud width. |
| Rafter spacing | 0.6 m; 0.25–1.2 | Nominal separation of rafter pairs along the length. Actual bays are fitted evenly, with additional fly rafters at the gable overhangs. |
| Ridge thickness | 0.045 m; 0.025–0.12 | Thickness across the central ridge board. Changes the meeting region of the two roof slopes. |
| Collar ties | On | Adds horizontal members between paired rafters near the upper roof. Turn off for a more open interior silhouette. |
| Sheathing | On | Adds a solid 18 mm plank underlayer beneath the outer roof boards. Turning it off removes that layer; outer roof boards remain. |

Roof Covering visibility hides **both** the exterior boards and sheathing. Roof Framing visibility controls rafters/ridge/ties separately. Wall leakage controls do not punch holes in the roof.

## Wood deformation

These controls act on generated subdivided **planks**, including siding, floorboards, roof boards/sheathing, and plank parts of fixtures. Box/prism structural timbers such as studs and rafters do not receive this plank deformation pass. Supported sections constrain the deformation, so identical strengths can look different on boards with different support spacing.

| Parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Bow | 0.012 m; 0–0.06 | Smooth lengthwise displacement away from the undeformed board surface. Randomly signed and strongest between supports. Before Variation is applied, capped at 65% of board thickness. Raising it beyond this cap has no further effect on that board. |
| Twist | 3°; 0–12 | Rotation of the cross-section along a plank. Produces a warped face rather than a whole-board sideways tilt. Randomly signed and reduced at supports. |
| Cup | 0.003 m; 0–0.02 | Curvature across the plank width. Before Variation, capped at 35% of thickness. Makes edges depart from the center surface. |
| Edge | 0.002 m; 0–0.008 | Smooth irregularity along long edges, capped at 2.5% of plank width. Adds a worn outline rather than surface texture. |
| Split | 0.07 m; 0–0.3 | Maximum depth of a geometric V-shaped split at one local end. Capped at 14% of original board length, scaled by Variation and randomness, then limited to 10% of remaining length after breakage. Zero removes these splits. |
| Broken | 0.035; 0–1 | Chance of a broken plank. Actual probability is Broken × Variation. An affected plank randomly loses material from its local start, local end, or both. It is a frequency, not the amount removed. |
| Max broken length (%) | 28%; 0–95 | Upper bound on combined length removed by breakage from both ends, relative to original board length. Also scaled by Variation and a random severity. Zero disables this break damage even when Broken is high. |
| Loose | 0.04; 0–1 | Chance of an end lifting away from its supports. Actual ordinary probability is Loose × Variation. Wall leakage can independently force loose siding. |
| Separation | 0.018 m; 0–0.15 | Maximum lift used for detached plank ends, tapering from the remaining fixed support region. Ordinary loose boards scale this by Variation. Also interacts with Leak separation; see Light leakage. |
| Seed | 17; nonnegative integer | Selects repeatable wood deformation, breakage, and board-color choices. Same settings and seed reproduce the same generated result. Changing layout can change board identities and therefore their random choices. |
| Variation | 0.7; 0–1 | Master strength for ordinary plank deformation and damage: scales bow, twist, cup, edge, split, break probability/severity, and ordinary loose probability/lift. Zero removes these effects. It does **not** turn off Crooked, leakage-driven detachment, procedural material weathering, or Color variation. |

For example, Broken 0.5 with Variation 0.6 damages approximately 30% of eligible planks. Max broken length 40% at that Variation allows at most 24% of original length to be assigned to breakage. A two-meter board therefore loses at most 0.48 m across both ends, usually less because severity is randomized and the ends are jagged. A both-end break splits that budget between the ends; it does not give each end the entire budget. **Split is separate** and can cut additional material inward.

The distinction between three easily confused controls is useful: **Crooked** tilts siding in its wall plane; **Bow/Twist/Cup** warp its shape; **Loose/Separation** lift an end out from the wall or support plane.

## Materials

All six controls range from 0 to 1 and support **Materials only** updates. Use Material Preview or Rendered shading to judge them; Solid shading does not show the full shader. These controls affect the generated wood shader; metal, glass, and concrete have their own materials.

| Parameter | Default | Meaning and practical effect |
| --- | --- | --- |
| Aging | 0.7 | Blends warm brown timber toward weathered gray/green-gray. Does not add broken geometry. Lower it for fresher-looking wood. |
| Roughness | 0.82 | Principled surface roughness. Lower values create sharper reflections; higher values give a matte surface. It does not change the amount of geometric damage. |
| Grain | 0.65 | Strength of fine fiber **bump relief**. Does not change grain scale or remove the grain's color pattern when set to zero. |
| Dirt | 0.35 | Dark brown buildup near the base. Fades from its set strength at finished-floor height to zero about one meter above the floor. |
| Water | 0.45 | Strength of dark, elongated water-stain patterns. This colors the wood; it does not simulate water or automatically lower Roughness. Patterns use the shed root's coordinates, so rotating the entire shed also rotates their reference. |
| Color variation | 0.25 | Strength of deterministic per-object tint multiplication. Raise for more board-to-board contrast; lower for a more uniform palette. The main Seed selects the board tints. |

Material controls remain active at Variation 0. To make timber visually fresh as well as geometrically straight, also reduce Aging, Dirt, and Water. Editing a shared generated material manually can cause many boards to be preserved during later updates.

## Door and windows

The Door, Window A, and Window B each have their own opening settings. Fixture geometry fits **inside** the rough opening, so the finished clear opening is smaller than the entered dimensions.

| Parameter | Defaults | Meaning and practical effect |
| --- | --- | --- |
| Enabled | On for all three | Includes that opening and its fixture. Disabling it closes the opening with normal wall framing/siding on rebuild. |
| Wall | Door: Front; A: Left; B: Right | Assigns the opening to one of the four named walls. Several openings can share a wall if their framing fits without overlap. |
| Center from wall start | Door: 1.5 m; A: 1.5 m; B: 2.6 m | Opening center measured from the negative X endpoint for Front/Rear, or negative Y endpoint for Left/Right. Range 0–20 m, but the actual opening must fit its wall. This is **not always the left edge as viewed from outside**. |
| Rough opening width | Door: 0.85 m; windows: 0.8 m | Width before jambs/frame, range 0.3–8 m. Increasing it needs more room for king/jack studs on both sides. |
| Rough opening height | Door: 1.9 m; windows: 0.7 m | Height before fixture framing, range 0.3–5 m. The opening plus header must fit below the double top plate. |
| Sill above floor | Windows: 1 m | Height of the window rough-opening bottom above finished floor, range 0–5 m. Needs at least twice Stud width beneath it for the sill/bottom plate arrangement. The door begins at the floor and has no exposed sill-height control. |
| Door hinge side | Left | Left or Right **as viewed from outside** that wall. Mirrors hinge position, handle, and brace handing. |
| Door angle | 18° | Opening angle, −170° to 170°. Zero closes the leaf; positive opens outward for either hinge side; negative swings inward. Large angles may intersect nearby geometry; there is no fixture swing collision check. |
| Glass | On | Adds solid glass to both windows. Off leaves the wooden window frames and open pane spaces. |
| Broken glass | On | Replaces one designated pane in each window with shard geometry. This is a switch, not a random break percentage. Has no effect when Glass is off. |
| Shutters | On | Adds the modeled wooden shutters to both windows. This version has no separate shutter-angle slider. |

To center an opening, use Width / 2 on Front or Rear, and Length / 2 on Left or Right. For the default shed, those centers are 1.6 m and 2 m respectively.

Each side of an opening needs corner clearance of at least `Stud depth + 3 × Stud width`. Two openings also need enough separation for their surrounding framing. Vertically, `Sill + Opening height + Header height` must be no greater than `Wall height − 2 × Stud width`. The door's Header height is Stud width; a window uses Window header height.

## Light leakage

Leakage changes **wall siding geometry**: actual gaps, absent pieces, and lifted ends allow light through. It does not add lights, emit light, or make wood transparent. Use an exterior light/sky and a suitable render engine such as Cycles to illuminate the interior.

| Global parameter | Default; range | Meaning and practical effect |
| --- | --- | --- |
| Leakage | 0.35; 0–1 | Master amount for the global siding leakage settings. Scales added gap distances, large-gap events, missing/loose frequency, and leakage separation. Does not remove the base Plank gap or independent wood deformation at zero. |
| Leak gap | 0.006 m; 0–0.08 | Nominal extra gap before multiplication by Leakage and gap variation. Despite the override label “Average added gap,” the final mean also depends on the gap weight/randomizer and caps. |
| Leak variation | 0.5; 0–1 | Spread of the leakage-added gap around its nominal amount in ordinary spacing, and part of the maximum in randomized spacing. Zero removes this spread but does not disable Gap randomizer. |
| Large gaps | 0.04; 0–1 | Probability of an extra-wide course gap, scaled by effective Leakage. On such an event, adds 22% of Plank width × effective Leakage before the final gap cap/randomizer blend. |
| Missing | 0.025; 0–1 | Probability of omitting a generated siding segment, multiplied by effective Leakage and capped at 90%. Around windows/doors, a course may contain several separately tested segments. Does not remove framing. |
| Leak loose | 0.06; 0–1 | Probability of forcing a siding end loose, multiplied by effective Leakage and capped at 90%. Independent of the ordinary Loose × Variation decision. |
| Leak separation | 0.018 m; 0–0.15 | Leakage-specific detached-end lift. The effective leakage value is scaled by the wall amount and capped at 0.15 m; the deformation pass uses the larger of that result and ordinary Separation. |
| Leak seed | 41; nonnegative integer | Selects gap sizes, larger-gap events, missing segments, and leakage-loose choices. Independent of the main wood Seed. |
| Dramatic | Off | Multiplies leakage amount by 1.8, including wall overrides, and raises the maximum siding gap from 35% to 65% of Plank width. Use for strong shafts of light or severe neglect. |

A leakage-forced loose board uses its selected separation **without Variation scaling**. On a board that becomes loose only through the ordinary Loose control, the selected separation is multiplied by Variation. Thus zero Variation does not guarantee that leakage-loose siding lies flat. To prevent detachment, set both Loose and Leak loose to zero, including any wall overrides.

### Per-wall overrides

Each Front/Rear/Left/Right box has **Override global leakage**. Off uses the global settings. On replaces all seven leakage fields for that wall; the values do not add to the global ones and are not multiplied by the global Leakage slider.

| Override field | Corresponding global control | Initial override value |
| --- | --- | --- |
| Leakage amount | Leakage | 0.35 |
| Average added gap | Leak gap | 0.006 m |
| Gap variation | Leak variation | 0.5 |
| Larger gap probability | Large gaps | 0.04 |
| Missing board frequency | Missing | 0.025 |
| Loose board frequency | Leak loose | 0.06 |
| Detached end separation | Leak separation | 0.018 m |

The overrides have the same ranges and behavior as their global counterparts. They still share Plank gap, Gap randomizer, Gap random weight, Crooked, Leak seed, and Dramatic. For example, to admit sunlight mainly through the rear wall, keep global Leakage low, enable Rear's override, and raise its amount/gap/missing values. An active override can keep leaking even when global Leakage is zero.

## Cinematic visibility

Each row has separate **Viewport** and **Render** switches. Enabled means shown. Changes are immediate and do not rebuild meshes or alter UVs. Render-hidden geometry is excluded from rendering, including its shadows, which is useful for opening a wall to the camera and light.

| Row | Affected components |
| --- | --- |
| Front / Rear / Left / Right | All generated layers of that wall: framing, siding, and fixtures. |
| Roof | All roof framing and both roof skins. |
| Roof Covering | Exterior roof boards and underlying sheathing together. |
| Roof Framing | Rafters, ridge, and collar ties. |
| Floor Foundation | Floorboards, floor joists/rims, and foundation piers. |
| Cladding | Siding across all four walls. Does not hide roof covering. |
| Framing | Wall framing, including gable studs. Floor and roof framing use their own rows. |
| Fixtures | Door and window assemblies across all walls. |

The switches combine. A hidden Front wall remains hidden even if Cladding is enabled. Likewise, enabling Roof Covering cannot reveal it while Roof is disabled. Viewport and Render are independent; a viewport cutaway can still render as a closed building if you only switch the viewport column.

**Profile name** names the current visibility setup. **Save Visibility for Active Camera** stores both columns and associates the profile with the scene's active camera, if one exists. Saving the same name replaces that named profile. Saving another name for the same camera transfers its camera association to the new profile; the old named profile remains manually restorable.

**Restore: [name]** applies a saved setup manually. **Follow active camera** automatically applies a bound profile when the active camera changes, including camera-marker animation. A camera without a bound profile does not supply a new visibility setup. These profiles use global collection visibility, not simultaneous independent per-camera or per-view-layer visibility.

## UVs and image textures

UV creation is automatic; version 1.1 has no UV size, rotation, or packing sliders.

![Actual generated connected timber UV net](images/board_uv_net.svg)

Each rectangular timber uses a connected **front → top → back → bottom** strip, with left/right end caps attached to the front face, as in the supplied reference. Board length runs horizontally. Notched or irregular cut faces may need small extra islands. Planks unwrap before deformation, so UVs follow the deformed surface from their original board layout.

**UVMap** is the painting/baking atlas. Nets fit within 0–1 without overlap within each group. Each group has a shared material and uniform generated texel scale:

| Atlas/material group | Contents |
| --- | --- |
| Cladding | All wall siding |
| Framing | Studs, plates, headers, floor joists, rafters, ridge, ties |
| RoofSheathing | Roof underlayer |
| DoorsWindows | Wooden door/window parts, shutters, braces |
| Floorboards | Floor planks |
| RoofCovering | Outer roof planks |
| Glass | A separate space/material for each pane; shards share their original pane's space |
| Metal / Concrete | Hardware and piers, each in its own group |

Different groups reuse 0–1 intentionally because they use separate materials/textures. To inspect an entire atlas, select the meshes in that group and inspect their UVMap together in the UV Editor. To paint a custom image, create/select an Image Texture in the group's material and use **UVMap** as its coordinates. The supplied shader contains a labeled UVMap node to connect for this purpose; it does not automatically create or connect a paint image.

**WoodGrain** is a second UV layer for procedural grain coordinates. It can extend outside 0–1 and is not the packed painting atlas. Keep it if retaining the generated grain shader.

A full geometry rebuild can repack generated charts, so finish major layout changes before painting an atlas. Preserved manual UV edits remain untouched and reserve their occupied rectangles; new boards may pack at a smaller scale around them. Materials-only updates and visibility changes do not repack. Bake to Editable Meshes retains both UV layers but does not create texture images.

## Suggested starting points

These are starting recipes, not additional built-in presets. Use All components when combining categories. Disable wall overrides unless explicitly included; otherwise they can mask the global settings.

### Straight, minimally weathered construction

Click Reset Weathering, then set Crooked 0 and Gap randomizer 0. Use Plank gap 0.002–0.004 m for deliberate construction seams. Lower Color variation if the boards still look too varied; turn Broken glass off for intact windows. Reset Weathering leaves the underlying deformation strengths available, so increasing Variation later brings those effects back.

### Subtle uneven siding

Try Plank gap 0.003 m, Leakage 0.2, Leak gap 0.005 m, Gap randomizer 1, Gap random weight 0.6, and Crooked 0.4. Set Missing and Leak loose to 0 while tuning spacing. This favors mostly tight seams with occasional visible clearance. Add breakage separately after the spacing looks right.

### Clearly crooked, neglected siding

Try Plank gap 0.006 m, Leakage 0.6, Leak gap 0.012 m, Gap randomizer 1, Gap random weight 1.5, and Crooked 0.9. Use Variation 0.7, Broken 0.12, and Max broken length 35%. Long boards may still tilt only slightly because their ends use up the available gap quickly.

### Strong rear-wall light leaks

Keep global Leakage around 0.1. Enable Rear's override and try amount 0.8, added gap 0.015 m, larger-gap probability 0.1, missing frequency 0.08, and loose frequency 0.12. Place an external light behind that wall. Start with Dramatic off; enable it only if the openings need to be more pronounced.

### Diagnose unwanted wall gaps

For a straight, unbroken siding baseline, set Plank gap 0, Variation 0, Crooked 0, global Leakage 0, and disable every wall override. Disable preservation only if you intend to regenerate manually edited boards. Window/door openings remain intentional openings; a swung door or broken glass will still admit light. This recipe diagnoses siding, not a completely watertight building.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Values changed but the shed did not | Click Update Parameters in Object Mode. Use All components for mixed changes. Check the retained-object count and Preserve User Edits. |
| Partial update says a full rebuild is required | A changed setting affects other components, or the shed predates the UV upgrade. Use Generate / Rebuild. |
| Broken affects few or no boards | Check Variation, Max broken length, and how many eligible planks exist. Broken is a probability, not a guaranteed count. |
| Increasing Bow/Cup has no visible effect | Thickness-relative limits may already be reached. Supports also constrain deformation. |
| Crooked does little | Neighbor/edge clearance may be tiny, especially on long boards. Increase available gaps moderately and inspect a broadside view. |
| Gaps remain at Leakage 0 | Check base Plank gap, wall overrides, Broken/Split/Loose, Crooked, and preserved edits. |
| Setting Variation to 0 does not make everything new | Materials, Crooked, leakage, and Broken glass are independent. See Reset Weathering and the starting recipes. |
| Opening will not fit | Move its center inward, reduce width/height, lower the window sill, or increase the wall dimensions. Leave room for corner, king/jack, header, and top-plate framing. |
| Rafter-depth validation error | Increase Rafter depth or reduce Roof pitch/Stud depth so the birdsmouth notch leaves sufficient timber. |
| UVs seem to overlap | Select one atlas group and UVMap, not all materials at once or WoodGrain. Preserved manual UV layouts may also differ from regenerated ones. |
| A wall is hidden but still renders | Check the Render column separately from Viewport. Check whether an active-camera profile is restoring older visibility. |
| No visible light beams | First confirm physical openings and exterior illumination. Beams visible in air also require atmosphere/volume scattering; leakage alone illuminates receiving surfaces. |

For installation, source downloads, and validation details, return to the [README](../README.md). The guide describes version 1.1.0 behavior; later versions may extend these controls.
