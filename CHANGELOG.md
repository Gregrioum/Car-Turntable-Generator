# Changelog

All notable changes to **Car Turntable Generator** are documented here.

---

## [2.0.0] - 2026-11-20

### Added
- **Native Blender 4.2+ / 5.x Extension Packaging**: Migrated to a validated modular Extension (`blender_manifest.toml`, `__init__.py`, `properties.py`, `utils.py`, `operators.py`, `ui.py`) cleanly namespaced under `ctg.*` / `CTG_*`.
- **Procedural Turntable Disc (`ctg.create_disc`)**: One-click beveled automotive showroom platform seated cleanly at `Z = 0.0`, with F9 Redo controls for `Radius`, `Height`, `Segments`, and `Top Bevel`.
- **Studio Camera Presets & Track-To Aim**: Added 5 automotive framing presets (`3/4`, `Side`, `Front`, `Low`, `High`), dedicated `Turntable_Target` Empty with toggleable `TRACK_TO` constraint, live **Aim Z** slider, **Focal Length (`mm`)**, **Camera View (`Numpad 0`)**, and **Lock Camera to View**.
- **Collection Mode & Quick Object Pickers**: Added `Object` / `Collection` source toggle so multi-part car assemblies rotate together without breaking internal sub-hierarchies, plus 1-click eyedropper buttons to assign the active viewport object.
- **Bounds Center Alignment**: Added `Bounds Ctr` anchor alignment mode alongside `Align Base` origin alignment.
- **Seamless Loop & Motion Controls**: Added **Seamless Loop** (`frame_end + 1` end keyframe for stutter-free 360° spins), **CCW / CW** direction toggle, **Start Frame**, **Interpolation** selector (`Linear (Constant)`, `Sine Ease`, `Bezier Smooth`), **Auto Play** toggle, and live duration readout (`360f · 15.0s @ 24 fps`).
- **Playback & Non-Destructive Clear Strip**: Added **Play / Pause**, **Reset `0°`**, and **Clear** (unparents models preserving exact world transforms and clears keyframes).
- **Bundled Turntable Mock-Up Model (`assets/Turntable.blend`)**: Included a ready-to-use automotive showroom turntable mock-up `.blend` file (~5.58 m platform under `Turntable` root Empty with stainless steel, chrome, and anti-slip metal materials).

### Fixed
- **Blender 5.0+ Slotted-Action Linear Interpolation**: Replaced legacy `action.fcurves` (removed in Blender 5.0) with a dual-path F-Curve resolver (`bpy_extras.anim_utils.action_get_channelbag_for_slot` + `layers → strips → channelbags` + legacy fallback), restoring true constant-speed linear rotation in Blender 5.x.
- **Seamless 360° Loop Hitch**: Fixed duplicate pose at frame 1 and final frame during looping 360° playback.
- **Edit Mode Rig Creation Crash**: Replaced `bpy.ops.object.empty_add` / `camera_add` with direct `bpy.data` object creation so `Setup Rig` succeeds from any mode and reuses existing rig objects instead of duplicating `.001` empties/cameras.
- **Parented Anchor Alignment Shift**: `Align Anchor` now preserves world matrices of all direct children so aligning an already-parented turntable never displaces the car or base.
- **Playback Toggle Pause Bug**: Regenerating animation while playback is already running no longer pauses playback.
- **Blender 5.2 Unregistration Guards**: Added `getattr(cls, "is_registered", False)` and `hasattr(bpy.types.Scene, "ctg_props")` guards.
- **Narrow N-Panel Label Truncation**: Redesigned panel rows so labels and action buttons remain crisp without ellipsis truncation.

---

## [1.8.10] - 2026-07-11
- Added configurable `Z Rotation (Degrees)` and `Frame Length` scene properties.
- Added `Regenerate Animation` button alongside `Create Animation`.
- Packaged as `Car Turntable_Generator_v1.8.10.zip` (`car_turntable_animator_custom.py`).

---

## [1.6.0] - 2026-07-09
- Initial consolidated 3-step N-Panel release (`Turntable` tab) automating `Turntable_Anchor` empty creation, fixed front-view `Turntable_Camera`, `Align Empty to Turntable`, single-object car/base parenting, and 720-frame / 360° linear Z-rotation animation.
