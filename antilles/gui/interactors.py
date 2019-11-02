import numpy
from matplotlib import rcParams
from matplotlib.patches import FancyArrowPatch

from antilles.utils import flatten
from antilles.utils.math import cart2pol, pol2cart

K_UP = 'w'
K_DOWN = 's'
K_LEFT = 'a'
K_RIGHT = 'd'
ARROW_KEYS = K_UP + K_DOWN + K_LEFT + K_RIGHT
epsilon = 20  # pixels

for key, value in rcParams.items():
    if key.startswith('keymap'):
        for char in ARROW_KEYS:
            try:
                value.remove(char)
            except ValueError:
                pass


def move(key, x, y):
    # image coordinates are relative to an origin that's placed at the top left
    stride = 1

    if key == K_UP:
        y -= stride
    elif key == K_DOWN:
        y += stride
    elif key == K_LEFT:
        x -= stride
    elif key == K_RIGHT:
        x += stride

    return x, y


mode2color = {
    'light': 'k',
    'dark': 'w'
}


class BaseInteractor:
    def __init__(self, axes, **kwargs):
        self.axes = axes

        # TODO: better management of interactor colors
        self.color = mode2color[kwargs.get('mode', 'light')]
        self.active = kwargs.get('active', True)

        self.artists = {}

    def draw_callback(self, event):
        for artist in flatten(self.artists.values()):
            self.axes.draw_artist(artist)

    def button_press_callback(self, event):
        raise NotImplemented

    def button_release_callback(self, event):
        raise NotImplemented

    def motion_notify_callback(self, event):
        raise NotImplemented

    def key_press_event(self, event):
        raise NotImplemented

    def key_release_event(self, event):
        raise NotImplemented


class RocketDeviceInteractor(BaseInteractor):
    def __init__(self, axes, **kwargs):
        self.id = kwargs.get('id')
        self.label = kwargs.get('label')
        self.cxy = kwargs.get('cxy')
        self.wxy = kwargs.get('wxy')

        super().__init__(axes, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()
        self.init_label()

    def init_artists(self):
        main_arrow_props = {'alpha': 0.5 if not self.active else 0.2,
                            'animated': True,
                            'arrowstyle': '->,head_length=10,head_width=7',
                            'color': self.color,
                            'linestyle': 'solid'}

        opp_arrow_props = {'alpha': 0.3 if not self.active else 0.1,
                           'animated': True,
                           'arrowstyle': '->,head_length=10,head_width=7',
                           'color': self.color,
                           'linestyle': 'dashed'}

        right_props = {'alpha': 0.2 if not self.active else 0.1,
                       'animated': True,
                       'color': self.color,
                       'linestyle': 'dashed',
                       'linewidth': 1}

        line_props = {'alpha': 0.7 if not self.active else 0.3,
                      'animated': True,
                      'color': self.color,
                      'linestyle': '',
                      'marker': 'x',
                      'markerfacecolor': self.color,
                      'markersize': 8,
                      'markevery': [1]}

        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        rx, ry = self._calc_right_delta()

        # main arrow
        main_arrow = FancyArrowPatch(posA=self.cxy,
                                     posB=self.wxy,
                                     **main_arrow_props)
        self.artists['main_arrow'] = main_arrow
        self.axes.add_patch(main_arrow)

        # opposite arrow
        opp_arrow = FancyArrowPatch(posA=self.cxy,
                                    posB=(cx - dx, cy - dy),
                                    **opp_arrow_props)
        self.artists['opp_arrow'] = opp_arrow
        self.axes.add_patch(opp_arrow)

        # cross line
        right, = self.axes.plot([cx - rx, cx, cx + rx],
                                [cy - ry, cy, cy + ry],
                                **right_props)
        self.artists['right'] = right
        self.axes.add_line(right)

        # line
        line, = self.axes.plot([cx - dx, cx, cx + dx],
                               [cy - dy, cy, cy + dy],
                               **line_props)
        self.artists['line'] = line
        self.axes.add_line(line)

    def init_label(self):
        label_props = {'alpha': 0.7 if not self.active else 0.2,
                       'animated': True,
                       'family': 'sans-serif',
                       'horizontalalignment': 'center',
                       'size': 10,
                       'color': self.color,
                       'verticalalignment': 'center'}

        x, y = self._calc_label_pos()
        label = self.axes.text(x, y, self.label, **label_props)
        self.artists['label'] = label

    # === COMPUTED =========================================================== #

    @property
    def angle(self):
        delta_x = self.wxy[0] - self.cxy[0]
        delta_y = self.wxy[1] - self.cxy[1]

        return cart2pol(delta_x, delta_y)[1]

    def _calc_label_pos(self):
        offset = 60
        angle = self.angle + 90
        dx, dy = pol2cart(offset, angle)
        x, y = self.cxy[0] + dx, self.cxy[1] + dy
        return x, y

    def _calc_right_delta(self):
        right_offset = 40
        angle = self.angle + 90
        rx, ry = pol2cart(right_offset, angle)
        return rx, ry

    # === EXPORT ============================================================= #

    def get_params(self):
        return {'label': self.label,
                'id': self.id,
                'cxy': self.cxy,
                'angle': round(self.angle, 1)}

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event):
        line = self.artists['line']

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        lx, ly = self._calc_label_pos()
        rx, ry = self._calc_right_delta()

        self.artists['main_arrow'].set_positions(self.cxy, self.wxy)
        self.artists['opp_arrow'].set_positions(self.cxy, (cx - dx, cy - dy))
        self.artists['right'].set_data([cx - rx, cx, cx + rx],
                                       [cy - ry, cy, cy + ry])
        self.artists['line'].set_data([cx - dx, cx, cx + dx],
                                      [cy - dy, cy, cy + dy])
        self.artists['label'].set_position((lx, ly))

    def motion_notify_callback(self, event):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), \
               int(round(event.ydata))
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

    def key_press_event(self, event):
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

    def key_release_event(self, event):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return


class BrainDeviceInteractor(BaseInteractor):
    def __init__(self, axes, **kwargs):
        self.id = kwargs.get('id')
        self.label = kwargs.get('label')
        self.cxy = kwargs.get('cxy')
        self.wxy = kwargs.get('wxy')

        super().__init__(axes, **kwargs)

        self._ind = None
        self._ind_last = None

        self.init_artists()
        self.init_labels()

    def init_artists(self):
        main_arrow_props = {'alpha': 0.5 if not self.active else 0.2,
                            'animated': True,
                            'arrowstyle': '->,head_length=10,head_width=7',
                            'color': self.color,
                            'linestyle': 'solid'}

        opp_arrow_props = {'alpha': 0.3 if not self.active else 0.1,
                           'animated': True,
                           'arrowstyle': '->,head_length=10,head_width=7',
                           'color': self.color,
                           'linestyle': 'dashed'}

        line_props = {'alpha': 0.7 if not self.active else 0.3,
                      'animated': True,
                      'color': self.color,
                      'linestyle': '',
                      'marker': 'x',
                      'markerfacecolor': self.color,
                      'markersize': 8,
                      'markevery': [1]}

        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy

        # main arrow
        main_arrow = FancyArrowPatch(self.cxy, self.wxy,
                                     **main_arrow_props)
        self.artists['main_arrow'] = main_arrow
        self.axes.add_patch(main_arrow)

        # opposite arrow
        opp_arrow = FancyArrowPatch(self.cxy, (cx - dx, cy - dy),
                                    **opp_arrow_props)
        self.artists['opp_arrow'] = opp_arrow
        self.axes.add_patch(opp_arrow)

        # line
        line, = self.axes.plot([cx - dx, cx, cx + dx],
                               [cy - dy, cy, cy + dy],
                               **line_props)
        self.artists['line'] = line
        self.axes.add_line(line)

    def init_labels(self):
        label_props = {'alpha': 0.7 if not self.active else 0.3,
                       'animated': True,
                       'color': self.color,
                       'family': 'sans-serif',
                       'horizontalalignment': 'center',
                       'size': 10,
                       'verticalalignment': 'center'}

        x, y = self._calc_label_pos()
        label = self.axes.text(x, y, self.label, **label_props)
        self.artists['line'] = label

    # === COMPUTED =========================================================== #

    @property
    def angle(self):
        delta_x = self.wxy[0] - self.cxy[0]
        delta_y = self.wxy[1] - self.cxy[1]

        return cart2pol(delta_x, delta_y)[1]

    def _calc_label_pos(self):
        offset = 60
        angle = self.angle + 90
        dx, dy = pol2cart(offset, angle)
        x, y = self.cxy[0] + dx, self.cxy[1] + dy
        return x, y

    # === EXPORT ============================================================= #

    def get_params(self):
        return {'label': self.label,
                'id': self.id,
                'cxy': self.cxy,
                'angle': round(self.angle, 1)}

    # === INTERACTION ======================================================== #

    def get_ind_under_point(self, event):
        line = self.artists['line']

        xy = numpy.asarray(line.get_xydata())
        xyt = line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]

        d = numpy.hypot(xt - event.x, yt - event.y)
        ind_seq = numpy.nonzero(numpy.equal(d, numpy.amin(d)))[0]
        ind = ind_seq[0]

        if d[ind] >= epsilon:
            ind = None

        return ind

    def button_press_callback(self, event):
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        self._ind = self.get_ind_under_point(event)
        self._ind_last = self._ind

    def button_release_callback(self, event):
        if event.button != 1:
            return

        self._ind = None

    def update_all(self):
        cx, cy = self.cxy
        wx, wy = self.wxy
        dx, dy = wx - cx, wy - cy
        lx, ly = self._calc_label_pos()

        self.artists['main_arrow'].set_positions(self.cxy, self.wxy)
        self.artists['opp_arrow'].set_positions(self.cxy, (cx - dx, cy - dy))
        self.artists['line'].set_data([cx - dx, cx, cx + dx],
                                      [cy - dy, cy, cy + dy])
        self.artists['label'].set_position((lx, ly))

    def motion_notify_callback(self, event):
        if self._ind is None:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return

        x, y = int(round(event.xdata)), \
               int(round(event.ydata))
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

    def key_press_event(self, event):
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

    def key_release_event(self, event):
        if self._ind_last is None:
            return
        if event.inaxes is None:
            return


models2interactors = {
    'ROCKET': RocketDeviceInteractor,
    'BRAIN': BrainDeviceInteractor,
}
