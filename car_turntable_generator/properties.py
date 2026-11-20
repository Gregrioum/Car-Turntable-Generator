"""Scene properties for Car Turntable Generator v2.0."""

import bpy
from .utils import ensure_camera_track_to, sync_camera_target_position


def _poll_camera_object(_self, obj):
    return obj.type == 'CAMERA'


def _poll_non_camera_object(_self, obj):
    return obj.type != 'CAMERA'


def _on_track_to_update(self, _context):
    ensure_camera_track_to(self.render_camera, self.camera_target, enabled=self.use_track_to)


def _on_target_height_update(self, _context):
    sync_camera_target_position(self)


class CTG_SceneProperties(bpy.types.PropertyGroup):
    # --- Rig Objects ---
    anchor_empty: bpy.props.PointerProperty(
        name="Anchor Empty",
        type=bpy.types.Object,
        description="Root Empty that drives the turntable Z-axis rotation",
    )
    render_camera: bpy.props.PointerProperty(
        name="Camera",
        type=bpy.types.Object,
        poll=_poll_camera_object,
        description="Turntable showcase camera",
    )
    camera_target: bpy.props.PointerProperty(
        name="Camera Target",
        type=bpy.types.Object,
        description="Aim target Empty for Camera Track-To constraint",
    )

    # --- Camera Framing ---
    use_track_to: bpy.props.BoolProperty(
        name="Track-To Target",
        description="Keep the camera aimed at the turntable center when moving camera position",
        default=True,
        update=_on_track_to_update,
    )
    target_height: bpy.props.FloatProperty(
        name="Target Z",
        description="Vertical aim height of the camera target above the turntable anchor",
        default=0.80,
        min=-10.0,
        max=10.0,
        soft_min=0.0,
        soft_max=3.0,
        unit='LENGTH',
        update=_on_target_height_update,
    )
    show_camera_settings: bpy.props.BoolProperty(
        name="Camera Settings",
        description="Expand or collapse camera framing controls",
        default=True,
    )

    # --- Model Assignment ---
    car_source_mode: bpy.props.EnumProperty(
        name="Car Source",
        description="Assign either a single Car object/Empty or an entire Collection",
        items=(
            ('OBJECT', "Object", "Assign a single Car object or parent Empty", 'OBJECT_DATA', 0),
            ('COLLECTION', "Collection", "Assign all top-level objects in a Collection without breaking sub-hierarchies", 'OUTLINER_COLLECTION', 1),
        ),
        default='OBJECT',
    )
    car_model: bpy.props.PointerProperty(
        name="Car",
        type=bpy.types.Object,
        poll=_poll_non_camera_object,
        description="Car mesh or root Empty to rotate on the turntable",
    )
    car_collection: bpy.props.PointerProperty(
        name="Car Collection",
        type=bpy.types.Collection,
        description="Collection containing multi-part car meshes to rotate together",
    )
    turntable_model: bpy.props.PointerProperty(
        name="Base",
        type=bpy.types.Object,
        poll=_poll_non_camera_object,
        description="Turntable platform mesh to rotate alongside the car",
    )

    # --- Animation Settings ---
    rotation_angle: bpy.props.FloatProperty(
        name="Angle (°)",
        description="Total Z-axis rotation angle in degrees",
        default=360.0,
        soft_min=0.0,
        soft_max=720.0,
        precision=1,
    )
    direction: bpy.props.EnumProperty(
        name="Direction",
        description="Turntable spin direction around the Z axis",
        items=(
            ('CCW', "CCW", "Rotate counter-clockwise (+Z)"),
            ('CW', "CW", "Rotate clockwise (-Z)"),
        ),
        default='CCW',
    )
    frame_start: bpy.props.IntProperty(
        name="Start",
        description="First frame of the turntable animation",
        default=1,
        min=0,
    )
    frame_length: bpy.props.IntProperty(
        name="Frames",
        description="Total duration of the turntable animation in frames",
        default=360,
        min=2,
        soft_max=1440,
    )
    seamless_loop: bpy.props.BoolProperty(
        name="Seamless Loop",
        description="Place final keyframe at End+1 for full 360° spins to eliminate the duplicate-frame hitch on loop",
        default=True,
    )
    interpolation: bpy.props.EnumProperty(
        name="Motion",
        description="Keyframe interpolation curve for turntable rotation",
        items=(
            ('LINEAR', "Linear (Constant)", "Constant angular speed for smooth continuous loops"),
            ('SINE', "Sine Ease", "Gentle sinusoidal ease-in and ease-out"),
            ('BEZIER', "Bezier Smooth", "Standard smooth Bezier acceleration and deceleration"),
        ),
        default='LINEAR',
    )
    auto_play: bpy.props.BoolProperty(
        name="Auto Play",
        description="Automatically start timeline playback after generating animation",
        default=True,
    )


CLASSES = (
    CTG_SceneProperties,
)
