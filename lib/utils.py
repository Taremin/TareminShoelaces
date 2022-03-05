
def get_settings(context):
    return context.scene.taremin_shoelace


def set_settings(context, value):
    context.scene.taremin_shoelace = value


def get_knot_list(scene, context):
    settings = get_settings(context)
    items = [
        (knot.object.name, knot.object.name, "")
        for i, knot in enumerate(settings.knots) if knot.object is not None
    ]
    return items
