import bpy
import sys
import importlib
import inspect
from pathlib import Path

from .lib import props

# モジュール読み込み
module_names = [
    "library",
    "lacing_base",
    "lacing_bow_tie",
    "lacing_display",
    "lacing_list",
    "props",
    "ops",
    "panel",
]
namespace = globals()
for name in module_names:
    fullname = '{}.{}.{}'.format(__package__, "lib", name)
    if fullname in sys.modules:
        namespace[name] = importlib.reload(sys.modules[fullname])
    else:
        namespace[name] = importlib.import_module(fullname)


# アドオン情報
bl_info = {
    'name': 'Taremin Shoelaces',
    'category': 'Tools',
    'author': 'Taremin',
    'location': 'View 3D > UI > Taremin',
    'description': "",
    'version': (0, 0, 6),
    'blender': (2, 80, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}


classes = [
]
for module in module_names:
    for module_class in [obj for name, obj in inspect.getmembers(namespace[module], inspect.isclass) if hasattr(obj, "bl_rna")]:
        classes.append(module_class)


def register():
    for value in classes:
        bpy.utils.register_class(value)
    bpy.types.Scene.taremin_shoelace = bpy.props.PointerProperty(type=props.ShoeLacingSettings)


def unregister():
    for value in classes:
        bpy.utils.unregister_class(value)
    del bpy.types.Scene.taremin_shoelace
    Path(__file__).touch()


if __name__ == '__main__':
    register()
