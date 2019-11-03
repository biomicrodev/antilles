"""
A wxpython app for iterating through a pandas.DataFrame of slides and their
annotations.

The two DataFrames are 'coords' and 'angles', which are stored separately since
the sample angles remain the same for each slide in a block. The two DataFrames
are also modified in place; this app's only responsibility is to open up a GUI
for modifying the annotations. The actual data access is done by the Extractor
class.
"""
import os

import wx
from pubsub import pub

from antilles.gui.panels import ButtonPanel, ImageAnnotationPanel
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
    def __init__(self, coords, angles):
        self.coords = coords
        self.angles = angles
        self.relpaths = sorted(list(set(self.coords['relpath'].unique())))

        self._ind = 0

    def get(self):
        relpath = self.relpaths[self._ind]
        inds = self.coords['relpath'] == relpath
        coords = self.coords.loc[inds, ['sample', 'center_x', 'center_y']]
        angles = self.angles.to_dict('records')

        title = f'Slide {self._ind + 1}/{len(self.relpaths)}: ' \
                f'{os.path.basename(relpath)}'
        annotations = get_annotations(coords, angles)
        thumbnail = get_thumbnail(relpath)

        return {
            'id': relpath,
            'title': title,
            'annotations': annotations,
            'factor': thumbnail['factor'],
            'image': thumbnail['image']
        }

    def update(self, slide):
        relpath = slide['id']
        annotations = slide['annotations']

        for annotation in annotations:
            sample = annotation['id']
            c_x, c_y = annotations['cxy']
            w_x, w_y = annotations['wxy']
            _, angle = cart2pol(w_x - c_x, w_y - c_y)

            ind_c = self.coords['relpath'] == relpath and \
                    self.coords['sample'] == sample
            self.coords.loc[ind_c, ['center_x']] = c_x
            self.coords.loc[ind_c, ['center_y']] = c_y

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


class SlideAnnotationView(wx.Frame):
    def __init__(self):
        title = 'Slide Annotation'
        frame_style = wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.RESIZE_BORDER | \
                      wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | \
                      wx.CLIP_CHILDREN
        frame_size = 1400, 900  # width, height

        super().__init__(parent=None, title=title, style=frame_style,
                         size=frame_size)

        self.SetMinSize(frame_size)

        self.imageAnnotationP = ImageAnnotationPanel(self)
        self.buttonP = ButtonPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.imageAnnotationP, flag=wx.EXPAND, proportion=1)
        sizer.Add(self.buttonP, flag=wx.CENTER | wx.ALIGN_CENTER | wx.ALL,
                  border=10)

        self.SetSizer(sizer)
        self.SetUpShortcuts()
        self.SetUpButtons()

    def SetUpShortcuts(self):
        prevId = wx.NewId()
        nextId = wx.NewId()
        saveId = wx.NewId()

        self.Bind(wx.EVT_MENU, self.OnPrev, id=prevId)
        self.Bind(wx.EVT_MENU, self.OnNext, id=nextId)
        self.Bind(wx.EVT_MENU, self.OnSave, id=saveId)

        accel = wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, ord('Q'), prevId),
            (wx.ACCEL_NORMAL, ord('E'), nextId),
            (wx.ACCEL_CTRL, ord('S'), saveId)
        ])
        self.SetAcceleratorTable(accel)

    def SetUpButtons(self):
        self.buttonP.prevBtn.Bind(wx.EVT_BUTTON, self.OnPrev)
        self.buttonP.nextBtn.Bind(wx.EVT_BUTTON, self.OnNext)

        self.buttonP.saveBtn.Bind(wx.EVT_BUTTON, self.OnSave)
        self.buttonP.doneBtn.Bind(wx.EVT_BUTTON, self.OnDone)

    # === BUTTON ACTIONS ===================================================== #

    def OnPrev(self, event):
        self.OnSave(event, do_after='prev')

    def OnNext(self, event):
        self.OnSave(event, do_after='next')

    def OnSave(self, event, do_after=None):
        # slide = self.imageAnnotationP.interactorsP.GetInteractorsParams()
        slide = None
        # TODO: merge with slide
        pub.sendMessage('update', slide=slide, do_after=do_after)

    def OnDone(self, event):
        self.OnSave(event)
        self.Close()

    def UpdateSequenceButtons(self, prev, next):
        if prev:
            self.buttonP.prevBtn.Enable()
        else:
            self.buttonP.prevBtn.Disable()

        if next:
            self.buttonP.nextBtn.Enable()
        else:
            self.buttonP.nextBtn.Disable()

    # === GUI ACTIONS ======================================================== #

    def SetImageTitle(self, title):
        self.imageAnnotationP.title.SetLabel(title)

    def SetInteractors(self, *args, **kwargs):
        self.imageAnnotationP.interactorsP.SetInteractors(*args, **kwargs)

    def SetImage(self, image):
        self.imageAnnotationP.interactorsP.Render(image)

    def Draw(self):
        self.imageAnnotationP.interactorsP.canvas.draw()


class SlideAnnotationController:
    def __init__(self, coords, angles):
        self.view = SlideAnnotationView()
        self.view.Show()

        # from view to controller
        pub.subscribe(self.update, 'update')

        self.model = SlideAnnotationModel(coords, angles)

    def render(self):
        slide = self.model.get()

        self.view.SetImageTitle(slide['title'])
        self.view.SetImage(slide['image'])

        self.view.UpdateSequenceButtons(prev=not self.model.is_first(),
                                        next=not self.model.is_last())
        self.view.Draw()

    def update(self, slide, do_after=None):
        # self.model.update(slide)

        if do_after == 'prev':
            self.model.prev()
        elif do_after == 'next':
            self.model.next()

        # TODO: find better name for this function, it does two things here
        if do_after is not None:
            self.render()


def annotate_slides(*args, **kwargs):
    app = wx.App()
    controller = SlideAnnotationController(*args, **kwargs)
    controller.render()
    app.MainLoop()
