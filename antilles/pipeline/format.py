import logging

import pandas

from antilles.block import Block, Field
from antilles.project import Project
from antilles.utils.io import DAO


class Formatter:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self) -> None:
        regions: pandas.DataFrame = self.block.get(Field.COORDS_BOW)

        regions["relpath"].apply(lambda x: DAO.abs(x))
        regions.rename(columns={"relpath": "abspath"}, inplace=True)
        print(regions)

        self.block.save(regions, Field.CELLPROFILER_INPUT)
