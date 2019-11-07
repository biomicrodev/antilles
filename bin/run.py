import logging.config

from antilles.pipeline.extract import Extractor
from antilles.utils import profile

logging.config.fileConfig('../logging.ini')
log = logging.getLogger(__name__)


@profile(log=log)
def main():
    project_name = 'TEST'
    block_name = 'BLK1'

    step = 0

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
        extractor = Extractor(project_name, block_name)
        # extractor.adjust()
        extractor.extract(params)

    # === FINE ADJUST ======================================================== #
    elif step == 1:
        pass

    # === ANALYZE ============================================================ #
    elif step == 2:
        pass


if __name__ == '__main__':
    main()
