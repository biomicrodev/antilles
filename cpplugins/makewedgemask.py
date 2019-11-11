import math
from typing import Tuple, List, Dict, Union, Any

import cellprofiler.gui as cpg
import cellprofiler.module as cpm
import cellprofiler.object as cpo
import cellprofiler.pipeline as cpp
import cellprofiler.setting as cps
import cellprofiler.workspace as cpw
import numpy
import skimage.color

__author__ = "Sebastian Ahn"
__doc__ = """\
MakeWedgeMask
=============

Create a mask object of the *wedge*, a region of tissue that has experienced 
biologically active substances diffused from a single well, or several nearby wells. The
wedge mask is obtained from reasonable assumptions regarding drug diffusion.

The wedge is projected normal to the surface of the void left by the device. The 
thickness of the wedge is preset to a distance indicating the extent of drug release 
based on the duration of diffusion. The span of the wedge is meant to disregard 
crosstalk from adjacent well effects.

The output of this module is a mask object that can be used by the MaskObjects 
module to count objects of interest within the mask.


See also
^^^^^^^^

See also **MaskObjects**.


Technical notes
^^^^^^^^^^^^^^^
In Matplotlib's event handling, event data is passed into callbacks through the
*events* argument. This class has x, y, xdata, and ydata as properties. Note 
that the (x,y) coordinates refer to pixel coordinates (with respect to one 
corner of the display window, usually the bottom left), and the (xdata,ydata)
coordinates refer to data coordinates (displayed by the x- and y-axes).

    Minimum cross entropy: good for readily identifiable foreground/background
    Otsu: choose between 2- or 3- class if mid-level intensities are present   
    Robust background: good for images in which most of the image_name is comprised of   
        background 

    Intensity: works best if objects are brighter at center, dimmer at edges
    Shape: works best if objects have indentations where clumps touch (esp if 
        obj are round)


References
^^^^^^^^^^
-  Jonas O, Landry HM, Fuller JE, Santini Jr JT, Baselga J, Tepper RI, Cima MJ,
    Langer R (2015) "An implantable microdevice to perform high-throughput in
    vivo drug sensitivity in tumors." *Science* 7-284.
    (`link <https://stm.sciencemag.org/content/7/284/284ra57>`_)

"""


def cart2pol(x: float, y: float, in_deg: bool = True) -> Tuple[float, float]:
    r = math.sqrt(pow(x, 2) + pow(y, 2))
    theta = math.atan2(y, x)

    if in_deg:
        theta = math.degrees(theta)

    return r, theta


def pol2cart(r: float, theta: float, in_degs: bool = True) -> Tuple[float, float]:
    if in_degs:
        theta = (theta + 180) % 360 - 180
        theta = math.radians(theta)
    else:
        theta = (theta + (math.pi / 2)) % math.pi - (math.pi / 2)

    x = r * math.cos(theta)
    y = r * math.sin(theta)

    return x, y


def merge_image_and_mask(
        image: numpy.ndarray,
        mask: numpy.ndarray,
        color: Tuple[Union[float, Any], ...] = None,
):
    if color is None:
        color = (1.0, 1.0, 1.0)

    alpha1 = 0.5
    alpha2 = 0.5

    color_mask = numpy.zeros_like(image)
    color_mask[mask] = color

    # painter's algorithm
    mixed = (image * alpha1 + color_mask * alpha2 * (1.0 - alpha1)) / (
            alpha1 + alpha2 * (1.0 - alpha1)
    )
    return mixed


def _make_mask(
        dims: Tuple[int, int],
        pos: Tuple[int, int],
        width: float,
        radius: float,
        th: float,
        hspan: float,
) -> numpy.ndarray:
    """
    This lower-level function has been somewhat optimized, so make sure to time it
    before making any changes.

    Computations are done in radians to avoid calling numpy.degrees.
    """
    w, h = dims
    x, y = pos

    th *= math.pi / 180
    hspan *= math.pi / 180

    xx, yy = numpy.meshgrid(numpy.arange(w), numpy.arange(h))
    xx -= int(x)
    yy -= int(y)
    theta = numpy.arctan2(xx, yy)

    angle = (th - theta + math.pi * 3) % (math.pi * 2) - math.pi

    d2 = xx ** 2 + yy ** 2
    radius_small = (radius - width) ** 2
    mask = (
            (radius_small <= d2)
            & (radius ** 2 >= d2)
            & (-hspan <= angle)
            & (angle <= hspan)
    )

    return mask


def make_mask(params: Dict[str, Any], dims: Tuple[int, int]) -> numpy.ndarray:
    mpp = params["mpp"]
    cx, cy = (params["center_x"], params["center_y"])
    wx, wy = (params["well_x"], params["well_y"])
    offset = params["offset"] / mpp  # to pixels
    thickness = params["thickness"] / mpp  # to pixels
    span = params["span"]

    dx, dy = wx - cx, wy - cy
    center_length, center_angle = cart2pol(dy, dx)

    return _make_mask(
        dims=dims,
        pos=(cx, cy),
        radius=center_length + offset + thickness,
        width=thickness,
        th=center_angle,
        hspan=span / 2,
    )


class MakeWedgeMask(cpm.Module):
    category = "JonasLab Custom"
    module_name = "MakeWedgeMask"
    variable_revision_number = 1

    measurements = ["center_x", "center_y", "well_x", "well_y"]

    def __init__(self):
        super().__init__()
        self.wedge = {}

    def create_settings(self):
        module_explanation = [
            """\
            Construct wedge from User-supplied parameters regarding the area of drug 
            influence around a well in tissue. Outputs a binary mask that can be used 
            by the **MaskObject** module for scoring the desired cell populations 
            within the wedge.
            """
        ]
        self.set_notes([" ".join(module_explanation)])

        image_name = cps.ImageNameSubscriber(
            text=u"Select image to visualize wedge on",
            value=cps.NONE,
            doc="""\
            Choose the image_name upon which a wedge constructed from the given
            parameters is laid. Can be either RGB or grayscale.""",
        )

        mask_name = cps.ObjectNameProvider(
            text=u"Name the wedge mask",
            value="WedgeMask",
            doc="""Enter the name of the wedge mask.""",
        )

        color = cps.Color(
            text=u"Select wedge outline color",
            value="green",
            doc="""The wedge is displayed in this color.""",
        )

        offset = cps.Float(
            text=u"Enter distance of wedge from edge of well (um)",
            value=0.0,
            doc="""""",
        )

        thickness = cps.Float(
            text=u"Enter thickness of wedge (um)", value=400.0, doc=""""""
        )

        span = cps.Float(text=u"Enter span of wedge (in deg)", value=90.0, doc="""""")

        use_custom = cps.Binary(text=u"Use custom settings?", value=False, doc="""""")

        self.wedge = {
            "image_name": image_name,
            "mask_name": mask_name,
            "color": color,
            "offset": offset,
            "thickness": thickness,
            "span": span,
            "use_custom": use_custom,
        }

    def settings(self) -> List[object]:
        names = [
            "image_name",
            "mask_name",
            "color",
            "offset",
            "thickness",
            "span",
            "use_custom",
        ]
        return [self.wedge[name] for name in names]

    def visible_settings(self) -> List[object]:
        names = ["image_name", "mask_name", "color", "use_custom"]
        if self.wedge["use_custom"].value:
            names += ["offset", "thickness", "span"]
        return [self.wedge[name] for name in names]

    def prepare_run(self, workspace: cpw.Workspace) -> bool:
        init_val: float = 0.0
        for name in self.measurements:
            workspace.measurements.add_measurement(
                object_name=cpm.IMAGE,
                feature_name="Wedge_" + name,
                data=init_val,
                data_type=cpm.COLTYPE_FLOAT,
            )

        return True

    def get_measurement_columns(self, pipeline: cpp.Pipeline) -> List:
        # add our own entry in the tree checkbox dialog
        return [
            (cpm.IMAGE, "Wedge_" + name, cpm.COLTYPE_FLOAT)
            for name in self.measurements
        ]

    def get_workspace_params(self, workspace: cpw.Workspace) -> Dict[str, object]:
        m = {}
        for name in self.measurements:
            measurement = workspace.measurements.get_current_measurement(
                cpm.IMAGE, "Metadata_Wedge_" + name
            )
            m[name] = measurement

        m["mpp"] = workspace.measurements.get_current_measurement(
            cpm.IMAGE, "Metadata_MPP"
        )

        return m

    def get_user_params(self) -> Dict[str, object]:
        m = {"offset": self.wedge["thickness"].value}
        if self.wedge["use_custom"].value:
            m["thickness"] = self.wedge["thickness"].value
            m["span"] = self.wedge["span"].value
        return m

    def get_image(self, workspace: cpw.Workspace):
        name = self.wedge["name"].value
        image = workspace.image_set.get_image(name)
        return image

    def save_mask(self, workspace: cpw.Workspace, mask: numpy.ndarray):
        mask_obj = cpo.Objects()
        mask_obj.segmented = mask
        workspace.object_set.add_objects(mask_obj, self.wedge["name"].value)

    def merge_image_and_mask(
            self, image: numpy.ndarray, mask: numpy.ndarray
    ) -> numpy.ndarray:
        alpha1 = 0.5
        alpha2 = 0.5

        color = tuple(c / 255.0 for c in self.wedge["color"].to_rgb())
        color_mask = numpy.zeros_like(image)
        color_mask[mask] = color

        # painter's algorithm
        mixed = (image * alpha1 + color_mask * alpha2 * (1.0 - alpha1)) / (
                alpha1 + alpha2 * (1.0 - alpha1)
        )
        return mixed

    def get_color(self) -> Tuple[Union[float, Any], ...]:
        return tuple(c / 255.0 for c in self.wedge["color"].to_rgb())

    def run(self, workspace: cpw.Workspace):
        params = {**self.get_workspace_params(workspace), **self.get_user_params()}
        image = self.get_image(workspace)

        dims = image.pixel_data.shape[:2]
        mask = make_mask(params, dims)
        self.save_mask(workspace, mask)

        if self.show_window:
            # data to be displayed; display_data needs to be json-serializable
            image_rgb = (
                numpy.copy(image.pixel_data)
                if image.multichannel
                else skimage.color.gray2rgb(image.pixel_data)
            )

            color = self.get_color()
            mixed_image = merge_image_and_mask(image_rgb, mask, color)
            workspace.display_data.image = mixed_image

    def display(self, workspace: cpw.Workspace, figure: cpg.Figure):
        if self.show_window:
            image = workspace.display_data.image

            figure.set_subplots((1, 1))
            figure.subplot_imshow_color(
                x=0, y=0, image=image, title="Wedge Mask", normalize=False
            )
