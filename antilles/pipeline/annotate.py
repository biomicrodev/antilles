"""
A wxpython app for iterating through a pandas.DataFrame of slides and their
annotations.

The two DataFrames are 'positions' and 'angles', which are stored separately
since the sample angles remain the same for each slide in a block. The two
DataFrames are also modified in place; this app's only responsibility is to
open up a GUI for modifying the annotations. The actual data access is done by
the Extractor class.
"""
import os

import wx
from pubsub import pub

from antilles.utils.image import get_thumbnail
from antilles.utils.math import pol2cart, cart2pol


def add_dxy(x, y, l, a):
    dx, dy = pol2cart(l, a)
    dx, dy = int(round(dx)), int(round(dy))
    return x + dx, y + dy


def get_annotations(coords, angles):
    length = 1000  # pixels

    annotations = []
    for i, (sample, c_x, c_y) in coords.iterrows():
        angle = next(a['angle'] for a in angles if a['sample'] == sample)
        w_x, w_y = add_dxy(c_x, c_y, length, angle)

        annotations.append({
            'id': sample,
            'label': sample,
            'cxy': (c_x, c_y),
            'wxy': (w_x, w_y)
        })

    return annotations


class SlideAnnotationModel:
    def __init__(self, positions, angles):
        self.positions = positions
        self.angles = angles
        self.relpaths = sorted(list(set(self.positions['relpath'].unique())))

        self._ind = 0

    def get(self):
        relpath = self.relpaths[self._ind]
        inds = self.positions['relpath'] == relpath
        coords = self.positions.loc[inds, ['sample', 'center_x', 'center_y']]
        angles = self.angles.to_dict('records')

        annotations = get_annotations(coords, angles)
        thumbnail = get_thumbnail(relpath)

        return {**thumbnail, **{
            'id': relpath,
            'label': os.path.basename(relpath),
            'annotations': annotations,
        }}

    def update(self, slide):
        relpath = slide['id']
        annotations = slide['annotations']

        for annotation in annotations:
            sample = annotation['id']
            c_x, c_y = annotations['cxy']
            w_x, w_y = annotations['wxy']
            _, angle = cart2pol(w_x - c_x, w_y - c_y)

            ind_c = self.positions['relpath'] == relpath and \
                    self.positions['sample'] == sample
            self.positions.loc[ind_c, ['center_x']] = c_x
            self.positions.loc[ind_c, ['center_y']] = c_y

            ind_s = self.angles['sample'] == sample
            self.angles.loc[ind_s, ['angle']] = angle

    def prev(self):
        if not self.is_first():
            self._ind -= 1

    def next(self):
        if not self.is_last():
            self._ind += 1

    def is_first(self):
        return self._ind <= 0

    def is_last(self):
        return self._ind >= len(self.relpaths) - 1


class SlideAnnotationView:
    pass


class SlideAnnotationController:
    def __init__(self, positions, angles):
        self.view = SlideAnnotationView()
        # self.view.Show()

        # from view to controller
        pub.subscribe(self.save, 'save')

        self.model = SlideAnnotationModel(positions, angles)

    def render(self):
        slide = self.model.get()
        annotations = slide['annotations']

        print(annotations)

    def save(self, slide):
        self.model.update(slide)


def annotate_slides(*args, **kwargs):
    app = wx.App()
    controller = SlideAnnotationController(*args, **kwargs)
    controller.render()
    app.MainLoop()
