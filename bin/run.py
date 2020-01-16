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
    project_name = "HUMANIZED"
    block_name = "BLK2"

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
                "span": 90.0,  # degrees
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
