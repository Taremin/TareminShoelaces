import bpy

from . import utils


class ShoeLacingKnotProps(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(
        type=bpy.types.Object,
        poll=lambda self, object:
            object.type == 'CURVE' and len(object.data.splines) > 0
    )


class ShoeLacingSettings(bpy.types.PropertyGroup):
    knots: bpy.props.CollectionProperty(type=ShoeLacingKnotProps)
    active_knot_index: bpy.props.IntProperty(name='ActiveKnotIndex', options={'HIDDEN'}, default=0)
    knots_folding: bpy.props.BoolProperty(name="expand", default=False)


class VIEW3D_UL_ShoeLacing(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        col = layout.column(align=True)
        row = col.row()
        box = row.box()
        box.scale_x = 0.5
        box.scale_y = 0.5
        box.label(text="", icon='OUTLINER_OB_CURVE')
        row.prop(item, "object", text="", expand=True)


class ShoeLacing_OT_Add(bpy.types.Operator):
    bl_idname = "taremin.add_texture_scale"
    bl_label = "Add Entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = utils.get_settings(context)
        settings.knots.add()
        settings.active_knot_index = len(settings.knots) - 1
        settings.knots[settings.active_knot_index].name = "ShoeLacing"
        return {'FINISHED'}


class ShoeLacing_OT_Remove(bpy.types.Operator):
    bl_idname = "taremin.remove_texture_scale"
    bl_label = "Remove Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return utils.get_settings(context).active_knot_index >= 0

    def execute(self, context):
        settings = utils.get_settings(context)

        settings.knots.remove(settings.active_knot_index)
        max_index = len(settings.knots) - 1
        if settings.active_knot_index > max_index:
            settings.active_knot_index = max_index
        return {'FINISHED'}


class ShoeLacing_OT_Up(bpy.types.Operator):
    bl_idname = "taremin.up_texture_scale"
    bl_label = "Up Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return utils.get_settings(context).active_knot_index > 0

    def execute(self, context):
        settings = utils.get_settings(context)
        index = settings.active_knot_index
        settings.knots.move(index, index - 1)
        settings.active_knot_index = index - 1
        return {'FINISHED'}


class ShoeLacing_OT_Down(bpy.types.Operator):
    bl_idname = "taremin.down_texture_scale"
    bl_label = "Down Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = utils.get_settings(context)
        max_index = len(settings.knots) - 1
        return settings.active_knot_index < max_index

    def execute(self, context):
        settings = utils.get_settings(context)
        index = settings.active_knot_index
        settings.knots.move(index, index + 1)
        settings.active_knot_index = index + 1
        return {'FINISHED'}
