import logging

from antilles.block import Field
from antilles.pipeline.annotate import annotate_slides
from antilles.project import Project
from antilles.utils import profile


class Extractor:
    log = logging.getLogger(__name__)

    def __init__(self, project_name, block_name):
        self.project = Project(project_name)
        self.block = self.project.block(block_name)

    def adjust(self):
        coords = self.block.get(Field.COORDS_SLIDES)
        angles = self.block.get(Field.ANGLES_COARSE)

        annotate_slides(coords, angles)

        self.block.save(coords, Field.COORDS_SLIDES)
        self.block.save(angles, Field.ANGLES_COARSE)

    def extract(self, params):
        regions = self.extract_wedges(params['wedge'])
        # self.block.save(regions, Field.COORDS_BOW)

    @profile(log)
    def extract_wedges(self, params):
        self.log.info('Extracting regions ... ')
