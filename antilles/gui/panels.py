import wx
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure


class ButtonPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent=parent)

        buttonSize = (70, 30)

        self.prevBtn = wx.Button(self, label='Prev', size=buttonSize)
        self.prevBtn.Disable()

        self.nextBtn = wx.Button(self, label='Next', size=buttonSize)
        self.nextBtn.Disable()

        self.saveBtn = wx.Button(self, label='Save', size=buttonSize)
        self.doneBtn = wx.Button(self, label='Done', size=buttonSize)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.prevBtn)
        sizer.AddSpacer(20)
        sizer.Add(self.nextBtn)
        sizer.AddSpacer(100)
        sizer.Add(self.saveBtn)
        sizer.AddSpacer(20)
        sizer.Add(self.doneBtn)
        self.SetSizer(sizer)


class BaseInteractorsPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.interactors = []
        self.factor = None
        self.image_id = None
        self.background = None

        self.BuildUI()

    def BuildUI(self):
        self.figure = Figure()
        self.axes = self.figure.add_subplot(1, 1, 1)
        self.axes.set_aspect('equal')
        self.canvas = FigureCanvas(self, id=wx.ID_ANY, figure=self.figure)
        self.figure.tight_layout()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, flag=wx.EXPAND, proportion=1)
        self.SetSizer(sizer)

        self.canvas.mpl_connect('draw_event', self.DrawCallback)
        self.canvas.mpl_connect('button_press_event', self.OnClick)
        self.canvas.mpl_connect('button_release_event', self.OnMouseButtonUp)
        self.canvas.mpl_connect('motion_notify_event', self.OnMouseMoved)
        self.canvas.mpl_connect('key_press_event', self.OnKeyPress)
        self.canvas.mpl_connect('key_release_event', self.OnKeyRelease)

    def DrawCallback(self, event):
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        for interactor in self.interactors:
            interactor.draw_callback(event)

        self.canvas.blit(self.axes.bbox)

    def OnClick(self, event):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.button_press_callback(event)

    def OnMouseButtonUp(self, event):
        if event.inaxes is not None and \
                event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.button_release_callback(event)

    def OnMouseMoved(self, event):
        if event.inaxes != self.axes:
            return

        self.UpdateInteractors(event)

    def OnKeyPress(self, event):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.key_press_event(event)

        self.UpdateInteractors(event)

    def OnKeyRelease(self, event):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.key_release_event(event)

        self.UpdateInteractors(event)

    def UpdateInteractors(self, event):
        if self.background is not None:
            self.canvas.restore_region(self.background)
        else:
            self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        for interactor in self.interactors:
            interactor.motion_notify_callback(event)
            interactor.draw_callback(event)

        self.canvas.blit(self.axes.bbox)

    def Render(self, image):
        self.axes.clear()
        self.axes.imshow(image, interpolation='lanczos', vmin=0, vmax=255)


class DevicesInteractorsPanel(BaseInteractorsPanel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def SetInteractors(self, interactors):
        self.interactors = []
        for interactor in interactors:
            args = {
                'axes': self.axes,
                'id': interactor['id'],
                'label': interactor['label'],
                'cxy': interactor['cxy'],
                'wxy': interactor['wxy']
            }
            artist = interactor['artist'](**args)
            self.interactors.append(artist)

    def GetInteractors(self):
        return [a.get_params() for a in self.interactors]

    def OnMouseMoved(self, event):
        if event.button != 1:
            return

        super().OnMouseMoved(event)

    def OnKeyPress(self, event):
        super().OnKeyPress(event)


class ImageAnnotationPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        font = wx.Font(
            pointSize=18, family=wx.FONTFAMILY_SWISS, style=wx.FONTSTYLE_NORMAL,
            weight=wx.FONTWEIGHT_NORMAL)

        self.title = wx.StaticText(self, style=wx.ST_ELLIPSIZE_MIDDLE)
        self.title.SetFont(font)

        self.interactorsP = DevicesInteractorsPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, flag=wx.EXPAND | wx.ALL, border=10)
        sizer.Add(self.interactorsP, flag=wx.EXPAND, proportion=1)

        self.SetSizer(sizer)
