import json
import logging
import os
from typing import List, Dict, Any

import wx
from PIL import Image
from pandas import DataFrame
from pubsub import pub

from antilles.block import Field, Block
from antilles.gui.interactors import device2interactor
from antilles.gui.panels import ImageAnnotationPanel, ButtonPanel, MetadataPanel
from antilles.project import Project
from antilles.utils.image import get_thumbnail


def get_interactors(region: Dict[str, Any]):
    device = "BOW"
    assert device in device2interactor.keys()

    interactors = [
        {
            "id": 0,  # leaving open possibility of multiple interactors
            "cxy": (region["center_x"], region["center_y"]),
            "wxy": (region["well_x"], region["well_y"]),
            "device": device,
        }
    ]

    return interactors


class RegionBowAnnotationModel:
    def __init__(self, regions: DataFrame):
        self.regions = regions
        self.relpaths = sorted(list(set(self.regions["relpath"])))

    def get(self, index: int) -> Dict[str, Any]:
        relpath = self.relpaths[index]
        ind = self.regions["relpath"] == relpath
        region = self.regions.loc[
            ind, ["center_x", "center_y", "well_x", "well_y", "metadata"]
        ]

        title = (
            f"Region {index + 1}/{len(self.relpaths)}: " f"{os.path.basename(relpath)}"
        )
        interactors = get_interactors(region)

        return {
            "id": relpath,
            "relpath": relpath,
            "title": title,
            "interactors": interactors,
            "metadata": json.loads(region["metadata"].values[0]),
        }

    def set(self, region: Dict[str, Any]):
        ind = self.regions["relpath"] == region["id"]
        self.regions.loc[ind, ["metadata"]] = json.dumps(region["metadata"])

        for interactor in region["interactors"]:
            c_x, c_y = interactor["cxy"]
            w_x, w_y = interactor["wxy"]

            self.regions.loc[ind, ["center_x", "center_y"]] = [c_x, c_y]
            self.regions.loc[ind, ["well_x", "well_y"]] = [w_x, w_y]

    @property
    def n_regions(self) -> int:
        return len(self.regions)


class RegionBowAnnotationView(wx.Frame):
    def __init__(self):
        title = "Bow Annotation"
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

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_THIN_SASH)
        self.imageAnnotationP = ImageAnnotationPanel(splitter)
        self.metadataP = MetadataPanel(splitter)
        splitter.SplitVertically(self.imageAnnotationP, self.metadataP)
        splitter.SetMinimumPaneSize(300)  # px
        splitter.SetSashPosition(1500)
        splitter.SetSashGravity(1.0)

        self.buttonP = ButtonPanel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, flag=wx.EXPAND, proportion=1)
        sizer.Add(self.buttonP, flag=wx.ALL | wx.ALIGN_CENTER, border=5)

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

    def OnSave(self, event, do_after: str = None):
        interactors = self.GetInteractors()
        metadata = self.GetAnnotations()
        pub.sendMessage(
            "update", interactors=interactors, metadata=metadata, do_after=do_after
        )

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

    def SetImageTitle(self, title: str) -> None:
        self.imageAnnotationP.title.SetLabel(title)

    def SetInteractors(self, *args, **kwargs) -> None:
        self.imageAnnotationP.interactorsP.SetInteractors(*args, **kwargs)

    def GetInteractors(self) -> list:
        return self.imageAnnotationP.interactorsP.GetInteractors()

    def SetImage(self, image: Image) -> None:
        self.imageAnnotationP.interactorsP.Render(image)

    def SetAnnotations(self, annotations: Dict[str, Any]) -> None:
        self.metadataP.dictP.Clear()
        self.metadataP.dictP.UpsertMany(annotations)

    def GetAnnotations(self) -> Dict[str, Any]:
        return self.metadataP.dictP.GetAll()

    def Draw(self) -> None:
        self.imageAnnotationP.interactorsP.canvas.draw()


class RegionBowAnnotationPresenter:
    def __init__(self, model, view):
        self.model = model
        self.view = view
        self.state = {"ind": 0, "id": None, "factor": None}

        pub.subscribe(self.on_changed, "update")

        self.view.Show()

    @staticmethod
    def scale(interactors: list, factor: float) -> List[Dict[str, Any]]:
        for interactor in interactors:
            cx, cy = interactor["cxy"]
            cx, cy = cx * factor, cy * factor
            cx, cy = int(round(cx)), int(round(cy))
            interactor["cxy"] = cx, cy

            wx, wy = interactor["wxy"]
            wx, wy = wx * factor, wy * factor
            wx, wy = int(round(wx)), int(round(wy))
            interactor["wxy"] = wx, wy
        return interactors

    def is_first(self) -> bool:
        return self.state["ind"] == 0

    def is_last(self) -> bool:
        return self.state["ind"] == (self.model.n_regions - 1)

    def render(self) -> None:
        ind = self.state["ind"]
        region = self.model.get(ind)
        thumbnail = get_thumbnail(region["relpath"])
        self.state["id"] = region["relpath"]
        self.state["factor"] = thumbnail["factor"]

        interactors = region["interactors"]
        interactors = [
            {
                "id": a["id"],
                "label": None,
                "cxy": a["cxy"],
                "wxy": a["wxy"],
                "artist": device2interactor[a["device"]],
            }
            for a in interactors
        ]
        interactors = self.scale(interactors, 1 / self.state["factor"])

        self.view.SetInteractors(interactors)
        self.view.SetImageTitle(region["title"])
        self.view.SetImage(thumbnail["image"])
        self.view.SetAnnotations(region["metadata"])

        self.view.UpdateSequenceButtons(first=self.is_first(), last=self.is_last())
        self.view.Draw()

    def on_changed(
        self, interactors: list, metadata: Dict[str, Any], do_after: str = None
    ):
        interactors = self.scale(interactors, self.state["factor"])
        region = {
            "id": self.state["id"],
            "interactors": interactors,
            "metadata": metadata,
        }
        self.model.set(region)

        if do_after == "prev" and not self.is_first():
            self.state["ind"] -= 1
            self.render()
        elif do_after == "next" and not self.is_last():
            self.state["ind"] += 1
            self.render()


def adjust_regions(*args, **kwargs) -> None:
    model = RegionBowAnnotationModel(*args, **kwargs)

    app = wx.App()
    view = RegionBowAnnotationView()
    presenter = RegionBowAnnotationPresenter(model=model, view=view)
    presenter.render()

    app.MainLoop()


class Adjuster:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self) -> None:
        regions = self.block.get(Field.IMAGES_COORDS_BOW)

        adjust_regions(regions)

        self.block.save(regions, Field.IMAGES_COORDS_BOW)


class RegionAdjuster:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self) -> None:
        regions = self.block.get(Field.REGIONS_COORDS_BOW)

        adjust_regions(regions)

        self.block.save(regions, Field.REGIONS_COORDS_BOW)
