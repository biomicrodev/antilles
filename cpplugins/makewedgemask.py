# coding=utf-8
import math
from typing import Tuple, List

import cellprofiler.object
import cellprofiler.setting
import numpy
import skimage.color
from cellprofiler.workspace import Workspace
from cellprofiler.module import Module

__author__ = "Sebastian Ahn"
__doc__ = """\
MakeWedgeMask
=============

Create a mask object of the *wedge*, a region of tissue that has experienced 
biologically active substances diffused from a single well, or several nearby wells. The
wedge mask is obtained from reasonable assumptions regarding drug diffusion.

The wedge is projected normal to the surface of the void left by the device.

Create a mask object of the *wedge*, a region of tissue (usually in a tumor) 
that has experienced bioactive substances (e.g. anticancer drugs, cytokines, 
mRNA) diffused from a single well. The wedge mask may be obtained directly from 
explicit measurement of imageable drug, or using reasonable parameters based on 
physico-chemical assumptions regarding its dose response effects, diffusion, 
solubility, pKa, etc. The wedge is projected normal to the surface of the void 
left by the device. The thickness of the wedge is preset to a distance 
indicating the extent of drug release based on the duration of diffusion. The 
span of the wedge is preset to disregard crosstalk from adjacent well effects.

The output of this module is a mask object that can be used by the MaskObjects 
module to count objects of interest within the mask, such as stained and 
counterstained cells


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


def make_mask(
    dims: Tuple[int, int],
    pos: Tuple[int, int],
    width: float,
    radius: float,
    th: float,
    span: float,
) -> numpy.ndarray:
    """
    This function has been somewhat optimized, so make sure to time it before
    making any changes.

    Computations are done in radians to avoid calling numpy.degrees.
    """
    w, h = dims
    x, y = pos

    th *= math.pi / 180
    span *= math.pi / 180
    hspan = span / 2

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


def make_wedge_mask_from_wedge_params(
    params: dict, dims: Tuple[int, int]
) -> numpy.ndarray:
    microns_per_pixel = params["MPP"]
    center_curvature = (params["CenterCurvatureX"], params["CenterCurvatureY"])
    center_well = (params["CenterWellX"], params["CenterWellY"])
    wedge_offset = params["Offset"] / microns_per_pixel  # to pixels
    wedge_thickness = params["Thickness"] / microns_per_pixel
    wedge_span = params["Span"]  # full span

    delta_x = center_well[0] - center_curvature[0]
    delta_y = center_well[1] - center_curvature[1]

    center_length, center_angle = cart2pol(delta_y, delta_x)

    mask = make_mask(
        dims=dims,
        pos=center_curvature,
        radius=center_length + wedge_offset + wedge_thickness,
        width=wedge_thickness,
        th=center_angle,
        span=wedge_span / 2,
    )

    return mask


class MakeWedgeMask(Module):
    category = "JonasLab Custom"
    module_name = "MakeWedgeMask"
    variable_revision_number = 1

    D_WEDGE = "Wedge"
    WEDGE_MEASUREMENT_NAMES = [
        "CenterCurvatureX",
        "CenterCurvatureY",
        "CenterWellX",
        "CenterWellY",
        "Thickness",
        "Span",
    ]
    DEFAULT_WEDGE_COLOR = "green"

    def create_settings(self) -> None:
        module_explanation = [
            "Construct wedge from User-supplied parameters regarding the "
            "area of drug influence around a well in a tumor. Outputs a binary "
            "mask that can be used by the **MaskObject** module for scoring "
            "the desired cell populations within the wedge."
        ]
        self.set_notes([" ".join(module_explanation)])

        self.image_name = cellprofiler.setting.ImageNameSubscriber(
            text=u"Select image to visualize wedge on",
            value=cellprofiler.setting.NONE,
            doc="""\
            Choose the image_name upon which a wedge constructed from the given
            parameters is laid. Can be either RGB or grayscale.""",
        )

        self.wedge_mask_name = cellprofiler.setting.ObjectNameProvider(
            text=u"Name the wedge mask",
            value="WedgeMask",
            doc="""Enter the name of the wedge mask.""",
        )

        self.wedge_color = cellprofiler.setting.Color(
            text=u"Select wedge outline color",
            value=self.DEFAULT_WEDGE_COLOR,
            doc="""The wedge is displayed in this color.""",
        )

        self.offset = cellprofiler.setting.Float(
            text=u"Enter distance of wedge from well (um)", value=0.0, doc=""""""
        )

        self.thickness = cellprofiler.setting.Float(
            text=u"Enter thickness of wedge (um)", value=400.0, doc=""""""
        )

        self.span = cellprofiler.setting.Float(
            text=u"Enter span of wedge (in deg)", value=90.0, doc=""""""
        )

        self.use_custom = cellprofiler.setting.Binary(
            text=u"Use custom settings?", value=False, doc=""""""
        )

    def settings(self) -> List:
        settings = [
            self.image_name,
            self.wedge_mask_name,
            self.wedge_color,
            self.offset,
            self.thickness,
            self.span,
            self.use_custom,
        ]

        return settings

    def visible_settings(self) -> List:
        settings = [
            self.image_name,
            self.wedge_mask_name,
            self.wedge_color,
            self.use_custom,
        ]

        if self.use_custom.value:
            settings += [self.offset, self.thickness, self.span]

        return settings

    def prepare_run(self, workspace: Workspace) -> bool:
        # prepare wedge measurements
        default_val = 0.0
        for measurement_name in self.WEDGE_MEASUREMENT_NAMES:
            workspace.measurements.add_measurement(
                cellprofiler.measurement.IMAGE,
                "_".join([self.D_WEDGE, measurement_name]),
                default_val,
                data_type=cellprofiler.measurement.COLTYPE_FLOAT,
            )

        return True

    def get_measurement_columns(self, pipeline) -> List:
        # add our own entry in the tree checkbox dialog
        columns = []
        for measurement_name in self.WEDGE_MEASUREMENT_NAMES:
            columns += [
                (
                    cellprofiler.measurement.IMAGE,
                    "_".join([self.D_WEDGE, measurement_name]),
                    cellprofiler.measurement.COLTYPE_FLOAT,
                )
            ]

        return columns

    def run(self, workspace):
        wedge_params = {}
        for measurement_name in self.WEDGE_MEASUREMENT_NAMES:
            measurement = workspace.measurements.get_current_measurement(
                cellprofiler.measurement.IMAGE,
                "_".join(["Metadata", self.D_WEDGE, measurement_name]),
            )

            wedge_params[measurement_name] = measurement

        wedge_params["Offset"] = self.offset.value
        if self.use_custom.value:
            wedge_params["Thickness"] = self.thickness.value
            wedge_params["Span"] = self.span.value

        wedge_params["MPP"] = workspace.measurements.get_current_measurement(
            cellprofiler.measurement.IMAGE, "_".join(["Metadata", "MPP"])
        )

        # store wedge mask
        image_name = self.image_name.value
        raw_image = workspace.image_set.get_image(image_name)
        image_data = raw_image.pixel_data

        wedge_mask = make_wedge_mask_from_wedge_params(
            wedge_params, image_data.shape[:2]
        )

        wedge_mask_obj = cellprofiler.object.Objects()
        wedge_mask_obj.segmented = wedge_mask
        workspace.object_set.add_objects(wedge_mask_obj, self.wedge_mask_name.value)

        if self.show_window:
            # data to be displayed; display_data needs to be json-serializable
            image_rgb = (
                numpy.copy(image_data)
                if raw_image.multichannel
                else skimage.color.gray2rgb(image_data)
            )

            alpha1 = 0.5
            alpha2 = 0.5

            color = tuple(c / 255.0 for c in self.wedge_color.to_rgb())

            color_mask = numpy.zeros_like(image_rgb)
            color_mask[wedge_mask] = color

            # painter's algorithm
            mixed = (image_rgb * alpha1 + color_mask * alpha2 * (1.0 - alpha1)) / (
                alpha1 + alpha2 * (1.0 - alpha1)
            )

            workspace.display_data.mixed = mixed

    def display(self, workspace, figure):
        if self.show_window:
            mixed = workspace.display_data.mixed

            figure.set_subplots((1, 1))
            figure.subplot_imshow_color(
                0, 0, mixed, title="Wedge Mask", normalize=False
            )
