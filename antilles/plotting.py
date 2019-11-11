import matplotlib.pyplot as plt

from antilles.block import Block
from antilles.project import Project


class Plotter:
    def __init__(self, project: Project, block: Block):
        self.project = project
        self.block = block
        self.fig: plt.Figure = plt.Figure()

    def run(self) -> None:
        plt.show()
