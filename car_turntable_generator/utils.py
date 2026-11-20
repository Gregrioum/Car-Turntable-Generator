"""Shared utilities for Car Turntable Generator v2.0 (Blender 4.2+ & 5.x)."""

import math
import bpy
import bmesh
from mathutils import Vector

try:
    from bpy_extras import anim_utils
except ImportError:
    anim_utils = None


TRACK_TO_CONSTRAINT_NAME = "CTG_TrackTo_Target"


def get_active_collection(context):
    """Return a safe Collection to link newly created rig objects into."""
    if context and getattr(context, "collection", None) is not None:
        return context.collection
    if context and getattr(context, "scene", None) is not None:
        return context.scene.collection
    return bpy.context.scene.collection


def link_object_to_collection(obj, collection):
    """Link object into collection if not already linked."""
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def is_descendant(candidate_child, potential_ancestor):
    """Return True if potential_ancestor is candidate_child or its descendant."""
    cur = potential_ancestor
    visited = set()
    while cur is not None:
        if cur == candidate_child:
            return True
        ptr = cur.as_pointer()
        if ptr in visited:
            break
        visited.add(ptr)
        cur = cur.parent
    return False


def safe_parent_keep_transform(obj, parent_obj):
    """Parent obj to parent_obj while preserving its exact world transform.

    Guards against self-parenting and circular hierarchies.
    """
    if obj is None or parent_obj is None:
        return False
    if obj == parent_obj or is_descendant(obj, parent_obj):
        return False
    if obj.parent == parent_obj:
        return True

    world_mat = obj.matrix_world.copy()
    obj.parent = parent_obj
    obj.matrix_parent_inverse = parent_obj.matrix_world.inverted_safe()
    obj.matrix_world = world_mat
    return True


def safe_unparent_keep_transform(obj):
    """Clear obj.parent while preserving its exact world transform."""
    if obj is None or obj.parent is None:
        return False
    world_mat = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world_mat
    return True


def move_object_preserving_children(obj, new_location):
    """Move obj to new_location while keeping all direct children stationary in world space."""
    if obj is None:
        return
    children_mats = [(child, child.matrix_world.copy()) for child in obj.children]
    obj.location = Vector(new_location)
    depsgraph = bpy.context.evaluated_depsgraph_get() if bpy.context else None
    if depsgraph is not None:
        depsgraph.update()
    for child, world_mat in children_mats:
        child.matrix_parent_inverse = obj.matrix_world.inverted_safe()
        child.matrix_world = world_mat


def collect_target_objects(props):
    """Return list of top-level objects to parent to the turntable anchor.

    In COLLECTION mode, only objects whose parent is None or outside the
    collection are returned so internal car sub-hierarchies remain intact.
    """
    anchor = props.anchor_empty
    target = props.camera_target
    camera = props.render_camera
    excluded = {o for o in (anchor, target, camera) if o is not None}

    result = []
    seen = set()

    def _add(obj):
        if obj is None or obj in excluded:
            return
        if obj.name in seen:
            return
        seen.add(obj.name)
        result.append(obj)

    if props.car_source_mode == 'COLLECTION':
        col = props.car_collection
        if col is not None:
            all_col_objs = list(col.all_objects)
            col_set = set(all_col_objs)
            for obj in all_col_objs:
                if obj in excluded:
                    continue
                if obj.parent is None or obj.parent not in col_set:
                    _add(obj)
    else:
        _add(props.car_model)

    _add(props.turntable_model)
    return result


def compute_world_bounds_bottom_center(objects):
    """Compute world-space (center_x, center_y, min_z) across a sequence of objects."""
    pts = []
    for obj in objects:
        if obj is None:
            continue
        if obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'} and getattr(obj, "bound_box", None):
            mat = obj.matrix_world
            for corner in obj.bound_box:
                pts.append(mat @ Vector(corner))
        else:
            pts.append(obj.matrix_world.translation.copy())

    if not pts:
        return None

    min_x = min(p.x for p in pts)
    max_x = max(p.x for p in pts)
    min_y = min(p.y for p in pts)
    max_y = max(p.y for p in pts)
    min_z = min(p.z for p in pts)
    return Vector(((min_x + max_x) * 0.5, (min_y + max_y) * 0.5, min_z))


def get_action_fcurves(action, anim_data=None):
    """Return iterable of F-Curves compatible with Blender 4.2-4.5 and Blender 5.x Slotted Actions."""
    if action is None:
        return []

    # 1. Official Blender 4.4+ / 5.x helper via bpy_extras.anim_utils
    if anim_utils is not None and hasattr(anim_utils, "action_get_channelbag_for_slot"):
        slot = getattr(anim_data, "action_slot", None) if anim_data is not None else None
        if slot is not None:
            try:
                channelbag = anim_utils.action_get_channelbag_for_slot(action, slot)
                if channelbag is not None and hasattr(channelbag, "fcurves"):
                    return list(channelbag.fcurves)
            except Exception:
                pass

    # 2. Direct layered/slotted action traversal (Blender 4.4+ / 5.x)
    if hasattr(action, "layers"):
        found = []
        for layer in action.layers:
            for strip in getattr(layer, "strips", ()):
                for cbag in getattr(strip, "channelbags", ()):
                    if hasattr(cbag, "fcurves"):
                        found.extend(cbag.fcurves)
        if found:
            return found

    # 3. Legacy Blender 4.2 / 4.3 action.fcurves
    if hasattr(action, "fcurves"):
        return list(action.fcurves)

    return []


def set_rotation_z_interpolation(obj, interpolation_mode):
    """Apply keyframe interpolation to obj's Z-rotation F-Curve on Blender 4.2+ & 5.x."""
    anim_data = getattr(obj, "animation_data", None)
    action = getattr(anim_data, "action", None) if anim_data else None
    if action is None:
        return 0

    fcurves = get_action_fcurves(action, anim_data)
    updated = 0
    for fc in fcurves:
        if fc.data_path == "rotation_euler" and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.interpolation = interpolation_mode
                if interpolation_mode == 'SINE':
                    kp.easing = 'EASE_IN_OUT'
                updated += 1
            fc.update()
    return updated


def ensure_camera_track_to(camera, target, enabled=True):
    """Create or update the Track-To constraint on camera targeting target."""
    if camera is None or camera.type != 'CAMERA':
        return None

    con = camera.constraints.get(TRACK_TO_CONSTRAINT_NAME)
    if target is None:
        if con is not None:
            con.mute = True
        return con

    if con is None:
        con = camera.constraints.new(type='TRACK_TO')
        con.name = TRACK_TO_CONSTRAINT_NAME

    con.target = target
    con.track_axis = 'TRACK_NEGATIVE_Z'
    con.up_axis = 'UP_Y'
    con.mute = not enabled
    return con


def sync_camera_target_position(props):
    """Keep Turntable_Target positioned directly above Turntable_Anchor at target_height."""
    target = props.camera_target
    anchor = props.anchor_empty
    if target is None:
        return

    if anchor is not None:
        if target.parent != anchor:
            target.parent = anchor
            target.matrix_parent_inverse.identity()
        target.location = Vector((0.0, 0.0, props.target_height))
    else:
        target.location.z = props.target_height


def build_turntable_disc_mesh(name, radius=3.0, height=0.14, segments=96, bevel_width=0.025):
    """Generate a sleek beveled automotive showroom turntable platform mesh."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=max(16, int(segments)),
        radius1=radius,
        radius2=radius,
        depth=height,
    )

    # Shift so top face sits cleanly at Z = 0.0 (cars parked at Z = 0 rest directly on top!)
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector((0.0, 0.0, -height * 0.5)))

    # Bevel the top outer rim for crisp studio highlights
    top_edges = [
        e for e in bm.edges
        if all(abs(v.co.z) < 1e-4 for v in e.verts)
    ]
    if top_edges and bevel_width > 0.0:
        safe_bevel = min(bevel_width, height * 0.45, radius * 0.25)
        bmesh.ops.bevel(
            bm,
            geom=top_edges,
            offset=safe_bevel,
            offset_type='OFFSET',
            segments=3,
            profile=0.5,
            affect='EDGES',
            clamp_overlap=True,
        )

    for face in bm.faces:
        face.smooth = True

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return mesh


def get_first_view3d_space(context):
    """Return active or first 3D Viewport space_data."""
    if context and context.space_data and context.space_data.type == 'VIEW_3D':
        return context.space_data
    screen = getattr(context, "screen", None)
    if screen is not None:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        return space
    return None


def format_duration_readout(scene, frame_length):
    """Return formatted playback duration readout such as '360f · 15.0s @ 24fps'."""
    fps = scene.render.fps / max(scene.render.fps_base, 1e-6)
    seconds = frame_length / max(fps, 1e-6)
    fps_str = f"{fps:.0f}" if abs(fps - round(fps)) < 0.01 else f"{fps:.2f}"
    return f"{frame_length}f · {seconds:.1f}s @ {fps_str} fps"


def is_full_revolution(angle_deg):
    """Return True if angle_deg is a non-zero integer multiple of 360 degrees."""
    if abs(angle_deg) < 1e-4:
        return False
    rem = abs(angle_deg) % 360.0
    return rem < 1e-3 or abs(rem - 360.0) < 1e-3
