import matplotlib.pyplot as plt

from .block import Block
from .project import Project


class Plotter:
    def __init__(self, project: Project, block: Block):
        self.project = project
        self.block = block
        self.fig: plt.Figure = plt.Figure()

    def run(self) -> None:
        plt.show()
