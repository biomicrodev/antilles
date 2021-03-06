import logging
import time
from functools import reduce
from typing import List, Iterator, Callable, Any

import pandas

log = logging.getLogger(__name__)


def flatten(l: Iterator[Any]) -> Iterator[Any]:
    """
    Thanks to this StackOverflow answer: https://stackoverflow.com/a/10824420
    """
    for i in l:
        if isinstance(i, (list, tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i


def upsert(
    update: pandas.DataFrame, using: pandas.DataFrame, cols: List[str]
) -> pandas.DataFrame:
    indices = map(lambda x: ~update[x].isin(using[x]), cols)
    indices = reduce((lambda x, y: x | y), indices)

    updated = pandas.concat([update[indices], using], ignore_index=True)
    updated = updated.sort_values(by=cols)
    updated.index = range(len(updated))

    return updated


def profile(log: logging.Logger) -> Callable:
    def wrapper(func: Callable) -> Callable:
        def _wrapper(*args, **kwargs):
            t0 = time.time()

            func(*args, **kwargs)

            t1 = time.time()
            dt = t1 - t0
            mm = int(round(dt / 60))
            ss = dt % 60
            log.info(f"Elapsed time: {mm}m, {ss:.2f}s")

        return _wrapper

    return wrapper
