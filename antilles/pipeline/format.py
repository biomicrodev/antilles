import logging

from antilles.block import Block, Field
from antilles.project import Project
from antilles.utils.io import DAO


class Formatter:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self) -> None:
        regions = self.block.get(Field.COORDS_BOW)
        regions.rename(columns={"relpath": "abspath"}, inplace=True)
        regions["abspath"].apply(lambda x: DAO.abs(x))
        print(regions)
