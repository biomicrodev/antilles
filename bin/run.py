import logging.config

from antilles.pipeline.adjust import Adjuster
from antilles.pipeline.analyze import Analyzer
from antilles.pipeline.extract import Extractor
from antilles.project import Project
from antilles.utils import profile

logging.config.fileConfig('../logging.ini')
log = logging.getLogger(__name__)


@profile(log=log)
def main():
    project_name = 'TEST'
    block_name = 'BLK1'

    step = 1
    project = Project(project_name)
    block = project.block(block_name)

    # === COARSE ADJUST & EXTRACT ============================================ #
    if step == 0:
        params = {
            'wedge': {
                'span': 90.0,  # degrees
                'radius_inner': 400,  # microns
                'radius_outer': 1200  # microns
            }
        }

        # These parameters are not for analysis; these values are used to
        # compute a reasonable buffer around the region of interest.
        extractor = Extractor(project, block)
        extractor.adjust()
        # extractor.extract(params)

    # === FINE ADJUST ======================================================== #
    elif step == 1:
        adjuster = Adjuster(project, block)
        adjuster.run()

    # === ANALYZE ============================================================ #
    elif step == 2:
        params = {}

        analyzer = Analyzer(project, block)
        analyzer.run(params)


if __name__ == '__main__':
    main()
