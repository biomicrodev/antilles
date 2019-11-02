from antilles.block import Field
from antilles.pipeline.annotate import annotate_slides
from antilles.project import Project


class Extractor:
    def __init__(self, project_name, block_name):
        self.project = Project(project_name)
        self.block = self.project.block(block_name)

    def adjust(self):
        positions = self.block.get_coords_slides()
        angles = self.block.get_angles_coarse()

        annotate_slides(positions, angles)

        self.block.save(positions, Field.COORDS_SLIDES)
        self.block.save(angles, Field.ANGLES_COARSE)

    def extract(self, params):
        pass
