import logging.config
import time

from antilles.pipeline.extract import Extractor

logging.config.fileConfig('../logging.ini')
log = logging.getLogger(__name__)


def profile(func):
    def wrapper(*args, **kwargs):
        t0 = time.time()

        func(*args, **kwargs)

        t1 = time.time()
        dt = t1 - t0
        log.info(f'Elapsed time: {dt / 60:.0f}m, {dt:.2f}s')

    return wrapper


@profile
def main():
    project_name = 'TEST'
    block_name = 'BLK1'

    step = 0

    # === COARSE ADJUST & EXTRACT ============================================ #
    if step == 0:
        pass
        # These parameters are not for analysis; these values are used to
        # compute a reasonable buffer around the region of interest.
        extractor = Extractor(project_name, block_name)
        extractor.adjust()
        # extractor.run(repick=True, extract=False, params=params)

    # === FINE ADJUST ======================================================== #
    elif step == 1:
        pass

    # === ANALYZE ============================================================ #
    elif step == 2:
        pass


if __name__ == '__main__':
    main()
