import bpy
import numpy
import bmesh
from bpy.props import IntProperty, FloatProperty, BoolProperty

bl_info = {
    'name': 'Taremin Shoelaces',
    'category': 'Tools',
    'author': 'Taremin',
    'location': 'View 3D > UI > Taremin',
    'description': "",
    'version': (0, 0, 3),
    'blender': (2, 80, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}


class ShoeLacingSettings:
    pass


class ShoeLacing:
    def __init__(self, obj, vertices2d, settings: ShoeLacingSettings):
        self.base_obj = obj
        self.vertices2d = vertices2d
        self.settings = settings

    def create_curve_points(self):
        pass

    def immutable(self, vec):
        return vec.copy().freeze()

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

    def calc_center_co_by_length(self):
        verts = self.base_obj.data.vertices
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


class DisplayShoeLacing(ShoeLacing):
    # Bottom
    #
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------O-------O-------+
    #              \       \
    #               \_______\______  BOTTOM
    #
    def get_bottom_points(self):
        return self.calc_center_points(0, False)

    # Middle
    # ナナメに分割する両方のedgeで共通してる頂点が中心点
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       |       |       |
    #     |       |       |       |
    #     |       |       |       |
    #     +-------+-------+-------+
    #     |       O       O       |
    #     |       |\  O   |\      |
    #     |       O_\__\__O_\_____|______  MIDDLE (CENTER): y = 1
    #     O-------+-------+-------O
    #      \                       \
    #       \_______________________\____  MIDDLE (SIDE): y = 1
    #
    def get_side_points(self):
        vertices2d = self.vertices2d
        width, height = vertices2d.shape
        data = self.base_obj.data
        verts = data.vertices

        settings = self.settings
        is_simple_curve = settings.is_simple_curve
        center_length = settings.bevel_depth
        center_handle_length_ratio = settings.center_handle_length_ratio

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(data)

        left = []
        right = []
        for y in range(1, height):
            x_prev = ((y - 1) % 2) * -1 % width
            x = (y % 2) * -1 % width

            # Side
            self.calc_side_points(left, right, x_prev, x, y - 1, False)

            # Center
            lines = []
            for x, x_prev in [(x, x_prev), (x_prev, x)]:
                bpy.ops.mesh.select_all(action='DESELECT')
                bm.verts.ensure_lookup_table()
                v1 = bm.verts[vertices2d[x_prev][y-1]]
                v2 = bm.verts[vertices2d[x][y]]
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
            front_or_back = 1 if y % 2 == 0 else -1
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

        return (left, right)

    # Top
    #        ______________________________ TOP (SIDE)
    #       /                       /
    #      /                       /
    #     O-------O-------O-------O
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
    def get_top_points(self):
        vertices2d = self.vertices2d
        width, height = vertices2d.shape
        verts = self.base_obj.data.vertices

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

        return left + center + right

    def create_curve_points(self):
        bpy.context.view_layer.objects.active = self.base_obj

        bottom = self.get_bottom_points()
        left, right = self.get_side_points()
        top = self.get_top_points()

        return bottom + left + top + list(reversed(right))


class OBJECT_OT_TareminShoeLacesCreateCurve(bpy.types.Operator):
    bl_idname = 'taremin.shoelaces_create_curve'
    bl_label = 'カーブの生成'
    bl_options = {'REGISTER', 'UNDO'}

    offset: IntProperty(
        name="方向オフセット",
        description="生成するカーブの向きを決定します",
        default=0,
        min=0,
        max=3,
    )

    bevel_depth: FloatProperty(
        name="ベベル深度",
        description="カーブのベベル深度",
        default=0.01,
    )

    side_handle_length = FloatProperty(
        name="両端頂点の制御点の長さ",
        description="紐を通す部分の厚さを指定します",
        default=0.1,
    )

    center_handle_length_ratio = FloatProperty(
        name="中心頂点の制御点の比率",
        description="結び目など両端以外の制御点の、前後の頂点との長さの比率を指定します",
        default=0.5,
    )

    is_simple_curve: BoolProperty(
        name="シンプルなカーブ",
        description="最低限の制御点によるシンプルなカーブを生成",
        default=True,
    )
    use_center_offset: BoolProperty(
        name="上下端の中心に'両端頂点の制御点の長さ'を加える",
        description="上下端の中心に'両端頂点の制御点の長さ'を加えることで、へこむのを防止します",
        default=True,
    )

    is_create_hole_curve: BoolProperty(
        name="穴あけ用のカーブを生成",
        description="Booleanモディファイアなどで紐を通すための穴を開けるためのカーブを生成します",
        default=True,
    )

    @classmethod
    def get_corner_vertices(cls, bm):
        corner_vertices = []

        for v in bm.verts:
            num_link_faces = len(v.link_faces)
            if num_link_faces == 1:
                corner_vertices.append(v.index)
            if num_link_faces == 0 or num_link_faces == 3 or num_link_faces > 4:
                return True, "不正な入力メッシュ"

        return None, corner_vertices

    # カド頂点からカド頂点への辺を取得
    @classmethod
    def get_corner_to_corner_edges(cls, bm, corner_vertices):
        corner_to_corner_edges = []

        for from_index in range(len(corner_vertices)):
            edge_from = corner_vertices[from_index]
            for i in range(1, 4-from_index):
                to_index = (from_index + i) % 4
                edge_to = corner_vertices[to_index]

                bpy.ops.mesh.select_all(action='DESELECT')
                bm.verts[edge_from].select = True
                bm.verts[edge_to].select = True
                bpy.ops.mesh.shortest_path_select()

                edges = [e for e in bm.edges if e.select]

                # 距離が1の場合、shortest_path_selectで選択が解除されてしまうため別の方法で辺を取得する
                if len(edges) == 0:
                    v1 = bm.verts[edge_from]
                    v2 = bm.verts[edge_to]
                    edges = [
                        e for e in bm.edges if v1 in e.verts and v2 in e.verts]

                corner_to_corner_edges.append(
                    (edge_from, edge_to, edges))

        # 対角線を削除(対角線は辺の数が 横+高さ なので辺の多いものを2つ削除すれば良い)
        corner_to_corner_edges.sort(key=lambda tuple: len(tuple[2]))
        corner_to_corner_edges.pop()
        corner_to_corner_edges.pop()

        # from_index, to_index のソート
        corner_to_corner_edges.sort(key=lambda tuple: tuple[1])
        corner_to_corner_edges.sort(key=lambda tuple: tuple[0])

        return corner_to_corner_edges

    @classmethod
    def edges_to_sorted_vertices(cls, bm, from_idx, to_idx, edges):
        visited = {}

        next = from_idx
        visited[from_idx] = True
        verts = [bm.verts[from_idx]]

        while next != to_idx:
            vert = bm.verts[next]
            link_edges = vert.link_edges
            next_edge = None
            if len(link_edges) == 1:
                next_edge = link_edges[0]
            else:
                for edge in link_edges:
                    other_vert = edge.other_vert(vert)
                    if other_vert.index in visited:
                        continue
                    if edge in edges:
                        next_edge = edge
                        break
            visited[vert.index] = True
            verts.append(next_edge.other_vert(vert))
            next = next_edge.other_vert(vert).index

        return verts

    def fill_verts(self, visited, v1, v2):
        for e1 in v1.link_edges:
            o1 = e1.other_vert(v1).index
            for e2 in v2.link_edges:
                o2 = e2.other_vert(v2).index
                if o1 == o2 and o1 not in visited:
                    visited[o1] = True
                    return o1
        return None

    def convert_coordinate(self, src_obj, dst_obj, vector):
        return (dst_obj.matrix_world.inverted() @ (src_obj.matrix_world @ vector))

    def mesh_to_array2d(self, obj, corner_vertices):
        bpy.context.view_layer.objects.active = obj

        offset = self.offset

        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        bpy.ops.mesh.select_mode(type='VERT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        corner_to_corner_edges = type(self).get_corner_to_corner_edges(
            bm, corner_vertices)

        # カド(始点)からカド(終点)と経路となる辺の辞書を作成する
        # このとき同じ始点から開始する場合は始点と終点を入れ替え、一巡するような形にする
        corner_to_corner_with_route = {}
        for from_index, to_index, edges in corner_to_corner_edges:
            if from_index in corner_to_corner_with_route:
                # from, to 双方使用済みだった場合はすでに辞書に登録済みの方がおかしいので修正
                if to_index in corner_to_corner_with_route:
                    for index1, index2 in ((from_index, to_index), (to_index, from_index)):
                        tmp_index, tmp_edges = corner_to_corner_with_route[index1]
                        if tmp_index not in corner_to_corner_with_route:
                            corner_to_corner_with_route[tmp_index] = (
                                index1, tmp_edges)
                            corner_to_corner_with_route[index1] = (
                                index2, edges)
                            break
                else:
                    corner_to_corner_with_route[to_index] = (from_index, edges)
            else:
                corner_to_corner_with_route[from_index] = (to_index, edges)

        # 辺のリストから始点から終点までの頂点のリストにする
        start, next, _ = corner_to_corner_edges[0]
        edges_tmp = []
        current = start

        while True:
            to_index, edges = corner_to_corner_with_route[current]
            edges_tmp.append(type(self).edges_to_sorted_vertices(
                bm, current, to_index, edges))

            # update loop
            current = next
            next, _ = corner_to_corner_with_route[next]
            if current == start:
                break

        edges_tmp = edges_tmp[offset:] + edges_tmp[:offset]
        first = edges_tmp[0]
        last = edges_tmp[len(edges_tmp)-1]

        # 四角形を一巡する形になっているため、最初と最後の辺の長さが横幅と高さになる
        width = len(first)
        height = len(last)
        vertices2d = numpy.zeros((width, height), dtype=int)
        visited = {}
        for from_index, v in enumerate(first):
            vertices2d[from_index][0] = v.index
            visited[v.index] = True
        for from_index, v in enumerate(reversed(last)):
            vertices2d[0][from_index] = v.index
            visited[v.index] = True

        for x in range(1, width):
            for y in range(1, height):
                vertices2d[x][y] = self.fill_verts(
                    visited, bm.verts[vertices2d[x-1][y]], bm.verts[vertices2d[x][y-1]])

        return vertices2d

    @classmethod
    def check_mesh_geometry(cls, obj):
        result = []

        if obj is None:
            return True, "アクティブオブジェクトがありません"

        if obj.type != 'MESH':
            return True, "アクティブオブジェクトがメッシュではありません"

        if bpy.context.object.mode != 'OBJECT':
            return True, "オブジェクトモードではありません"

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        err, result = cls.get_corner_vertices(bm)

        if err:
            return True, result

        corner_vertices = result

        if corner_vertices is None:
            return True, "カドになる頂点が見つかりません"

        if len(corner_vertices) != 4:
            return True, "カドの頂点が4以外です"

        return None, corner_vertices

    def copy_object(self, base_obj):
        copy_obj = base_obj.copy()
        copy_obj.data = base_obj.data.copy()
        bpy.context.scene.collection.objects.link(copy_obj)
        bpy.context.view_layer.objects.active = copy_obj
        return copy_obj

    def restore_status(self, active_object, mode, remove_objects=[]):
        bpy.context.view_layer.objects.active = active_object
        bpy.ops.object.mode_set(mode=mode, toggle=False)

        for obj in remove_objects:
            bpy.data.objects.remove(obj, do_unlink=True)

    @classmethod
    def poll(cls, context):
        err, result = cls.check_mesh_geometry(context.active_object)
        return not err

    def execute(self, context):
        base_obj = bpy.context.active_object
        current_mode = bpy.context.object.mode

        settings = ShoeLacingSettings()
        settings.bevel_depth = self.bevel_depth
        settings.is_simple_curve = self.is_simple_curve
        settings.center_handle_length_ratio = self.center_handle_length_ratio
        settings.side_handle_length = self.side_handle_length
        settings.use_center_offset = self.use_center_offset
        settings.is_create_hole_curve = self.is_create_hole_curve

        bevel_depth = self.bevel_depth

        err, result = type(self).check_mesh_geometry(base_obj)
        if err is not None:
            self.report({'ERROR_INVALID_INPUT'}, result)
            self.restore_status(base_obj, current_mode)
            return {'CANCELLED'}
        corner_vertices = result

        copy_obj = self.copy_object(base_obj)
        vertices2d = self.mesh_to_array2d(copy_obj, corner_vertices)

        bpy.ops.curve.primitive_bezier_circle_add(enter_editmode=True)
        curve = bpy.context.active_object

        curve_generator = DisplayShoeLacing(copy_obj, vertices2d, settings)
        points = curve_generator.create_curve_points()

        bp = curve.data.splines[0].bezier_points
        bp.add(len(points) - len(bp))

        for i in range(len(points)):
            p = points[i]
            b = bp[i]

            b.co = self.convert_coordinate(copy_obj, curve, p['co'])
            b.handle_left_type = 'FREE'
            b.handle_right_type = 'FREE'
            b.handle_left = self.convert_coordinate(
                copy_obj, curve, p['handle_left'])
            b.handle_right = self.convert_coordinate(
                copy_obj, curve, p['handle_right'])
            b.handle_left_type = 'ALIGNED'
            b.handle_right_type = 'ALIGNED'

        bpy.context.view_layer.objects.active = curve
        bpy.ops.curve.select_all(action='DESELECT')
        curve.data.bevel_depth = bevel_depth

        if settings.is_create_hole_curve:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.curve.primitive_bezier_curve_add(enter_editmode=True)
            hole_curve_obj = bpy.context.active_object
            hole_curves = hole_curve_obj.data
            hole_splines = hole_curves.splines
            hole_splines.clear()
            for i in range(len(points)):
                p = points[i]
                if p['type'] != 'SIDE':
                    continue
                s = hole_splines.new(type='POLY')
                s.points.add(2 - len(s.points))
                s.points[0].co = self.convert_coordinate(
                    copy_obj, hole_curve_obj, p['handle_left']).to_4d()
                s.points[1].co = self.convert_coordinate(
                    copy_obj, hole_curve_obj, p['handle_right']).to_4d()
            hole_curves.bevel_depth = bevel_depth

        self.restore_status(base_obj, current_mode, [copy_obj])

        return {'FINISHED'}


class VIEW3D_PT_TareminShoeLacesPanel(bpy.types.Panel):
    bl_label = 'Taremin Shoe Laces'
    bl_region_type = 'UI'
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        errors = []

        err, result = OBJECT_OT_TareminShoeLacesCreateCurve.check_mesh_geometry(
            obj)
        if err:
            errors.append(result)

        for err in errors:
            col = layout.column(align=True)
            col.label(text=err, icon='ERROR')

        col = layout.column(align=True)
        operator_row = col.row(align=True)
        operator_row.operator(OBJECT_OT_TareminShoeLacesCreateCurve.bl_idname)


classesToRegister = [
    VIEW3D_PT_TareminShoeLacesPanel,
    OBJECT_OT_TareminShoeLacesCreateCurve,
]


def register():
    for value in classesToRegister:
        bpy.utils.register_class(value)


def unregister():
    for value in classesToRegister:
        bpy.utils.unregister_class(value)


if __name__ == '__main__':
    register()
