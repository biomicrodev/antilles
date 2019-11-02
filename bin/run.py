import logging.config

logging.config.fileConfig('../logging.ini')
log = logging.getLogger(__name__)


def main():
    project_name = 'TEST'
    block_name = 'BLK1'

    step = 0

    # === COARSE ADJUST & EXTRACT ============================================ #
    if step == 0:
        pass
        # These parameters are not for analysis; these values are used to
        # compute a reasonable buffer around the region of interest.
        # extractor = Extractor(project_name, block_name)
        # extractor.adjust()
        # extractor.run(repick=True, extract=False, params=params)

    # === FINE ADJUST ======================================================== #
    elif step == 1:
        pass

    # === ANALYZE ============================================================ #
    elif step == 2:
        pass


if __name__ == '__main__':
    import time

    t0 = time.time()

    main()

    t = time.time() - t0
    log.info(f'elapsed time: {t:.3f}s')
