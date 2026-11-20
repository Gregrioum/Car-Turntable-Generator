"""Car Turntable Generator v2.0 - Blender 4.2+ / 5.x Extension."""

import bpy

from . import operators, properties, ui


_CLASSES = (
    *properties.CLASSES,
    *operators.CLASSES,
    *ui.CLASSES,
)


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.ctg_props = bpy.props.PointerProperty(type=properties.CTG_SceneProperties)


def unregister():
    if hasattr(bpy.types.Scene, "ctg_props"):
        del bpy.types.Scene.ctg_props

    for cls in reversed(_CLASSES):
        if getattr(cls, "is_registered", False):
            try:
                bpy.utils.unregister_class(cls)
            except RuntimeError:
                pass
