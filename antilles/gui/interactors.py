from typing import Tuple, Dict, Union, Any

import numpy
from matplotlib import rcParams
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.patches import FancyArrowPatch, Arc

from antilles.utils.math import cart2pol, pol2cart

K_UP: str = "w"
K_DOWN: str = "s"
K_LEFT: str = "a"
K_RIGHT: str = "d"
ARROW_KEYS: str = K_UP + K_DOWN + K_LEFT + K_RIGHT
epsilon: int = 20  # pixels

for key, value in rcParams.items():
    if key.startswith("keymap"):
        for char in ARROW_KEYS:
            try:
                value.remove(char)
            except ValueError:
                pass


def move(key: str, x: int, y: int) -> Tuple[int, int]:
    # image coordinates are relative to an origin that's placed at the top left
    stride: int = 1

    if key == K_UP:
        y -= stride
    elif key == K_DOWN:
        y += stride
    elif key == K_LEFT:
        x -= stride
    elif key == K_RIGHT:
        x += stride

    return x, y


mode2color: Dict[str, str] = {"light": "k", "dark": "w"}


class BaseInteractor:
    def __init__(self, axes: Axes, **kwargs):
        self.axes: Axes = axes

        # TODO: better management of interactor colors
        self.color: str = mode2color[kwargs.get("mode", "light")]
        self.active: bool = kwargs.get("active", True)
        self.artists = {}

    def draw_callback(self, event):
        for artist in self.artists.values():
            self.axes.draw_artist(artist)

    def button_press_callback(self, event: MouseEvent):
        raise NotImplemented

    def button_release_callback(self, event: MouseEvent):
        raise NotImplemented

    def motion_notify_callback(self, event: MouseEvent):
        raise NotImplemented

    def key_press_event(self, event: MouseEvent):
        raise NotImplemented

    def key_release_event(self, event: MouseEvent):
        raise NotImplemented


class ArrowInteractor(BaseInteractor):
    def __init__(self, *args, **kwargs):
        self.id: str = kwargs.get("id")
        self.label: str = kwargs.get("label")
        self.cxy: Tuple[int, int] = kwargs.get("cxy")
        self.wxy: Tuple[int, int] = kwargs.get("wxy")

        super().__init__(*args, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()
        self.init_label()

    def init_artists(self):
        main_arrow_props: Dict[str, Any] = {
            "alpha": 0.5 if self.active else 0.2,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "solid",
        }

        line_props: Dict[str, Any] = {
            "alpha": 0.7 if self.active else 0.3,
            "animated": True,
            "color": self.color,
            "linestyle": "",
            "marker": "x",
            "markerfacecolor": self.color,
            "markersize": 8,
            "markevery": [0],
        }

        cx, cy = self.cxy
        wx, wy = self.wxy

        # main arrow
        main_arrow = FancyArrowPatch(posA=self.cxy, posB=self.wxy, **main_arrow_props)
        self.artists["main_arrow"] = main_arrow
        self.axes.add_patch(main_arrow)

        # line
        (line,) = self.axes.plot([cx, wx], [cy, wy], **line_props)
        self.artists["line"] = line
        self.axes.add_line(line)

    def init_label(self):
        label_props: Dict[str, Any] = {
            "alpha": 0.7 if self.active else 0.2,
            "animated": True,
            "family": "sans-serif",
            "horizontalalignment": "center",
            "size": 10,
            "color": self.color,
            "verticalalignment": "center",
        }

        x, y = self._calc_label_pos()
        label = self.axes.text(x, y, self.label, **label_props)
        self.artists["label"] = label

    # === COMPUTED =========================================================== #

    @property
    def angle(self) -> float:
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        _, angle = cart2pol(dx, dy)
        return angle

    def _calc_label_pos(self) -> Tuple[float, float]:
        offset = 60  # pixels
        angle = self.angle + 90

        cx, cy = self.cxy
        dx, dy = pol2cart(offset, angle)
        x, y = cx + dx, cy + dy
        return x, y

    def _calc_right_delta(self) -> Tuple[float, float]:
        right_offset = 40
        angle = self.angle + 90
        rx, ry = pol2cart(right_offset, angle)
        return rx, ry

    # === EXPORT ============================================================= #

    def get_params(self) -> Dict[str, Union[str, Tuple[int, int]]]:
        return {"id": self.id, "cxy": self.cxy, "wxy": self.wxy}

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event: MouseEvent):
        line = self.artists["line"]

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event: MouseEvent):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event: MouseEvent):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        lxy = self._calc_label_pos()

        self.artists["main_arrow"].set_positions(self.cxy, self.wxy)
        self.artists["line"].set_data([cx, cx + dx], [cy, cy + dy])
        self.artists["label"].set_position(lxy)

    def motion_notify_callback(self, event: MouseEvent):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), int(round(event.ydata))
        if self._ind == 1:
            self._set_arrow_head(x, y)
            self.update_all()

        elif self._ind == 0:
            self._set_arrow_tail(x, y)
            self.update_all()

    def key_press_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

        key = event.key
        if self._ind_last == 1:
            # arrow head moved
            wx, wy = self.wxy
            wx, wy = move(key, wx, wy)
            self._set_arrow_head(wx, wy)
            self.update_all()

        elif self._ind_last == 0:
            cx, cy = self.cxy
            cx, cy = move(key, cx, cy)
            self._set_arrow_tail(cx, cy)
            self.update_all()

    def key_release_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

    # === ATOMIC INTERACTION ================================================= #
    def _set_arrow_head(self, x: float, y: float):
        self.wxy = x, y

    def _set_arrow_tail(self, x: float, y: float):
        cx, cy = self.cxy
        self.cxy = x, y

        # move arrow head along with tail
        wx, wy = self.wxy
        self.wxy = wx - cx + x, wy - cy + y


class BowInteractor(BaseInteractor):
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get("id")
        self.cxy = kwargs.get("cxy")
        self.wxy = kwargs.get("wxy")

        self.span = kwargs.get("span", 90.0)  # degrees
        self.stickout = kwargs.get("stickout", 50)  # px

        super().__init__(*args, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()

    def init_artists(self):
        main_arrow_props: Dict[str, Any] = {
            "alpha": 0.5 if self.active else 0.2,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "solid",
        }

        line_props: Dict[str, Any] = {
            "alpha": 0.7 if self.active else 0.3,
            "animated": True,
            "color": self.color,
            "linestyle": "",
            "marker": "x",
            "markerfacecolor": self.color,
            "markersize": 8,
        }

        arc_props: Dict[str, Any] = {
            "alpha": 0.5 if self.active else 0.3,
            "animated": True,
            "color": self.color,
            "linestyle": "dashed",
        }

        prong_props: Dict[str, Any] = {
            "alpha": 0.5 if self.active else 0.2,
            "animated": True,
            "color": self.color,
            "linestyle": "dashed",
            "linewidth": 1,
        }

        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        r, angle = cart2pol(dx, dy)
        hspan = self.span / 2

        ex, ey = pol2cart(r + self.stickout, angle)

        # main arrow
        main_arrow = FancyArrowPatch(
            posA=self.cxy, posB=(ex + cx, ey + cy), **main_arrow_props
        )
        self.artists["main_arrow"] = main_arrow
        self.axes.add_patch(main_arrow)

        # line
        (line,) = self.axes.plot([cx, wx], [cy, wy], **line_props)
        self.artists["line"] = line
        self.axes.add_line(line)

        # arc
        arc = Arc(
            xy=self.cxy,
            width=2 * r,
            height=2 * r,
            angle=angle,
            theta1=-hspan,
            theta2=hspan,
            **arc_props
        )
        self.artists["arc"] = arc
        self.axes.add_patch(arc)

        # prongs
        r_ext = r + self.stickout
        p1_angle = angle - hspan
        p1 = {"tail": pol2cart(r, p1_angle), "head": pol2cart(r_ext, p1_angle)}
        (prong1,) = self.axes.plot(
            [cx + p1["tail"][0], cx + p1["head"][0]],
            [cy + p1["tail"][1], cy + p1["head"][1]],
            **prong_props
        )
        self.artists["prong1"] = prong1
        self.axes.add_line(prong1)

        p2_angle = angle + hspan
        p2 = {"tail": pol2cart(r, p2_angle), "head": pol2cart(r_ext, p2_angle)}
        (prong2,) = self.axes.plot(
            [cx + p2["tail"][0], cx + p2["head"][0]],
            [cy + p2["tail"][1], cy + p2["head"][1]],
            **prong_props
        )
        self.artists["prong2"] = prong2
        self.axes.add_line(prong2)

    # === COMPUTED =========================================================== #

    @property
    def angle(self) -> float:
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        _, angle = cart2pol(dx, dy)
        return angle

    # === EXPORT ============================================================= #

    def get_params(self) -> Dict[str, Any]:
        return {"id": self.id, "cxy": self.cxy, "wxy": self.wxy}

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event: MouseEvent) -> int:
        line = self.artists["line"]

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event: MouseEvent):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event: MouseEvent):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        r, angle = cart2pol(dx, dy)

        ex, ey = pol2cart(r + self.stickout, angle)

        self.artists["main_arrow"].set_positions(self.cxy, (cx + ex, cy + ey))
        self.artists["line"].set_data([cx, wx], [cy, wy])

        arc = self.artists["arc"]
        arc.angle = angle
        arc.width = 2 * r
        arc.height = 2 * r
        arc.set_center(self.cxy)

        r_ext = r + self.stickout
        hspan = self.span / 2
        p1_angle = angle - hspan
        p1 = {"tail": pol2cart(r, p1_angle), "head": pol2cart(r_ext, p1_angle)}
        self.artists["prong1"].set_data(
            [cx + p1["tail"][0], cx + p1["head"][0]],
            [cy + p1["tail"][1], cy + p1["head"][1]],
        )

        p2_angle = angle + hspan
        p2 = {"tail": pol2cart(r, p2_angle), "head": pol2cart(r_ext, p2_angle)}
        self.artists["prong2"].set_data(
            [cx + p2["tail"][0], cx + p2["head"][0]],
            [cy + p2["tail"][1], cy + p2["head"][1]],
        )

    def motion_notify_callback(self, event: MouseEvent):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), int(round(event.ydata))
        if self._ind == 1:
            self._set_arrow_head(x, y)
            self.update_all()

        elif self._ind == 0:
            self._set_arrow_tail(x, y)
            self.update_all()

    def key_press_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

        key = event.key
        if self._ind_last == 1:
            # arrow head moved
            wx, wy = self.wxy
            wx, wy = move(key, wx, wy)
            self._set_arrow_head(wx, wy)
            self.update_all()

        elif self._ind_last == 0:
            cx, cy = self.cxy
            cx, cy = move(key, cx, cy)
            self._set_arrow_tail(cx, cy)
            self.update_all()

    def key_release_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

    # === ATOMIC INTERACTION ================================================= #
    def _set_arrow_head(self, x: float, y: float):
        self.wxy = x, y

    def _set_arrow_tail(self, x: float, y: float):
        self.cxy = x, y


class RocketDeviceInteractor(BaseInteractor):
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get("id")
        self.label = kwargs.get("label")
        self.cxy = kwargs.get("cxy")
        self.wxy = kwargs.get("wxy")

        super().__init__(*args, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()
        self.init_label()

    def init_artists(self):
        main_arrow_props = {
            "alpha": 0.5 if self.active else 0.2,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "solid",
        }

        opp_arrow_props = {
            "alpha": 0.3 if self.active else 0.1,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "dashed",
        }

        right_props = {
            "alpha": 0.2 if self.active else 0.1,
            "animated": True,
            "color": self.color,
            "linestyle": "dashed",
            "linewidth": 1,
        }

        line_props = {
            "alpha": 0.7 if self.active else 0.3,
            "animated": True,
            "color": self.color,
            "linestyle": "",
            "marker": "x",
            "markerfacecolor": self.color,
            "markersize": 8,
            "markevery": [1],
        }

        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        rx, ry = self._calc_right_delta()

        # main arrow
        main_arrow = FancyArrowPatch(posA=self.cxy, posB=self.wxy, **main_arrow_props)
        self.artists["main_arrow"] = main_arrow
        self.axes.add_patch(main_arrow)

        # opposite arrow
        opp_arrow = FancyArrowPatch(
            posA=self.cxy, posB=(cx - dx, cy - dy), **opp_arrow_props
        )
        self.artists["opp_arrow"] = opp_arrow
        self.axes.add_patch(opp_arrow)

        # cross line
        (right,) = self.axes.plot(
            [cx - rx, cx, cx + rx], [cy - ry, cy, cy + ry], **right_props
        )
        self.artists["right"] = right
        self.axes.add_line(right)

        # line
        (line,) = self.axes.plot(
            [cx - dx, cx, cx + dx], [cy - dy, cy, cy + dy], **line_props
        )
        self.artists["line"] = line
        self.axes.add_line(line)

    def init_label(self):
        label_props = {
            "alpha": 0.7 if not self.active else 0.2,
            "animated": True,
            "family": "sans-serif",
            "horizontalalignment": "center",
            "size": 10,
            "color": self.color,
            "verticalalignment": "center",
        }

        x, y = self._calc_label_pos()
        label = self.axes.text(x, y, self.label, **label_props)
        self.artists["label"] = label

    # === COMPUTED =========================================================== #

    @property
    def angle(self) -> float:
        dx = self.wxy[0] - self.cxy[0]
        dy = self.wxy[1] - self.cxy[1]

        _, angle = cart2pol(dx, dy)
        return angle

    def _calc_label_pos(self) -> Tuple[float, float]:
        offset = 60
        angle = self.angle + 90
        dx, dy = pol2cart(offset, angle)
        x, y = self.cxy[0] + dx, self.cxy[1] + dy
        return x, y

    def _calc_right_delta(self) -> Tuple[float, float]:
        right_offset = 40
        angle = self.angle + 90
        rx, ry = pol2cart(right_offset, angle)
        return rx, ry

    # === EXPORT ============================================================= #

    def get_params(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "id": self.id,
            "cxy": self.cxy,
            "angle": round(self.angle, 1),
        }

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event: MouseEvent) -> int:
        line = self.artists["line"]

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event: MouseEvent):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event: MouseEvent):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        lx, ly = self._calc_label_pos()
        rx, ry = self._calc_right_delta()

        self.artists["main_arrow"].set_positions(self.cxy, self.wxy)
        self.artists["opp_arrow"].set_positions(self.cxy, (cx - dx, cy - dy))
        self.artists["right"].set_data([cx - rx, cx, cx + rx], [cy - ry, cy, cy + ry])
        self.artists["line"].set_data([cx - dx, cx, cx + dx], [cy - dy, cy, cy + dy])
        self.artists["label"].set_position((lx, ly))

    def motion_notify_callback(self, event: MouseEvent):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), int(round(event.ydata))
        if self._ind == 0:
            # opposite arrow head was moved
            cx, cy = self.cxy
            self.wxy = 2 * cx - x, 2 * cy - y
            self.update_all()

        elif self._ind == 1:
            # center was moved
            cx, cy = self.cxy
            self.cxy = x, y

            # move main arrow head along with center
            wx, wy = self.wxy
            self.wxy = wx - cx + x, wy - cy + y

            self.update_all()

        elif self._ind == 2:
            # main arrow head was moved
            self.wxy = x, y
            self.update_all()

    def key_press_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

        key = event.key
        if self._ind_last == 0:
            # opposite arrow head was moved; move point after inverting
            wx, wy = self.wxy
            wx, wy = move(key, -wx, -wy)
            self.wxy = -wx, -wy
            self.update_all()

        elif self._ind_last == 1:
            # center was moved
            self.cxy = move(key, *self.cxy)

            # move main arrow head along with center
            self.wxy = move(key, *self.wxy)

            self.update_all()

        elif self._ind_last == 2:
            # well was moved
            self.wxy = move(key, *self.wxy)
            self.update_all()

    def key_release_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return


class BrainDeviceInteractor(BaseInteractor):
    def __init__(self, *args, **kwargs):
        self.id = kwargs.get("id")
        self.label = kwargs.get("label")
        self.cxy = kwargs.get("cxy")
        self.wxy = kwargs.get("wxy")

        super().__init__(*args, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()
        self.init_labels()

    def init_artists(self):
        main_arrow_props = {
            "alpha": 0.5 if not self.active else 0.2,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "solid",
        }

        opp_arrow_props = {
            "alpha": 0.3 if not self.active else 0.1,
            "animated": True,
            "arrowstyle": "->,head_length=10,head_width=7",
            "color": self.color,
            "linestyle": "dashed",
        }

        line_props = {
            "alpha": 0.7 if not self.active else 0.3,
            "animated": True,
            "color": self.color,
            "linestyle": "",
            "marker": "x",
            "markerfacecolor": self.color,
            "markersize": 8,
            "markevery": [1],
        }

        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy

        # main arrow
        main_arrow = FancyArrowPatch(self.cxy, self.wxy, **main_arrow_props)
        self.artists["main_arrow"] = main_arrow
        self.axes.add_patch(main_arrow)

        # opposite arrow
        opp_arrow = FancyArrowPatch(self.cxy, (cx - dx, cy - dy), **opp_arrow_props)
        self.artists["opp_arrow"] = opp_arrow
        self.axes.add_patch(opp_arrow)

        # line
        (line,) = self.axes.plot(
            [cx - dx, cx, cx + dx], [cy - dy, cy, cy + dy], **line_props
        )
        self.artists["line"] = line
        self.axes.add_line(line)

    def init_labels(self):
        label_props = {
            "alpha": 0.7 if not self.active else 0.3,
            "animated": True,
            "color": self.color,
            "family": "sans-serif",
            "horizontalalignment": "center",
            "size": 10,
            "verticalalignment": "center",
        }

        x, y = self._calc_label_pos()
        label = self.axes.text(x, y, self.label, **label_props)
        self.artists["line"] = label

    # === COMPUTED =========================================================== #

    @property
    def angle(self) -> float:
        dx = self.wxy[0] - self.cxy[0]
        dy = self.wxy[1] - self.cxy[1]

        _, angle = cart2pol(dx, dy)
        return angle

    def _calc_label_pos(self) -> Tuple[float, float]:
        offset = 60
        angle = self.angle + 90
        dx, dy = pol2cart(offset, angle)
        x, y = self.cxy[0] + dx, self.cxy[1] + dy
        return x, y

    # === EXPORT ============================================================= #

    def get_params(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "id": self.id,
            "cxy": self.cxy,
            "angle": round(self.angle, 1),
        }

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event: MouseEvent) -> int:
        line = self.artists["line"]

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event: MouseEvent):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event: MouseEvent):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        lx, ly = self._calc_label_pos()

        self.artists["main_arrow"].set_positions(self.cxy, self.wxy)
        self.artists["opp_arrow"].set_positions(self.cxy, (cx - dx, cy - dy))
        self.artists["line"].set_data([cx - dx, cx, cx + dx], [cy - dy, cy, cy + dy])
        self.artists["label"].set_position((lx, ly))

    def motion_notify_callback(self, event: MouseEvent):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), int(round(event.ydata))
        if self._ind == 0:
            # opposite arrow head was moved
            cx, cy = self.cxy
            self.wxy = 2 * cx - x, 2 * cy - y
            self.update_all()

        elif self._ind == 1:
            # center was moved
            cx, cy = self.cxy
            self.cxy = x, y

            # move main arrow head along with center
            wx, wy = self.wxy
            self.wxy = wx - cx + x, wy - cy + y

            self.update_all()

        elif self._ind == 2:
            # main arrow head was moved
            self.wxy = x, y
            self.update_all()

    def key_press_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return

        key = event.key
        if self._ind_last == 0:
            # opposite arrow head was moved; move point after inverting
            wx, wy = self.wxy
            wx, wy = move(key, -wx, -wy)
            self.wxy = -wx, -wy
            self.update_all()

        elif self._ind_last == 1:
            # center was moved
            self.cxy = move(key, *self.cxy)

            # move main arrow head along with center
            self.wxy = move(key, *self.wxy)

            self.update_all()

        elif self._ind_last == 2:
            # well was moved
            self.wxy = move(key, *self.wxy)
            self.update_all()

    def key_release_event(self, event: MouseEvent):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return


device2interactor = {
    "ARROW": ArrowInteractor,
    "ROCKET": RocketDeviceInteractor,
    "BRAIN": BrainDeviceInteractor,
    "BOW": BowInteractor,
}
