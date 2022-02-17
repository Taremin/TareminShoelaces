import bpy
import bmesh
import mathutils
import math
import os
from . import library, ops


def append(context, path, obj_name):
    path = os.path.join(os.path.dirname(__file__), "..", path)

    with context.blend_data.libraries.load(path) as (data_from, data_to):
        data_to.objects = [obj_name]

    return data_to.objects[0]


class ShoeLacing:
    label = "ShoeLacing(Base)"

    def __init__(self, obj, vertices2d, settings: ops.ShoeLacingProps):
        self.base_obj = obj
        self.vertices2d = vertices2d
        self.settings = settings

    def create_curve_points(self, context):
        pass

    def immutable(self, vec):
        return vec.copy().freeze()

    # Center
    #
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------O-------O-------+
    #     |       |\      |       |
    #     |       | \_ _ _|_______|__ Center
    #     |       |       |       |
    #     +-------O-------O-------+
    #     |       |\      |       |
    #     |       | \_ _ _|_______|__ Center
    #     |       |       |       |
    #     +-------O-------O-------+
    #              \       \
    #               \_______\______ Center
    #
    def calc_center_points(self, y, is_reversed):
        verts = self.base_obj.data.vertices
        vertices2d = self.vertices2d
        width, height = vertices2d.shape
        points = []

        is_simple_curve = self.settings.is_simple_curve
        use_center_offset = self.settings.use_center_offset
        side_handle_length = self.settings.side_handle_length
        center_handle_length_ratio = self.settings.center_handle_length_ratio

        r = range(1, width-1)

        if is_simple_curve:
            r = [1]
        elif is_reversed:
            r = reversed(r)

        if width < 3:
            return points

        for x in r:
            v_current = verts[vertices2d[x][y]]
            v_prev = verts[vertices2d[x-1][y]]
            v_next = verts[vertices2d[x+1][y]]

            co = v_current.co
            normal = v_current.normal

            if is_simple_curve:
                t = [verts[vertices2d[x][y]] for x in range(width)]
                co, normal = self.calc_center_co_by_length(t)
                if co is None:
                    raise ValueError("Can't calculate center coordinate")
                v_next = verts[vertices2d[width - 1][y]]

            if use_center_offset:
                co += normal * side_handle_length

            if is_reversed:
                v_prev, v_next = v_next, v_prev

            handle_left = co + \
                self.calc_center_handle(co, v_next, v_prev,
                                        center_handle_length_ratio)
            handle_right = co + \
                self.calc_center_handle(co, v_prev, v_next,
                                        center_handle_length_ratio)

            points.insert(0, {
                "type": "MIDDLE",
                "co": self.immutable(co),
                "handle_left": self.immutable(handle_left),
                "handle_right": self.immutable(handle_right),
            })

        return points

    # SIDE
    #
    #     O-------+-------+-------O
    #     |\      |       |       |\
    #     | \_____|_______|_______|_\____ SIDE
    #     |       |       |       |
    #     O-------+-------+-------O
    #     |\      |       |       |\
    #     | \_____|_______|_______|_\____ SIDE
    #     |       |       |       |
    #     O-------+-------+-------O
    #     |\      |       |       |\
    #     | \_____|_______|_______|_\____ SIDE
    #     |       |       |       |
    #     O-------+-------+-------O
    #      \                       \
    #       \_______________________\____ SIDE
    #
    # is_reversed: 基本的には前から後ろに制御点がいくが、一番上だけは紐を前に出すために後ろから前になる
    def calc_side_points(self, left, right, left_x, right_x, y, is_reversed):
        verts = self.base_obj.data.vertices
        vertices2d = self.vertices2d
        side_handle_length = self.settings.side_handle_length

        for target, x, sign in [(left, left_x, 1.0), (right, right_x, -1.0)]:
            p = verts[vertices2d[x][y]]
            norm = p.normal.normalized() * side_handle_length * sign

            co = p.co
            handle_left = co + norm
            handle_right = co - norm

            if is_reversed:
                handle_left, handle_right = handle_right, handle_left

            target.append({
                "type": "SIDE",
                "co": self.immutable(co),
                "handle_left": self.immutable(handle_left),
                "handle_right": self.immutable(handle_right),
            })

    def calc_center_handle(self, center, side1, side2, length):
        co = center
        if getattr(center, "co", None) is not None:
            co = center.co

        return (side1.co - side2.co) * (
            (
                (side1.co - co).length /
                (side1.co - side2.co).length
            ) * length
        )

    # CROSS
    #
    #     +-------+-------+-------+
    #     |       O       O       |
    #     |       |\  O   |\      |
    #     |       O_\__\__O_\_____|______ CROSS
    #     +-------+-------+-------+
    #     |       O       O       |
    #     |       |\  O   |\      |
    #     |       O_\__\__O_\_____|______ CROSS
    #     +-------+-------+-------+
    #     |       O       O       |
    #     |       |\  O   |\      |
    #     |       O_\__\__O_\_____|______ CROSS
    #     +-------+-------+-------+
    #
    def calc_cross_points(self, left, right, from_x, from_y, to_x, to_y):
        vertices2d = self.vertices2d
        data = self.base_obj.data
        verts = data.vertices

        settings = self.settings
        is_simple_curve = settings.is_simple_curve
        center_length = settings.bevel_depth
        center_handle_length_ratio = settings.center_handle_length_ratio

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(data)

        # Center
        lines = []
        for to_x, from_x in [(to_x, from_x), (from_x, to_x)]:
            bpy.ops.mesh.select_all(action='DESELECT')
            bm.verts.ensure_lookup_table()
            v1 = bm.verts[vertices2d[from_x][from_y]]
            v2 = bm.verts[vertices2d[to_x][to_y]]
            v1.select = v2.select = True
            bpy.ops.mesh.vert_connect_path()

            tmp = self.get_selected_verts(v1, v2, None, [])
            lines.append(tmp)

        line_verts = lines[1]
        center = None
        bm.verts.ensure_lookup_table()

        # 対角線を辺で結び中心点を見つける
        for i in range(1, len(line_verts) - 1):
            tmp = []
            other_count = 0
            v = bm.verts[line_verts[i]]
            for edge in v.link_edges:
                ov = edge.other_vert(v)
                if ov.index in lines[0]:
                    tmp.append(ov)
                elif ov.index not in lines[1]:
                    other_count += 1
            if len(tmp) == 2 and (len(v.link_edges) == 6 or other_count == 0):
                i1 = lines[0].index(tmp[0].index)
                i2 = lines[0].index(tmp[1].index)
                if i1 > i2:
                    i1, i2 = i2, i1
                lines[0].insert(i2, v.index)
                center = v
                break

        """
            # 中心点に近い点を無視する
            for line in lines:
                for idx in reversed(range(len(line))):
                    v = bm.verts[line[idx]]
                    if v != center and (v.co - center.co).length < 0.5: # TODO: 0.5 = ignore distance
                        line.pop(idx)
            """

        if is_simple_curve:
            lines[0] = [lines[0].pop(0), center.index, lines[0].pop()]
            lines[1] = [lines[1].pop(0), center.index, lines[1].pop()]

        # 対角線をカーブで結ぶ
        # 紐同士が交差するため、衝突しないように位置調整
        front_or_back = 1 if to_y % 2 == 0 else -1
        for target, line, sign in [(left, lines[0], 1), (right, lines[1], -1)]:
            for idx in range(1, len(line) - 1):
                v_current = bm.verts[line[idx]]
                v_prev = bm.verts[line[idx-1]]
                v_next = bm.verts[line[idx+1]]

                co = v_current.co + \
                    (v_current.normal * center_length * sign * front_or_back)
                handle_left = co + \
                    self.calc_center_handle(
                        v_current, v_prev, v_next, center_handle_length_ratio)
                handle_right = co + \
                    self.calc_center_handle(
                        v_current, v_next, v_prev, center_handle_length_ratio)

                if sign < 0:
                    handle_left, handle_right = handle_right, handle_left

                target.append({
                    "type": "MIDDLE",
                    "co": self.immutable(co),
                    "handle_left": self.immutable(handle_left),
                    "handle_right": self.immutable(handle_right),
                })

    def calc_center_co_by_length(self, verts):
        total_length = 0.0

        for i in range(len(verts) - 1):
            v = verts[i]
            v_next = verts[i + 1]
            total_length += (v.co - v_next.co).length

        center_length = total_length / 2.0
        current_length = 0.0

        for i in range(len(verts) - 1):
            v = verts[i]
            v_next = verts[i + 1]
            edge_length = (v.co - v_next.co).length
            tmp_length = current_length + edge_length

            if tmp_length >= center_length:
                sub = center_length - current_length
                r1 = v.normal * (sub / edge_length)
                r2 = v_next.normal * (1 - sub / edge_length)
                return (
                    v.co + (v_next.co - v.co).normalized() * sub,
                    r1 + r2
                )

            current_length = tmp_length

        return (None, None)

    def get_selected_verts(self, v1, v2, prev=None, result=[]):
        if len(result) == 0:
            result.append(v1.index)
        if v1 == v2:
            return result

        for edge in v1.link_edges:
            ov = edge.other_vert(v1)
            if prev is not None and ov.index == prev.index:
                continue
            if ov.select:
                result.append(ov.index)
                return self.get_selected_verts(ov, v2, v1, result)

        return result

    # Top
    #                      _________________ KNOT
    #                     /
    #        ____________/__________________ TOP (SIDE)
    #       /           /           /
    #      /           /           /
    #     O-------O--XXX--O-------O
    #     |       |\      |\      |
    #     |       | \_____|_\_____|____ TOP (CENTER)
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #
    def get_top_points(self, context):
        vertices2d = self.vertices2d
        width, height = vertices2d.shape
        verts = self.base_obj.data.vertices
        settings = self.settings

        y = height-1
        x1 = (y % 2) * -1 % width
        x2 = (height % 2) * -1 % width

        # Side
        left = []
        right = []
        self.calc_side_points(left, right, x1, x2, y, True)

        # Center
        is_reversed = height % 2 != 0
        center = self.calc_center_points(y, is_reversed)

        asset = library.knots[int(settings.knot_type)]
        knots = ops.get_knot_list(context.scene, context)
        is_local_object = (asset[1] == "")
        if asset[1] is None or (is_local_object and len(knots) == 0):
            return (left + center, right, True)

        if is_local_object:
            obj = bpy.data.objects[settings.knot]
            is_reverse_spline_left = settings.is_reverse_spline_left
            is_reverse_spline_right = settings.is_reverse_spline_right
            spline_index_left = settings.sil
            spline_index_right = settings.sir
        else:
            obj = append(context, asset[1], asset[2])  # TODO: obj消さなくて平気？
            is_reverse_spline_left = asset[5]
            is_reverse_spline_right = asset[6]
            spline_index_left = asset[3]
            spline_index_right = asset[4]
        center_left = [bp for bp in obj.data.splines[spline_index_left].bezier_points]
        center_right = [bp for bp in obj.data.splines[spline_index_right].bezier_points]

        if is_reverse_spline_left:
            center_left = list(reversed(center_left))
        if is_reverse_spline_right:
            center_right = list(reversed(center_right))

        # Zを法線方向に, XYを上の辺に沿って回転
        xvec = mathutils.Vector((1, 0, 0)).freeze()
        vx1 = verts[vertices2d[x1][y]].co
        vx2 = verts[vertices2d[x2][y]].co

        if is_reversed:
            vx1, vx2 = vx2, vx1
        else:
            center_left, center_right = list(
                reversed(center_right)), list(reversed(center_left))

        xy_sub = vx1 - vx2
        xy_rot_diff = xy_sub.rotation_difference(xvec)
        if xy_rot_diff.y != 0.0:
            xy_sub = vx2 - vx1
            xy_rot_diff = xy_sub.rotation_difference(xvec)
            xy_rot_diff.rotate(mathutils.Euler((0, 0, math.pi), 'XYZ'))

        xy_rotate = xy_rot_diff.inverted()
        scale = settings.bevel_depth / obj.data.bevel_depth

        if len(center) == 0:
            center = [left[-1], right[0]]

        for cp in center_left + center_right:
            c = (center[0]["co"] + center[-1]["co"]) / 2.0

            if settings.is_reverse_knot:
                cp.co.y = 0.0 - cp.co.y

            cp.co = (cp.co * scale)
            cp.co.rotate(xy_rotate)
            cp.co = cp.co + c

            cp.handle_left_type = 'FREE'
            cp.handle_right_type = 'FREE'
            cp.handle_left = cp.handle_left * scale + c
            cp.handle_right = cp.handle_right * scale + c

        if not is_local_object:
            bpy.data.objects.remove(obj, do_unlink=True)

        return (left + center_left,  center_right + right, False)

    def calc_normal(self, v0, v1, v2, v3):
        return (v0 - v2).cross(v1 - v3)
