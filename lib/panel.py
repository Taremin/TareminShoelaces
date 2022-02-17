import bpy

from . import ops, props, utils


class VIEW3D_PT_TareminShoeLacesPanel(bpy.types.Panel):
    bl_label = 'Taremin Shoe Laces'
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        errors = []
        settings = utils.get_settings(context)

        err, result = ops.OBJECT_OT_TareminShoeLacesCreateCurve.check_mesh_geometry(
            obj)
        if err:
            errors.append(result)

        if len(errors) > 0:
            row = layout.box()
        for err in errors:
            col = row.column(align=True)
            col.label(text=err, icon='ERROR')

        row = layout.row()
        row.prop(
            settings, "knots_folding",
            icon="TRIA_RIGHT" if settings.knots_folding else "TRIA_DOWN",
            icon_only=True
        )
        row.label(text="Knots")

        if not settings.knots_folding:
            # Knots
            row = layout.row()
            col = row.column()
            col.template_list(
                "VIEW3D_UL_ShoeLacing",
                "",
                settings,
                "knots",
                settings,
                "active_knot_index",
                type="DEFAULT"
            )
            col = row.column(align=True)
            col.operator(props.ShoeLacing_OT_Add.bl_idname, text="", icon="ADD")
            col.operator(props.ShoeLacing_OT_Remove.bl_idname, text="", icon="REMOVE")
            col.separator()
            col.operator(props.ShoeLacing_OT_Up.bl_idname, text="", icon="TRIA_UP")
            col.operator(props.ShoeLacing_OT_Down.bl_idname, text="", icon="TRIA_DOWN")

        # Operator
        col = layout.column(align=True)
        operator_row = col.row(align=True)
        operator_row.operator(ops.OBJECT_OT_TareminShoeLacesCreateCurve.bl_idname)
