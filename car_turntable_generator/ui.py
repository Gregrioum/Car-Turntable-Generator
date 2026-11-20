"""N-Panel UI for Car Turntable Generator v2.0."""

import bpy
from .utils import format_duration_readout, get_first_view3d_space


class CTG_PT_main_panel(bpy.types.Panel):
    bl_label = "Car Turntable v2.0"
    bl_idname = "CTG_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Turntable"

    def draw(self, context):
        layout = self.layout
        props = context.scene.ctg_props

        # =====================================================================
        # 1. SETUP SCENE & CAMERA
        # =====================================================================
        layout.label(text="1. Scene & Camera Rig:")
        row = layout.row(align=True)
        row.operator("ctg.setup_turntable", text="Setup Rig", icon='OUTLINER_OB_EMPTY')
        row.operator("ctg.create_disc", text="Add Disc", icon='MESH_CYLINDER')

        cam = props.render_camera
        if cam is not None and cam.type == 'CAMERA':
            box = layout.box()
            header = box.row(align=True)
            title_sub = header.row(align=True)
            title_sub.alignment = 'LEFT'
            title_sub.prop(
                props,
                "show_camera_settings",
                text="Camera",
                icon='TRIA_DOWN' if props.show_camera_settings else 'TRIA_RIGHT',
                emboss=False,
            )
            header.separator()
            btn_sub = header.row(align=True)
            btn_sub.alignment = 'RIGHT'
            space = get_first_view3d_space(context)
            in_cam_view = bool(
                space and space.region_3d and space.region_3d.view_perspective == 'CAMERA'
            )
            btn_sub.operator(
                "ctg.toggle_camera_view",
                text="",
                icon='VIEW_CAMERA',
                depress=in_cam_view,
            )
            if space is not None:
                btn_sub.prop(space, "lock_camera", text="", icon='LOCKED' if space.lock_camera else 'UNLOCKED')
            btn_sub.prop(props, "use_track_to", text="", icon='CON_TRACKTO')

            if props.show_camera_settings:
                # Studio camera angle presets
                preset_row = box.row(align=True)
                for preset_id, label in (
                    ('THREE_QUARTER', "3/4"),
                    ('SIDE', "Side"),
                    ('FRONT', "Front"),
                    ('LOW', "Low"),
                    ('TOP_34', "High"),
                ):
                    op = preset_row.operator("ctg.camera_preset", text=label)
                    op.preset = preset_id

                col = box.column(align=True)
                col.prop(cam, "location", text="")

                if props.use_track_to:
                    aim_row = box.row(align=True)
                    aim_row.prop(props, "target_height", text="Aim Z")
                    aim_row.prop(cam.data, "lens", text="Lens")
                else:
                    rot_col = box.column(align=True)
                    rot_col.prop(cam, "rotation_euler", text="")
                    box.prop(cam.data, "lens", text="Focal Length")

        layout.separator(factor=0.6)

        # =====================================================================
        # 2. ASSIGN MODELS
        # =====================================================================
        layout.label(text="2. Assign Models:")
        box = layout.box()

        mode_row = box.row(align=True)
        mode_row.prop(props, "car_source_mode", expand=True)

        if props.car_source_mode == 'OBJECT':
            car_split = box.split(factor=0.24, align=True)
            car_split.label(text="Car:")
            car_row = car_split.row(align=True)
            car_row.prop(props, "car_model", text="", icon='AUTO')
            op = car_row.operator("ctg.assign_selected", text="", icon='EYEDROPPER')
            op.slot = 'CAR'
        else:
            col_split = box.split(factor=0.24, align=True)
            col_split.label(text="Car:")
            col_split.prop(props, "car_collection", text="", icon='OUTLINER_COLLECTION')

        base_split = box.split(factor=0.24, align=True)
        base_split.label(text="Base:")
        base_row = base_split.row(align=True)
        base_row.prop(props, "turntable_model", text="", icon='MESH_CYLINDER')
        op = base_row.operator("ctg.assign_selected", text="", icon='EYEDROPPER')
        op.slot = 'TURNTABLE'

        align_row = box.row(align=True)
        op_orig = align_row.operator("ctg.align_anchor", text="Align Base", icon='SNAP_PEEL_OBJECT')
        op_orig.mode = 'ORIGIN'
        op_bnds = align_row.operator("ctg.align_anchor", text="Bounds Ctr", icon='PIVOT_BOUNDBOX')
        op_bnds.mode = 'BOUNDS'

        layout.separator(factor=0.6)

        # =====================================================================
        # 3. ANIMATION SETTINGS
        # =====================================================================
        layout.label(text="3. Animation Settings:")
        box = layout.box()

        ang_split = box.split(factor=0.58, align=True)
        ang_split.prop(props, "rotation_angle", text="Angle")
        dir_sub = ang_split.row(align=True)
        dir_sub.prop(props, "direction", expand=True)

        frame_row = box.row(align=True)
        frame_row.prop(props, "frame_start", text="Start")
        frame_row.prop(props, "frame_length", text="Frames")

        box.prop(props, "interpolation", text="")

        opt_row = box.row(align=True)
        opt_row.prop(props, "seamless_loop", text="Seamless Loop")
        opt_row.prop(props, "auto_play", text="Auto Play")

        info_row = box.row()
        info_row.alignment = 'CENTER'
        info_row.label(text=format_duration_readout(context.scene, props.frame_length), icon='TIME')

        layout.separator(factor=0.6)

        # =====================================================================
        # 4. GENERATE & PLAYBACK
        # =====================================================================
        layout.label(text="4. Generate & Playback:")
        gen_row = layout.row()
        gen_row.scale_y = 1.25
        has_anim = bool(props.anchor_empty and props.anchor_empty.animation_data)
        gen_row.operator(
            "ctg.generate_animation",
            text="Update Animation" if has_anim else "Generate Animation",
            icon='FILE_REFRESH' if has_anim else 'PLAY',
        )

        is_playing = bool(context.screen and context.screen.is_animation_playing)
        ctrl_row = layout.row(align=True)
        ctrl_row.operator(
            "ctg.toggle_playback",
            text="Pause" if is_playing else "Play",
            icon='PAUSE' if is_playing else 'PLAY',
        )
        ctrl_row.operator("ctg.reset_rotation", text="0°", icon='REW')
        ctrl_row.operator("ctg.clear_rig", text="Clear", icon='UNLINKED')


CLASSES = (
    CTG_PT_main_panel,
)
