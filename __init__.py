
bl_info = {
    "name": "Set Origin Tool",
    "author": "Abbos Mirzaev",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Set Origin Tool (N-Panel), Ctrl+Alt+X (Pie Menu)",
    "description": "Advanced origin tools with 3x3 grid, standard origin functions, and a pie menu",
    "category": "Object",
}

import bpy
from bpy.types import Menu, Operator, Panel
from bpy.props import StringProperty
from mathutils import Vector, Matrix


# -- PIE MENU START --

class PIE_MT_set_origin(Menu):
    bl_idname = "PIE_MT_set_origin"
    bl_label = "Set Origin"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("object.origin_set_any_mode", text="Geometry → Origin", icon='TRANSFORM_ORIGINS').type = 'GEOMETRY_ORIGIN'
        pie.operator("object.origin_set_any_mode", text="Origin → Geometry", icon='SNAP_PEEL_OBJECT').type = 'ORIGIN_GEOMETRY'
        pie.operator("object.origin_set_to_bottom", text="Origin → Bottom", icon='TRIA_DOWN')
        pie.operator("object.origin_set_to_selection", text="Origin → Selection", icon='RESTRICT_SELECT_OFF')
        pie.operator("object.origin_set_any_mode", text="Origin → Cursor", icon='PIVOT_CURSOR').type = 'ORIGIN_CURSOR'
        pie.operator("object.origin_set_any_mode", text="Origin → Mass", icon='SNAP_FACE_CENTER').type = 'ORIGIN_CENTER_OF_MASS'
        pie.separator()
        pie.operator("object.origin_set_any_mode", text="Origin → Volume", icon='SNAP_FACE_CENTER').type = 'ORIGIN_CENTER_OF_VOLUME'


class OBJECT_OT_set_origin_to_selection(Operator):
    bl_idname = "object.origin_set_to_selection"
    bl_label = "Origin To Selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        org_mode = context.active_object.mode if context.active_object else 'OBJECT'
        saved_location = context.scene.cursor.location.copy()
        bpy.ops.view3d.snap_cursor_to_selected()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.mode_set(mode=org_mode)
        context.scene.cursor.location = saved_location
        self.report({'INFO'}, "Snapped origin to selection.")
        return {'FINISHED'}


class OBJECT_OT_set_origin_to_bottom(Operator):
    bl_idname = "object.origin_set_to_bottom"
    bl_label = "Origin To Bottom"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_obj = context.active_object
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        count = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                min_z = min((v.co.z for v in obj.data.vertices), default=0)
                for v in obj.data.vertices:
                    v.co.z -= min_z
                obj.location.z += min_z
                count += 1
        context.view_layer.objects.active = active_obj
        self.report({'INFO'}, f"Moved origins of {count} objects to bottom.")
        return {'FINISHED'}


class OBJECT_OT_set_origin_any_mode(Operator):
    bl_idname = "object.origin_set_any_mode"
    bl_label = "Set Origin"
    bl_options = {'REGISTER', 'UNDO'}

    type: StringProperty()

    def execute(self, context):
        org_mode = context.active_object.mode if context.active_object else 'OBJECT'
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.origin_set(type=self.type)
        bpy.ops.object.mode_set(mode=org_mode)
        self.report({'INFO'}, f"Origin set: {self.type}")
        return {'FINISHED'}

# -- PIE MENU END --


class OBJECT_OT_set_origin(Operator):
    bl_idname = "object.set_origin"
    bl_label = "Set Origin Grid"
    bl_options = {'REGISTER', 'UNDO'}

    mode: StringProperty()
    x: StringProperty()
    y: StringProperty()
    z: StringProperty()

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type not in {'MESH', 'CURVE'}:
                continue
            bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            coords = list(zip(*bbox))

            def get(axis, pos):
                idx = "XYZ".index(axis)
                if pos == "MIN": return min(coords[idx])
                if pos == "MAX": return max(coords[idx])
                return (min(coords[idx]) + max(coords[idx])) / 2

            target = Vector((get("X", self.x), get("Y", self.y), get("Z", self.z)))
            local_target = obj.matrix_world.inverted() @ target
            obj.data.transform(Matrix.Translation(-local_target))
            obj.matrix_world.translation = target
            self.report({'INFO'}, f"Origin set to {self.x}, {self.y}, {self.z}")
        return {'FINISHED'}


class OBJECT_PT_set_origin_tool(Panel):
    bl_label = "Set Origin Tool"
    bl_idname = "OBJECT_PT_set_origin_tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Set Origin"

    def draw_grid(self, layout, z, label):
        col = layout.column(align=True)
        col.label(text=label)
        symbols = {
            ("MIN", "MAX"): "↖", ("CENTER", "MAX"): "↑", ("MAX", "MAX"): "↗",
            ("MIN", "CENTER"): "←", ("CENTER", "CENTER"): "•", ("MAX", "CENTER"): "→",
            ("MIN", "MIN"): "↙", ("CENTER", "MIN"): "↓", ("MAX", "MIN"): "↘"
        }
        for y in ["MAX", "CENTER", "MIN"]:
            row = col.row(align=True)
            for x in ["MIN", "CENTER", "MAX"]:
                op = row.operator("object.set_origin", text=symbols[(x, y)])
                op.mode = "CUSTOM"
                op.x = x
                op.y = y
                op.z = z

    def draw(self, context):
        layout = self.layout
        self.draw_grid(layout.box(), "MAX", "Top - XY Axis")
        self.draw_grid(layout.box(), "CENTER", "Middle - XY Axis")
        self.draw_grid(layout.box(), "MIN", "Bottom - XY Axis")

        layout.separator()
        layout.label(text="Quick Origin Tools:")
        col = layout.column(align=True)
        col.operator("object.origin_set_any_mode", text="Geometry → Origin").type = 'GEOMETRY_ORIGIN'
        col.operator("object.origin_set_any_mode", text="Origin → Geometry").type = 'ORIGIN_GEOMETRY'
        col.operator("object.origin_set_any_mode", text="Origin → Cursor").type = 'ORIGIN_CURSOR'
        col.operator("object.origin_set_any_mode", text="Origin → Mass").type = 'ORIGIN_CENTER_OF_MASS'
        col.operator("object.origin_set_any_mode", text="Origin → Volume").type = 'ORIGIN_CENTER_OF_VOLUME'
        col.operator("object.origin_set_to_selection", text="Origin → Selection")
        col.operator("object.origin_set_to_bottom", text="Origin → Bottom")


classes = (
    OBJECT_OT_set_origin,
    OBJECT_PT_set_origin_tool,
    PIE_MT_set_origin,
    OBJECT_OT_set_origin_to_selection,
    OBJECT_OT_set_origin_to_bottom,
    OBJECT_OT_set_origin_any_mode,
)

addon_keymaps = []

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new("wm.call_menu_pie", type='Z', value='PRESS', ctrl=True, alt=True)
        kmi.properties.name = "PIE_MT_set_origin"
        addon_keymaps.append((km, kmi))

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
