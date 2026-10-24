bl_info = {
    "name": "Old Shed Builder",
    "author": "ag_tools",
    "version": (1, 1, 0),
    "blender": (4, 3, 0),
    "location": "View3D > Sidebar > Old Shed",
    "description": "Procedural timber shed with geometric deterioration and cinematic visibility",
    "category": "Add Mesh",
}


def register():
    from . import properties, operators, ui, visibility

    properties.register()
    operators.register()
    ui.register()
    visibility.register()


def unregister():
    from . import properties, operators, ui, visibility

    visibility.unregister()
    ui.unregister()
    operators.unregister()
    properties.unregister()
