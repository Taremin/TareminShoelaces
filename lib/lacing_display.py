from . import lacing_base


class DisplayShoeLacing(lacing_base.ShoeLacing):
    label = "DisplayShoeLacing"

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
    #     |       O_\__\__O_\_____|______  MIDDLE (CROSS): y = 1
    #     O-------+-------+-------O
    #      \                       \
    #       \_______________________\____  MIDDLE (SIDE): y = 1
    #
    def get_middle_points(self):
        vertices2d = self.vertices2d
        width, height = vertices2d.shape

        left = []
        right = []
        for y in range(1, height):
            from_y = y - 1
            to_y = y
            from_x = ((y - 1) % 2) * -1 % width
            to_x = (y % 2) * -1 % width

            self.calc_side_points(left, right, from_x, to_x, from_y, True)
            self.calc_cross_points(left, right, from_x, from_y, to_x, to_y)

        return (left, right)

    def create_curve_points(self, context):
        context.view_layer.objects.active = self.base_obj

        bottom = self.get_bottom_points()
        left, right = self.get_middle_points()
        top_left, top_right = self.get_top_points(context)

        return top_right + list(reversed(right)) + list(reversed(bottom)) + left + top_left
