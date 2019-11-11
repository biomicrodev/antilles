from typing import Tuple, List, Any, Dict

import wx
from PIL import Image
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure

known_types = {"int": int, "float": float, "str": str}


class ButtonPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        buttonSize: Tuple[int, int] = (70, 30)

        self.prevBtn = wx.Button(self, label="Prev", size=buttonSize)
        self.prevBtn.Disable()

        self.nextBtn = wx.Button(self, label="Next", size=buttonSize)
        self.nextBtn.Disable()

        self.saveBtn = wx.Button(self, label="Save", size=buttonSize)
        self.doneBtn = wx.Button(self, label="Done", size=buttonSize)

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

        self.interactors: List = []
        self.factor = None
        self.image_id = None
        self.background = None

        self.BuildUI()

    def BuildUI(self):
        self.figure: Figure = Figure()
        self.axes: Axes = self.figure.add_subplot(1, 1, 1)
        self.axes.set_aspect("equal")
        self.canvas = FigureCanvas(self, id=wx.ID_ANY, figure=self.figure)
        self.figure.tight_layout()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, flag=wx.EXPAND, proportion=1)
        self.SetSizer(sizer)

        self.canvas.mpl_connect("draw_event", self.DrawCallback)
        self.canvas.mpl_connect("button_press_event", self.OnClick)
        self.canvas.mpl_connect("button_release_event", self.OnMouseButtonUp)
        self.canvas.mpl_connect("motion_notify_event", self.OnMouseMoved)
        self.canvas.mpl_connect("key_press_event", self.OnKeyPress)
        self.canvas.mpl_connect("key_release_event", self.OnKeyRelease)

    def DrawCallback(self, event: MouseEvent):
        self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        for interactor in self.interactors:
            interactor.draw_callback(event)

        self.canvas.blit(self.axes.bbox)

    def OnClick(self, event: MouseEvent):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.button_press_callback(event)

    def OnMouseButtonUp(self, event: MouseEvent):
        if event.inaxes is not None and event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.button_release_callback(event)

    def OnMouseMoved(self, event: MouseEvent):
        if event.inaxes != self.axes:
            return

        self.UpdateInteractors(event)

    def OnKeyPress(self, event: MouseEvent):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.key_press_event(event)

        self.UpdateInteractors(event)

    def OnKeyRelease(self, event: MouseEvent):
        if event.inaxes != self.axes:
            return
        if event.inaxes.get_navigate_mode() is not None:
            return

        for interactor in self.interactors:
            interactor.key_release_event(event)

        self.UpdateInteractors(event)

    def UpdateInteractors(self, event: MouseEvent):
        if self.background is not None:
            self.canvas.restore_region(self.background)
        else:
            self.background = self.canvas.copy_from_bbox(self.axes.bbox)

        for interactor in self.interactors:
            interactor.motion_notify_callback(event)
            interactor.draw_callback(event)

        self.canvas.blit(self.axes.bbox)

    def Render(self, image: Image):
        self.axes.clear()
        self.axes.imshow(image, interpolation="lanczos", vmin=0, vmax=255)


class DevicesInteractorsPanel(BaseInteractorsPanel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def SetInteractors(self, interactors: List[Dict[str, Any]]) -> None:
        self.interactors = []
        for interactor in interactors:
            args = {
                "axes": self.axes,
                "id": interactor["id"],
                "label": interactor["label"],
                "cxy": interactor["cxy"],
                "wxy": interactor["wxy"],
            }
            artist = interactor["artist"](**args)
            self.interactors.append(artist)

    def GetInteractors(self) -> List[Dict[str, Any]]:
        return [a.get_params() for a in self.interactors]

    def OnMouseMoved(self, event: MouseEvent):
        if event.button != 1:
            return

        super().OnMouseMoved(event)

    def OnKeyPress(self, event: MouseEvent):
        super().OnKeyPress(event)


class ImageAnnotationPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        font = wx.Font(
            pointSize=18,
            family=wx.FONTFAMILY_SWISS,
            style=wx.FONTSTYLE_NORMAL,
            weight=wx.FONTWEIGHT_NORMAL,
        )

        self.title = wx.StaticText(self, style=wx.ST_ELLIPSIZE_MIDDLE)
        self.title.SetFont(font)

        self.interactorsP = DevicesInteractorsPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.title, flag=wx.EXPAND | wx.ALL, border=10)
        sizer.Add(self.interactorsP, flag=wx.EXPAND, proportion=1)

        self.SetSizer(sizer)


class DictionaryPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.listCtrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.listCtrl.InsertColumn(0, "Key")
        self.listCtrl.InsertColumn(1, "Value", width=125)
        self.listCtrl.InsertColumn(2, "Type")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.listCtrl, flag=wx.EXPAND | wx.ALL, proportion=1, border=10)
        self.SetSizer(sizer)

    def UpsertOne(self, key: str, value: Any) -> None:
        index = self.Where(key)

        v_type = type(value).__name__
        if index != -1:
            self.listCtrl.SetItem(index, 1, str(value))
            self.listCtrl.SetItem(index, 2, v_type)
        else:
            count = self.listCtrl.GetItemCount()
            self.listCtrl.InsertItem(count, key)
            self.listCtrl.SetItem(count, 1, str(value))
            self.listCtrl.SetItem(count, 2, v_type)

    def UpsertMany(self, dct: Dict[str, Any]) -> None:
        for key, value in dct.items():
            self.UpsertOne(key, value)

    def GetOne(self, key: str) -> Any:
        index = self.Where(key)
        if index != -1:
            _, v = self.GetItemAt(index)
            return v

        else:
            raise IndexError

    def GetAll(self) -> Dict[str, Any]:
        dct = dict()

        count = self.listCtrl.GetItemCount()
        for row in range(count):
            k, v = self.GetItemAt(row)
            dct[k] = v

        return dct

    def Where(self, key: str) -> int:
        count = self.listCtrl.GetItemCount()
        keys = [
            self.listCtrl.GetItem(itemIdx=row, col=0).GetText() for row in range(count)
        ]
        index = next((i for i, k in enumerate(keys) if k == key), -1)
        return index

    def GetItemAt(self, index: int) -> Tuple[str, Any]:
        k = self.listCtrl.GetItem(itemIdx=index, col=0).GetText()
        v = self.listCtrl.GetItem(itemIdx=index, col=1).GetText()
        v_type = self.listCtrl.GetItem(itemIdx=index, col=2).GetText()

        if v_type == "bool":
            v = v == "True"
        else:
            v = known_types[v_type](v)

        return k, v

    def Clear(self) -> None:
        self.listCtrl.DeleteAllItems()


class MetadataPanel(wx.Panel):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        buttonSize = (70, 30)

        self.dictP = DictionaryPanel(self)
        self.includeBtn = wx.Button(self, label="Include?", size=buttonSize)
        self.excludeBtn = wx.Button(self, label="Exclude?", size=buttonSize)
        self.SetUpButtons()

        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(self.includeBtn, flag=wx.ALL, border=5)
        buttonSizer.Add(self.excludeBtn, flag=wx.ALL, border=5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.dictP, flag=wx.EXPAND, proportion=1)
        sizer.Add(buttonSizer, flag=wx.EXPAND | wx.ALL, border=5)
        self.SetSizer(sizer)

    def SetUpButtons(self):
        self.includeBtn.Bind(wx.EVT_BUTTON, self.OnInclude)
        self.excludeBtn.Bind(wx.EVT_BUTTON, self.OnExclude)

    def OnInclude(self, event: MouseEvent):
        self.dictP.UpsertOne("include", True)

    def OnExclude(self, event: MouseEvent):
        self.dictP.UpsertOne("include", False)
