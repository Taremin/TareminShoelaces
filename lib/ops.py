import bpy
import bmesh
import numpy
from . import lacing_list, library, utils


def check_index(self, value):
    obj = bpy.data.objects[self.knot]

    if obj is None:
        value = -1
    else:
        size = len(obj.data.splines)
        if value < 0:
            value = 0
        if size <= value:
            value = size - 1

    return value


class OBJECT_OT_TareminShoeLacesCreateCurve(bpy.types.Operator):
    bl_idname = 'taremin.shoelaces_create_curve'
    bl_label = 'カーブの生成'
    bl_options = {'REGISTER', 'UNDO'}
    lacing_method: bpy.props.EnumProperty(name="結び方", items=lambda scene, context: [(
        class_name, lacing_list.ShoeLacingMethods[class_name].label, "") for i, class_name in enumerate(lacing_list.ShoeLacingMethods)])

    # --------------------------------------------------------------------------

    offset: bpy.props.IntProperty(
        name="方向オフセット",
        description="生成するカーブの向きを決定します",
        default=0,
        min=0,
        max=3,
    )

    bevel_depth: bpy.props.FloatProperty(
        name="ベベル深度",
        description="カーブのベベル深度",
        default=0.01,
    )

    side_handle_length: bpy.props.FloatProperty(
        name="両端頂点の制御点の長さ",
        description="紐を通す部分の厚さを指定します",
        default=0.1,
    )

    center_handle_length_ratio: bpy.props.FloatProperty(
        name="中心頂点の制御点の比率",
        description="結び目など両端以外の制御点の、前後の頂点との長さの比率を指定します",
        default=0.5,
    )

    is_simple_curve: bpy.props.BoolProperty(
        name="シンプルなカーブ",
        description="最低限の制御点によるシンプルなカーブを生成",
        default=True,
    )
    use_center_offset: bpy.props.BoolProperty(
        name="上下端の中心に'両端頂点の制御点の長さ'を加える",
        description="上下端の中心に'両端頂点の制御点の長さ'を加えることで、へこむのを防止します",
        default=True,
    )

    is_create_hole_curve: bpy.props.BoolProperty(
        name="穴あけ用のカーブを生成",
        description="Booleanモディファイアなどで紐を通すための穴を開けるためのカーブを生成します",
        default=True,
    )

    knot_type: bpy.props.EnumProperty(name="結び目のタイプ", items=[
        (str(i), asset[0], "") for i, asset in enumerate(library.knots)
    ])

    is_reverse_knot: bpy.props.BoolProperty(
        name="結び目の前後を反転する",
        default=False,
    )

    is_reverse_spline_left: bpy.props.BoolProperty(
        name="左スプラインを逆順にする",
        description="",
        default=False,
    )
    is_reverse_spline_right: bpy.props.BoolProperty(
        name="右スプラインを逆順にする",
        description="",
        default=False,
    )

    def get_index_left(self):
        return self.sil

    def set_index_left(self, value):
        self.sil = check_index(self, value)

    spline_index_left: bpy.props.IntProperty(
        name="左スプラインのindex",
        description="",
        default=0,
        set=set_index_left,
        get=get_index_left,
    )
    sil: bpy.props.IntProperty(
        default=0,
        options={'HIDDEN'}
    )

    def get_index_right(self):
        return self.sir

    def set_index_right(self, value):
        self.sir = check_index(self, value)

    spline_index_right: bpy.props.IntProperty(
        name="右スプラインのindex",
        description="",
        default=0,
        set=set_index_right,
        get=get_index_right,
    )
    sir: bpy.props.IntProperty(
        default=0,
        options={'HIDDEN'}
    )

    knot: bpy.props.EnumProperty(items=utils.get_knot_list)

    # --------------------------------------------------------------------------

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

    def mesh_to_array2d(self, context, obj, corner_vertices):
        context.view_layer.objects.active = obj

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
        bevel_depth = self.bevel_depth

        err, result = type(self).check_mesh_geometry(base_obj)
        if err is not None:
            self.report({'ERROR_INVALID_INPUT'}, result)
            self.restore_status(base_obj, current_mode)
            return {'CANCELLED'}
        corner_vertices = result

        copy_obj = self.copy_object(base_obj)
        vertices2d = self.mesh_to_array2d(context, copy_obj, corner_vertices)

        bpy.ops.curve.primitive_bezier_circle_add(enter_editmode=True)
        curve = bpy.context.active_object

        curve_generator = lacing_list.ShoeLacingMethods[self.lacing_method](
            copy_obj, vertices2d, self)
        points, cyclic = curve_generator.create_curve_points(context)

        s = curve.data.splines[0]
        s.use_cyclic_u = cyclic

        bp = s.bezier_points
        bp.add(len(points) - len(bp))

        for i in range(len(points)):
            p = points[i]
            b = bp[i]

            if isinstance(p, bpy.types.BezierSplinePoint):
                b.co = self.convert_coordinate(copy_obj, curve, p.co)
                b.handle_left = p.handle_left
                b.handle_right = p.handle_right
                b.handle_left_type = 'AUTO'
                b.handle_right_type = 'AUTO'
            else:
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

        if self.is_create_hole_curve:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
            bpy.ops.curve.primitive_bezier_curve_add(enter_editmode=True)
            hole_curve_obj = bpy.context.active_object
            hole_curves = hole_curve_obj.data
            hole_splines = hole_curves.splines
            hole_splines.clear()
            for i in range(len(points)):
                p = points[i]
                if isinstance(p, bpy.types.BezierSplinePoint) or p['type'] != 'SIDE':
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

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.prop(self, "lacing_method")
        box.prop(self, "offset")
        box.prop(self, "bevel_depth")
        box.prop(self, "is_simple_curve")
        box.prop(self, "center_handle_length_ratio")
        box.prop(self, "side_handle_length")
        box.prop(self, "use_center_offset")
        box.prop(self, "is_create_hole_curve")

        box = layout.box()
        box.prop(self, "knot_type")
        knot = library.knots[int(self.knot_type)]
        knots = utils.get_knot_list(context.scene, context)
        if knot[1] == "" and len(knots) > 0:
            box.prop(self, "knot")
            box.prop(self, "is_reverse_spline_left")
            box.prop(self, "is_reverse_spline_right")
            box.prop(self, "spline_index_left")
            box.prop(self, "spline_index_right")
        if knot[1] is not None:
            box.prop(self, "is_reverse_knot")
