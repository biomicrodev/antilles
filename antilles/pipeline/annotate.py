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
from typing import Tuple, List, Dict, Any

import pandas
import wx
from PIL import Image
from pubsub import pub

from antilles.gui.interactors import device2interactor
from antilles.gui.panels import ButtonPanel, ImageAnnotationPanel
from antilles.utils.image import get_thumbnail
from antilles.utils.math import pol2cart, cart2pol


def add_dxy(x: float, y: float, l: float, a: float) -> Tuple[float, float]:
    dx, dy = pol2cart(l, a)
    dx, dy = int(round(dx)), int(round(dy))
    return x + dx, y + dy


def get_interactors(
    coords: pandas.DataFrame, angles: pandas.DataFrame
) -> List[Dict[str, Any]]:
    device = "ARROW"  # simplest indicator of direction
    assert device in device2interactor.keys()

    interactors = []
    for i, (sample, c_x, c_y) in coords.iterrows():
        angle = next(a["angle"] for a in angles if a["sample"] == sample)

        interactors.append(
            {
                "id": sample,
                "label": sample,
                "cxy": (c_x, c_y),
                "angle": angle,
                "device": device,
            }
        )

    return interactors


class SlideArrowAnnotationModel:
    def __init__(self, coords: pandas.DataFrame, angles: pandas.DataFrame):
        self.coords = coords
        self.angles = angles
        self.relpaths = self.coords["relpath"].unique()

    def get(self, index: int) -> Dict[str, Any]:
        relpath = self.relpaths[index]
        inds = self.coords["relpath"] == relpath
        coords = self.coords.loc[inds, ["sample", "center_x", "center_y"]]
        angles = self.angles.to_dict("records")

        title = f"Slide {index + 1}/{len(self.relpaths)}: {os.path.basename(relpath)}"
        interactors = get_interactors(coords, angles)

        return {
            "id": relpath,
            "relpath": relpath,
            "title": title,
            "interactors": interactors,
        }

    def set(self, slide: Dict[str, Any]) -> None:
        relpath = slide["id"]
        interactors = slide["interactors"]

        for interactor in interactors:
            sample = interactor["id"]
            cx, cy = interactor["cxy"]
            angle = interactor["angle"]

            ind_c = (self.coords["relpath"] == relpath) & (
                self.coords["sample"] == sample
            )
            self.coords.loc[ind_c, ["center_x"]] = cx
            self.coords.loc[ind_c, ["center_y"]] = cy

            ind_s = self.angles["sample"] == sample
            self.angles.loc[ind_s, ["angle"]] = angle

    @property
    def n_slides(self) -> int:
        return len(self.relpaths)


class SlideArrowAnnotationView(wx.Frame):
    def __init__(self):
        title = "Slide Annotation"
        frame_style = (
            wx.MAXIMIZE_BOX
            | wx.MINIMIZE_BOX
            | wx.RESIZE_BORDER
            | wx.SYSTEM_MENU
            | wx.CAPTION
            | wx.CLOSE_BOX
            | wx.CLIP_CHILDREN
        )
        frame_size = 1500, 900  # width, height

        super().__init__(parent=None, title=title, style=frame_style, size=frame_size)

        self.imageAnnotationP = ImageAnnotationPanel(self)
        self.buttonP = ButtonPanel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.imageAnnotationP, flag=wx.EXPAND, proportion=1)
        sizer.Add(self.buttonP, flag=wx.CENTER | wx.ALIGN_CENTER | wx.ALL, border=10)

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

        accel = wx.AcceleratorTable(
            [
                (wx.ACCEL_NORMAL, ord("Q"), prevId),
                (wx.ACCEL_NORMAL, ord("E"), nextId),
                (wx.ACCEL_CTRL, ord("S"), saveId),
            ]
        )
        self.SetAcceleratorTable(accel)

    def SetUpButtons(self):
        self.buttonP.prevBtn.Bind(wx.EVT_BUTTON, self.OnPrev)
        self.buttonP.nextBtn.Bind(wx.EVT_BUTTON, self.OnNext)

        self.buttonP.saveBtn.Bind(wx.EVT_BUTTON, self.OnSave)
        self.buttonP.doneBtn.Bind(wx.EVT_BUTTON, self.OnDone)

    # === BUTTON ACTIONS ===================================================== #

    def OnPrev(self, event):
        self.OnSave(event, do_after="prev")

    def OnNext(self, event):
        self.OnSave(event, do_after="next")

    def OnSave(self, event, do_after=None):
        interactors = self.imageAnnotationP.interactorsP.GetInteractors()
        pub.sendMessage("update", interactors=interactors, do_after=do_after)

    def OnDone(self, event):
        self.OnSave(event)
        self.Close()

    def UpdateSequenceButtons(self, first: bool, last: bool):
        if first:
            self.buttonP.prevBtn.Disable()
        else:
            self.buttonP.prevBtn.Enable()

        if last:
            self.buttonP.nextBtn.Disable()
        else:
            self.buttonP.nextBtn.Enable()

    # === GUI ACTIONS ======================================================== #

    def SetImageTitle(self, title: str):
        self.imageAnnotationP.title.SetLabel(title)

    def SetInteractors(self, *args, **kwargs):
        self.imageAnnotationP.interactorsP.SetInteractors(*args, **kwargs)

    def SetImage(self, image: Image):
        self.imageAnnotationP.interactorsP.Render(image)

    def Draw(self):
        self.imageAnnotationP.interactorsP.canvas.draw()


class SlideArrowAnnotationPresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.state = {"ind": 0, "id": None, "factor": None}

        pub.subscribe(self.on_changed, "update")

        self.view.Show()

    @staticmethod
    def angles_to_coords(interactors: List[Dict[str, Any]]):
        length = 100  # pixels

        for interactor in interactors:
            angle = interactor.pop("angle")
            cx, cy = interactor["cxy"]

            dx, dy = pol2cart(length, angle)
            interactor["wxy"] = cx + dx, cy + dy
        return interactors

    @staticmethod
    def coords_to_angle(interactors: List[Dict[str, Any]]):
        for interactor in interactors:
            cx, cy = interactor["cxy"]
            wx, wy = interactor.pop("wxy")

            _, angle = cart2pol(wx - cx, wy - cy)
            interactor["angle"] = round(angle, 1)
        return interactors

    @staticmethod
    def scale(interactors: List[Dict[str, Any]], factor: float):
        for interactor in interactors:
            cx, cy = interactor["cxy"]
            cx, cy = cx * factor, cy * factor
            cx, cy = int(round(cx)), int(round(cy))
            interactor["cxy"] = cx, cy
        return interactors

    def is_first(self) -> bool:
        return self.state["ind"] == 0

    def is_last(self) -> bool:
        return self.state["ind"] == (self.model.n_slides - 1)

    def render(self) -> None:
        ind = self.state["ind"]
        slide = self.model.get(ind)
        thumbnail = get_thumbnail(slide["relpath"])
        self.state["id"] = slide["relpath"]
        self.state["factor"] = thumbnail["factor"]

        interactors = slide["interactors"]
        interactors = [
            {
                "id": a["id"],
                "label": a["label"],
                "cxy": a["cxy"],
                "angle": a["angle"],
                "artist": device2interactor[a["device"]],
            }
            for a in interactors
        ]
        interactors = self.scale(interactors, 1 / self.state["factor"])
        interactors = self.angles_to_coords(interactors)

        self.view.SetInteractors(interactors)
        self.view.SetImageTitle(slide["title"])
        self.view.SetImage(thumbnail["image"])

        self.view.UpdateSequenceButtons(first=self.is_first(), last=self.is_last())
        self.view.Draw()

    def on_changed(self, interactors, do_after=None):
        interactors = self.coords_to_angle(interactors)
        interactors = self.scale(interactors, self.state["factor"])
        slide = {"id": self.state["id"], "interactors": interactors}
        self.model.set(slide)

        if do_after == "prev" and not self.is_first():
            self.state["ind"] -= 1
            self.render()
        elif do_after == "next" and not self.is_last():
            self.state["ind"] += 1
            self.render()


def annotate_slides(*args, **kwargs):
    model = SlideArrowAnnotationModel(*args, **kwargs)

    app = wx.App()
    view = SlideArrowAnnotationView()
    presenter = SlideArrowAnnotationPresenter(model=model, view=view)
    presenter.render()

    app.MainLoop()
