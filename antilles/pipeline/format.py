import json
import logging
import os

import pandas

from antilles.block import Block, Field
from antilles.project import Project


class Formatter:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def run(self) -> None:
        regions: pandas.DataFrame = self.block.get(Field.COORDS_BOW)

        metadata = regions["metadata"]

        regions = regions[
            [
                "relpath",
                "project",
                "block",
                "panel",
                "level",
                "sample",
                "cohorts",
                "drug",
                "center_x",
                "center_y",
                "well_x",
                "well_y",
                "mpp",
            ]
        ]
        regions.insert(loc=len(regions.columns), column="Include", value=False)

        regions.rename(
            columns={
                "relpath": "Filename",
                "project": "Project",
                "block": "Block",
                "panel": "Panel",
                "level": "Level",
                "sample": "Sample",
                "cohorts": "Cohorts",
                "drug": "Drug",
                "center_x": "Bow_Center_X",
                "center_y": "Bow_Center_Y",
                "well_x": "Bow_Well_X",
                "well_y": "Bow_Well_Y",
                "mpp": "MPP",
                "metadata": "Metadata",
            },
            inplace=True,
        )
        regions["Filename"] = regions["Filename"].apply(lambda s: os.path.basename(s))
        regions["Include"] = metadata.apply(lambda s: json.loads(s)["include"])

        self.block.save(regions, Field.CELLPROFILER_INPUT)
