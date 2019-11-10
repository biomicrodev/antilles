import logging

from antilles.block import Block
from antilles.project import Project


class Analyzer:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self, params: dict) -> None:
        pass
