"""
A script to analyze regions of drug diffusion in histological images.

1. Specify the base project folder in `config.json`.
    In config.json is a value that must be set to the path containing the projects on 
    that computer.

2. Create a project folder with the following structure:
    {PROJECT}
        {BLOCK 1}
            0_slides
                {PROJECT}_{BLOCK}_LVL{LEVEL}_{PANEL}.svs
                ...
        {BLOCK 2}
            0_slides
            ...
        ...
        project.json

3. Specify the project.json file.
    The project.json file needs to contain the following keys:
        name
        image_regex
        output_order
        blocks
        devices
    Refer to the TEST project in the lab dropbox folder for an example.

4. Within the script, set the project name, block name, and step.
    The step should be set to 0 initially.
    For the moment, I can't guarantee that changing things done in earlier steps will
    automatically propagate to future steps.

5. The first step is adjusting the angle of each sample.
    When run with step == 0, this script will display a window of the downsampled image
    of the whole-slide images in sequence. The window will also display a certain
    number of arrows, which is set by the number of samples in the project.json file.
    Because samples are almost never aligned vertically, I recommend strictly moving
    from left to right (from slide label to away from the slide label), then only if
    samples are aligned vertically, from top to bottom.

    The arrow indicates the direction in which the fiducial points. This may be the
    notch or datum, or the highest well containing doxorubicin. The identity of the
    fiducial may not matter, as long as it remains consistently applied. Note that the
    angle specified for each drug in the project.json file is relative to this angle,
    with the angle increasing in the clockwise direction.

    The angle is represented in polar coordinates, but with the theta direction
    inverted. This is because traditionally, the origin in image processing has been
    the upper left, due to the convention set in the mid-1900s where the raster scan in
    cathode ray tubes began in the upper left of the screen.

    All this step is doing is simply generating a pandas.DataFrame from the files
    whose filenames match the image_regex in the project.json file, and maintaining
    a list of the coordinates and angles of each sample per level per block.

6. The second step is extracting regions from whole slide images.
    This step is done by taking each arrow's base and tail and cropping a particular
    region of interest using the angle specified per drug in the project.json file.
    This results in a second folder for each block folder, called '1_regions'.

7. The third step is fine-tuning the bow direction for each well.
    When run with step == 2, this script will display a window of the downsampled
    region in sequence. The window will also display a single bow, whose initial
    parameters are set roughly by the first step.

    All this step is doing is simply generating a pandas.DataFrame from the first step,
    and maintaining a list of the coordinates of the center and well of each region of
    interest.

    On the right-hand side is a panel for specifying whether to include or exclude
    the well from analysis.

8. The fourth step is a transformation of the pandas.DataFrame into a format that
    CellProfiler is able to understand, which is a file called 'CELLPROFILER_IMAGE_INPUT.csv'.

    This includes changing the column names and unpacking the metadata column from a
    json object into individual columns.

9. Drag the entire 1_regions folder into the Images module in CellProfiler.
    If you are analyzing a particular panel, make sure to apply filters to the file
    list so that only the images stained with a particular panel are being analyzed.

10. Specify the regular expression within the Metadata module as '^(?P<Filename>.*)',
    and specify the CSV file from which the bow coordinates will be read
    ('CELLPROFILER_IMAGE_INPUT.csv').

    This allows each image to be linked with its corresponding metadata. Ensure that
    each piece of metadata is typed properly (coordinates are integers, etc.).

11.

"""

import logging.config

from antilles.pipeline.adjust import Adjuster
from antilles.pipeline.extract import Extractor
from antilles.pipeline.format import Formatter
from antilles.project import Project
from antilles.utils import profile

logging.config.fileConfig("../logging.ini")
log = logging.getLogger(__name__)


@profile(log=log)
def main():
    project_name = "NOVARTIS-AB"
    block_name = "BLK1"

    step = 3
    project = Project(project_name)
    block = project.block(block_name)

    # === COARSE ADJUST & EXTRACT ==================================================== #
    extractor = Extractor(project, block)
    if step == 0:
        extractor.adjust()

    elif step == 1:
        # These parameters are not for analysis; these values are used to
        # compute a reasonable buffer around the region of interest.
        params = {
            "wedge": {
                "span": 120.0,  # degrees
                "radius_inner": 400,  # microns
                "radius_outer": 1200,  # microns
            }
        }
        extractor.extract(params)

    # === FINE ADJUST ================================================================ #
    elif step == 2:
        adjuster = Adjuster(project, block)
        adjuster.run()

    # === PRE-FORMAT ================================================================= #
    elif step == 3:
        formatter = Formatter(project, block)
        formatter.run()

    # === VISUALIZE ================================================================== #
    # elif step == 4:
    #     plotter = Plotter(project, block)
    #     plotter.run()


if __name__ == "__main__":
    main()
