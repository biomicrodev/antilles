import logging.config
from typing import Dict

from antilles.block import Block
from antilles.pipeline.adjust import Adjuster
from antilles.pipeline.format import Formatter
from antilles.pipeline.extract import Extractor
from antilles.plotting import Plotter
from antilles.project import Project
from antilles.utils import profile

logging.config.fileConfig("../logging.ini")
log = logging.getLogger(__name__)


@profile(log=log)
def main():
    project_name: str = "TEST"
    block_name: str = "BLK1"

    step: int = 3
    project: Project = Project(project_name)
    block: Block = project.block(block_name)

    # === COARSE ADJUST & EXTRACT ==================================================== #
    if step == 0:
        params: Dict[str, object] = {
            "wedge": {
                "span": 90.0,  # degrees
                "radius_inner": 400,  # microns
                "radius_outer": 1200,  # microns
            }
        }

        # These parameters are not for analysis; these values are used to
        # compute a reasonable buffer around the region of interest.
        extractor = Extractor(project, block)
        extractor.adjust()
        extractor.extract(params)

    # === FINE ADJUST ================================================================ #
    elif step == 1:
        adjuster = Adjuster(project, block)
        adjuster.run()

    # === PRE-FORMAT ================================================================= #
    elif step == 2:
        formatter = Formatter(project, block)
        formatter.run()

    # === VISUALIZE ================================================================== #
    elif step == 3:
        plotter = Plotter(project, block)
        plotter.run()


if __name__ == "__main__":
    main()
