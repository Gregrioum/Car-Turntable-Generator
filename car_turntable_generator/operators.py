"""Operators for Car Turntable Generator v2.0."""

import math
import bpy
from mathutils import Vector

from .utils import (
    build_turntable_disc_mesh,
    collect_target_objects,
    compute_world_bounds_bottom_center,
    ensure_camera_track_to,
    get_active_collection,
    get_first_view3d_space,
    is_full_revolution,
    link_object_to_collection,
    move_object_preserving_children,
    safe_parent_keep_transform,
    safe_unparent_keep_transform,
    set_rotation_z_interpolation,
    sync_camera_target_position,
)


CAMERA_PRESETS = {
    'THREE_QUARTER': {
        "label": "3/4 Hero",
        "offset": Vector((6.8, -7.2, 1.75)),
        "lens": 55.0,
        "target_z": 0.80,
    },
    'SIDE': {
        "label": "Side Profile",
        "offset": Vector((0.0, -10.5, 1.35)),
        "lens": 85.0,
        "target_z": 0.85,
    },
    'FRONT': {
        "label": "Front",
        "offset": Vector((9.5, 0.0, 1.35)),
        "lens": 85.0,
        "target_z": 0.80,
    },
    'LOW': {
        "label": "Low Hero",
        "offset": Vector((6.2, -6.5, 0.90)),
        "lens": 50.0,
        "target_z": 0.75,
    },
    'TOP_34': {
        "label": "High 3/4",
        "offset": Vector((6.5, -7.0, 4.20)),
        "lens": 55.0,
        "target_z": 0.65,
    },
}


class CTG_OT_setup_turntable(bpy.types.Operator):
    """Create (or restore) the Turntable Anchor Empty, Aim Target, and Studio Camera"""
    bl_idname = "ctg.setup_turntable"
    bl_label = "Setup Turntable Rig"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.ctg_props
        col = get_active_collection(context)

        created = []

        # 1. Anchor Empty
        anchor = props.anchor_empty
        if anchor is None or anchor.name not in bpy.data.objects:
            anchor = bpy.data.objects.new("Turntable_Anchor", None)
            anchor.empty_display_type = 'PLAIN_AXES'
            anchor.empty_display_size = 1.5
            anchor.location = Vector((0.0, 0.0, 0.0))
            link_object_to_collection(anchor, col)
            props.anchor_empty = anchor
            created.append("Anchor")
        else:
            link_object_to_collection(anchor, col)

        # 2. Aim Target Empty (child of Anchor along rotation axis)
        target = props.camera_target
        if target is None or target.name not in bpy.data.objects:
            target = bpy.data.objects.new("Turntable_Target", None)
            target.empty_display_type = 'SPHERE'
            target.empty_display_size = 0.25
            link_object_to_collection(target, col)
            props.camera_target = target
            created.append("Target")
        else:
            link_object_to_collection(target, col)

        sync_camera_target_position(props)

        # 3. Studio Camera
        cam = props.render_camera
        if cam is None or cam.name not in bpy.data.objects or cam.type != 'CAMERA':
            cam_data = bpy.data.cameras.new("Turntable_Camera")
            cam_data.lens = 55.0
            cam_data.clip_start = 0.1
            cam_data.clip_end = 1000.0
            cam = bpy.data.objects.new("Turntable_Camera", cam_data)
            cam.location = anchor.matrix_world.translation + Vector((0.0, -10.0, 2.0))
            cam.rotation_euler = (math.radians(80.0), 0.0, 0.0)
            link_object_to_collection(cam, col)
            props.render_camera = cam
            created.append("Camera")
        else:
            link_object_to_collection(cam, col)

        ensure_camera_track_to(cam, target, enabled=props.use_track_to)
        context.scene.camera = cam

        if created:
            self.report({'INFO'}, f"Turntable rig ready ({', '.join(created)} created).")
        else:
            self.report({'INFO'}, "Existing turntable rig verified and set as active camera.")
        return {'FINISHED'}


class CTG_OT_create_disc(bpy.types.Operator):
    """Generate a beveled automotive showroom turntable platform mesh at the anchor"""
    bl_idname = "ctg.create_disc"
    bl_label = "Add Turntable Disc"
    bl_options = {'REGISTER', 'UNDO'}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=3.0,
        min=0.5,
        max=20.0,
        unit='LENGTH',
    )
    height: bpy.props.FloatProperty(
        name="Height",
        default=0.14,
        min=0.02,
        max=2.0,
        unit='LENGTH',
    )
    segments: bpy.props.IntProperty(
        name="Segments",
        default=96,
        min=16,
        max=256,
    )
    bevel_width: bpy.props.FloatProperty(
        name="Top Bevel",
        default=0.025,
        min=0.0,
        max=0.25,
        unit='LENGTH',
    )

    def execute(self, context):
        props = context.scene.ctg_props
        col = get_active_collection(context)

        mesh = build_turntable_disc_mesh(
            "Turntable_Platform_Mesh",
            radius=self.radius,
            height=self.height,
            segments=self.segments,
            bevel_width=self.bevel_width,
        )
        disc_obj = bpy.data.objects.new("Turntable_Platform", mesh)
        if props.anchor_empty is not None:
            disc_obj.location = props.anchor_empty.matrix_world.translation.copy()
        else:
            disc_obj.location = Vector((0.0, 0.0, 0.0))

        link_object_to_collection(disc_obj, col)
        props.turntable_model = disc_obj

        self.report({'INFO'}, f"Created turntable disc (R={self.radius:.2f}m, H={self.height:.2f}m).")
        return {'FINISHED'}


class CTG_OT_assign_selected(bpy.types.Operator):
    """Assign the currently active viewport object as Car or Turntable Base"""
    bl_idname = "ctg.assign_selected"
    bl_label = "Pick Active Object"
    bl_options = {'REGISTER', 'UNDO'}

    slot: bpy.props.EnumProperty(
        name="Target Slot",
        items=(
            ('CAR', "Car", "Assign active object as Car"),
            ('TURNTABLE', "Base", "Assign active object as Turntable Base"),
        ),
        default='CAR',
    )

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'WARNING'}, "No active object selected in the 3D Viewport.")
            return {'CANCELLED'}
        if obj.type == 'CAMERA':
            self.report({'WARNING'}, "Cannot assign a Camera as a Car or Turntable Base.")
            return {'CANCELLED'}

        props = context.scene.ctg_props
        if obj == props.anchor_empty or obj == props.camera_target:
            self.report({'WARNING'}, "Select your Car or Turntable object, not the Rig Empty.")
            return {'CANCELLED'}

        if self.slot == 'CAR':
            props.car_source_mode = 'OBJECT'
            props.car_model = obj
            self.report({'INFO'}, f"Assigned Car: {obj.name}")
        else:
            props.turntable_model = obj
            self.report({'INFO'}, f"Assigned Base: {obj.name}")
        return {'FINISHED'}


class CTG_OT_align_anchor(bpy.types.Operator):
    """Safely align the Anchor Empty to the turntable origin or bounding-box center without shifting parented models"""
    bl_idname = "ctg.align_anchor"
    bl_label = "Align Anchor"
    bl_options = {'REGISTER', 'UNDO'}

    mode: bpy.props.EnumProperty(
        name="Alignment Mode",
        items=(
            ('ORIGIN', "Base Origin", "Move Anchor to the Turntable Base world origin"),
            ('BOUNDS', "Bounds Center", "Move Anchor to the XY center and bottom Z of assigned models"),
        ),
        default='ORIGIN',
    )

    def execute(self, context):
        props = context.scene.ctg_props
        anchor = props.anchor_empty
        if anchor is None:
            self.report({'WARNING'}, "Anchor Empty not found. Click 'Setup Turntable Rig' first.")
            return {'CANCELLED'}

        if self.mode == 'ORIGIN':
            target_obj = props.turntable_model or props.car_model
            if target_obj is None:
                self.report({'WARNING'}, "Assign a Turntable Base or Car object first.")
                return {'CANCELLED'}
            new_loc = target_obj.matrix_world.translation.copy()
            label = f"{target_obj.name} origin"
        else:
            objs = []
            if props.turntable_model is not None:
                objs.append(props.turntable_model)
            else:
                objs.extend(collect_target_objects(props))
            if not objs:
                self.report({'WARNING'}, "Assign a Turntable Base or Car model/collection first.")
                return {'CANCELLED'}
            new_loc = compute_world_bounds_bottom_center(objs)
            if new_loc is None:
                self.report({'WARNING'}, "Could not compute bounding box for assigned models.")
                return {'CANCELLED'}
            label = "world bounds center"

        move_object_preserving_children(anchor, new_loc)
        sync_camera_target_position(props)
        self.report({'INFO'}, f"Anchor aligned to {label}.")
        return {'FINISHED'}


class CTG_OT_camera_preset(bpy.types.Operator):
    """Apply an automotive studio camera framing preset around the turntable anchor"""
    bl_idname = "ctg.camera_preset"
    bl_label = "Camera Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=(
            ('THREE_QUARTER', "3/4", "Classic automotive 3/4 hero angle (55mm)"),
            ('SIDE', "Side", "Clean orthographic-style side profile (85mm)"),
            ('FRONT', "Front", "Straight-on front elevation (85mm)"),
            ('LOW', "Low", "Dramatic low-angle hero shot (50mm)"),
            ('TOP_34', "High", "Elevated 3/4 overview angle (55mm)"),
        ),
        default='THREE_QUARTER',
    )

    def execute(self, context):
        props = context.scene.ctg_props
        cam = props.render_camera
        if cam is None or cam.type != 'CAMERA':
            self.report({'WARNING'}, "Setup Turntable Rig first to create a Camera.")
            return {'CANCELLED'}

        spec = CAMERA_PRESETS[self.preset]
        base_loc = (
            props.anchor_empty.matrix_world.translation.copy()
            if props.anchor_empty is not None
            else Vector((0.0, 0.0, 0.0))
        )

        props.target_height = spec["target_z"]
        props.use_track_to = True
        sync_camera_target_position(props)
        ensure_camera_track_to(cam, props.camera_target, enabled=True)

        cam.location = base_loc + spec["offset"]
        cam.data.lens = spec["lens"]
        context.scene.camera = cam

        self.report({'INFO'}, f"Applied '{spec['label']}' camera preset ({int(spec['lens'])}mm).")
        return {'FINISHED'}


class CTG_OT_toggle_camera_view(bpy.types.Operator):
    """Switch the active 3D Viewport into or out of the Turntable Camera view"""
    bl_idname = "ctg.toggle_camera_view"
    bl_label = "Camera View"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.ctg_props
        if props.render_camera is not None:
            context.scene.camera = props.render_camera

        space = get_first_view3d_space(context)
        if space is None or space.region_3d is None:
            self.report({'WARNING'}, "No 3D Viewport found.")
            return {'CANCELLED'}

        r3d = space.region_3d
        r3d.view_perspective = 'PERSP' if r3d.view_perspective == 'CAMERA' else 'CAMERA'
        return {'FINISHED'}


class CTG_OT_generate_animation(bpy.types.Operator):
    """Parent assigned Car & Base to the Anchor Empty and generate/update turntable rotation keyframes"""
    bl_idname = "ctg.generate_animation"
    bl_label = "Generate / Update Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.ctg_props
        anchor = props.anchor_empty

        if anchor is None or anchor.name not in bpy.data.objects:
            self.report({'WARNING'}, "Anchor Empty not found. Click 'Setup Turntable Rig' first.")
            return {'CANCELLED'}

        targets = collect_target_objects(props)
        parented_count = 0
        for obj in targets:
            if safe_parent_keep_transform(obj, anchor):
                parented_count += 1

        frame_start = props.frame_start
        frame_length = props.frame_length
        frame_end = frame_start + frame_length - 1

        # Seamless loop places final 360° keyframe on frame_end + 1 so frame_end != frame_start pose
        use_seamless_offset = props.seamless_loop and is_full_revolution(props.rotation_angle)
        end_key_frame = frame_end + 1 if use_seamless_offset else frame_end

        sign = 1.0 if props.direction == 'CCW' else -1.0
        target_angle_rad = math.radians(props.rotation_angle * sign)

        scene = context.scene
        scene.frame_start = frame_start
        scene.frame_end = frame_end
        scene.frame_current = frame_start

        anchor.animation_data_clear()
        anchor.rotation_mode = 'XYZ'

        anchor.rotation_euler[2] = 0.0
        anchor.keyframe_insert(data_path="rotation_euler", index=2, frame=frame_start)

        anchor.rotation_euler[2] = target_angle_rad
        anchor.keyframe_insert(data_path="rotation_euler", index=2, frame=end_key_frame)

        set_rotation_z_interpolation(anchor, props.interpolation)

        # Reset viewport to start pose cleanly
        scene.frame_set(frame_start)

        if props.auto_play and context.screen and not context.screen.is_animation_playing:
            try:
                bpy.ops.screen.animation_play()
            except RuntimeError:
                pass

        loop_note = " (seamless loop)" if use_seamless_offset else ""
        dir_str = "CCW" if sign > 0 else "CW"
        self.report(
            {'INFO'},
            f"Turntable ready: {props.rotation_angle:.0f}° {dir_str} over {frame_length}f{loop_note} ({parented_count} target(s)).",
        )
        return {'FINISHED'}


class CTG_OT_toggle_playback(bpy.types.Operator):
    """Play or pause turntable timeline playback"""
    bl_idname = "ctg.toggle_playback"
    bl_label = "Play / Pause"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            bpy.ops.screen.animation_play()
        except RuntimeError:
            self.report({'WARNING'}, "Timeline playback is unavailable in the current context.")
            return {'CANCELLED'}
        return {'FINISHED'}


class CTG_OT_reset_rotation(bpy.types.Operator):
    """Pause playback and jump back to the start frame (0°)"""
    bl_idname = "ctg.reset_rotation"
    bl_label = "Reset 0°"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.ctg_props
        if context.screen and context.screen.is_animation_playing:
            try:
                bpy.ops.screen.animation_cancel(restore_frame=False)
            except RuntimeError:
                pass

        context.scene.frame_set(props.frame_start)
        if props.anchor_empty is not None and not props.anchor_empty.animation_data:
            props.anchor_empty.rotation_euler[2] = 0.0
        self.report({'INFO'}, f"Reset to frame {props.frame_start} (0°).")
        return {'FINISHED'}


class CTG_OT_clear_rig(bpy.types.Operator):
    """Unparent Car & Base (preserving world transforms) and clear Anchor keyframes"""
    bl_idname = "ctg.clear_rig"
    bl_label = "Unparent & Clear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.ctg_props
        anchor = props.anchor_empty
        if anchor is None:
            self.report({'WARNING'}, "No Anchor Empty assigned.")
            return {'CANCELLED'}

        if context.screen and context.screen.is_animation_playing:
            try:
                bpy.ops.screen.animation_cancel(restore_frame=False)
            except RuntimeError:
                pass

        context.scene.frame_set(props.frame_start)

        unparented = 0
        for child in list(anchor.children):
            if child == props.camera_target:
                continue
            if safe_unparent_keep_transform(child):
                unparented += 1

        anchor.animation_data_clear()
        anchor.rotation_euler[2] = 0.0

        self.report({'INFO'}, f"Cleared turntable animation and unparented {unparented} object(s).")
        return {'FINISHED'}


CLASSES = (
    CTG_OT_setup_turntable,
    CTG_OT_create_disc,
    CTG_OT_assign_selected,
    CTG_OT_align_anchor,
    CTG_OT_camera_preset,
    CTG_OT_toggle_camera_view,
    CTG_OT_generate_animation,
    CTG_OT_toggle_playback,
    CTG_OT_reset_rotation,
    CTG_OT_clear_rig,
)
