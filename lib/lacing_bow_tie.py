from . import lacing_base


class BowTieShoeLacing(lacing_base.ShoeLacing):
    label = "BowTieShoeLacing"

    def create_curve_points(self, context):
        vertices2d = self.vertices2d
        width, height = vertices2d.shape
        left = []
        right = []

        context.view_layer.objects.active = self.base_obj

        is_odd_height = (height % 2 != 0)
        bottom = self.calc_center_points(0, is_odd_height)
        if not is_odd_height:
            self.calc_side_points(left, right, 0, width - 1, 0, False)

        # ループ設定
        y = 1
        x1 = 0
        x2 = width - 1
        block_num = int(height / 2) - 1
        is_reversed = False

        if is_odd_height:
            y = 0
            block_num += 1
            x1, x2 = x2, x1
            is_reversed = True

        for block_index in range(block_num):
            self.calc_side_points(left, right, x1, x2, y, True)
            self.calc_cross_points(left, right, x1, y, x2, y + 1)
            self.calc_side_points(left, right, x2, x1, y + 1, False)

            is_reversed = not is_reversed
            x1, x2 = x2, x1
            y += 2

        top_left, top_right, cyclic = self.get_top_points(context)

        return (
            top_right + list(reversed(right)) + list(reversed(bottom)) + left + top_left,
            cyclic
        )
