import json
import logging
from enum import Enum
from os.path import join, dirname, basename
from typing import List, Dict, Any

import pandas
from PIL import Image

from .utils import upsert
from .utils.image import get_slide_dims
from .utils.io import DAO, get_sample_prefix
from .utils.math import init_arrow_coords
from .wholeslideimage import WholeSlideImage


class Field(Enum):
    ANGLES_COARSE = "ANGLES_COARSE"
    IMAGES_COORDS = "IMAGES_COORDS"  # IMAGES_COORDS
    IMAGES_COORDS_BOW = "IMAGES_COORDS_BOW"  # IMAGES_COORDS_BOW
    CELLPROFILER_IMAGE_INPUT = "CELLPROFILER_IMAGE_INPUT"  # CELLPROFILER_INPUT

    REGIONS_COORDS_BOW = "REGIONS_COORDS_BOW"  # REGIONS_COORDS_BOW
    CELLPROFILER_REGION_INPUT = "CELLPROFILER_REGION_INPUT"


class Step(Enum):
    S0 = "0_slides"
    S1 = "1_regions"
    S2 = "2_regions_{mode}"


columns = [
    "relpath",
    "project",
    "block",
    "level",
    "sample",
    "cohorts",
    "panel",
    "center_x",
    "center_y",
]
columns_sort_by = ["block", "level", "sample", "panel"]
columns_upsert = {
    Field.IMAGES_COORDS: ["project", "block", "panel", "level", "sample", "cohorts"],
    Field.ANGLES_COARSE: ["sample"],
    Field.IMAGES_COORDS_BOW: [],
}


def unpack(block: Dict[str, Any]) -> List[Dict[str, Any]]:
    samples = []

    b_samples = block["samples"]
    if isinstance(b_samples, int):
        if "device" not in block.keys():
            raise ValueError("Device not specified for block!")

        cohorts = block.get("cohorts", None)

        for s in range(b_samples):
            samples.append(
                {
                    "name": get_sample_prefix() + str(s + 1),
                    "device": block["device"],
                    "cohorts": cohorts,
                }
            )

    elif isinstance(b_samples, list):
        device = block.get("device", None)
        block_cohorts = block.get("cohorts", None)

        for s in b_samples:
            if isinstance(s, dict):
                if "name" not in s.keys():
                    raise ValueError("Sample name not specified!")
                if device is None and "device" not in s.keys():
                    raise ValueError("Device not specified!")
                sample_cohorts = s.get("cohorts", None)
                cohorts = sample_cohorts or block_cohorts
                if cohorts is None:
                    raise ValueError(
                        f"Cohorts must be specified for sample {s['name']}!"
                    )

                samples.append(
                    {
                        "name": s["name"],
                        "device": s["device"] if device is None else device,
                        "cohorts": cohorts,
                    }
                )

            elif isinstance(s, str):
                if device is None:
                    raise ValueError("Device not specified!")

                samples.append({"name": s, "device": device, "cohorts": block_cohorts})

            else:
                raise ValueError("Unknown sample type!")

    return samples


def init_coords_slides(
    slides: List[WholeSlideImage], samples: List[Dict[str, Any]]
) -> pandas.DataFrame:
    df = []
    for slide in slides:
        dims = get_slide_dims(slide.relpath)
        coords = list(init_arrow_coords(dims, len(samples)))
        for i, sample in enumerate(samples):
            df.append(
                {
                    **slide.to_dict(),
                    **{
                        "sample": str(sample["name"]),
                        "cohorts": json.dumps(sample["cohorts"]),
                        "center_x": coords[i][0],
                        "center_y": coords[i][1],
                    },
                }
            )

    df = pandas.DataFrame.from_records(df, columns=columns)
    df = df.sort_values(by=columns_sort_by)
    df.index = range(len(df))
    df["level"] = df["level"].astype(int)
    return df


def init_angles_coarse(samples: List[Dict[str, Any]]) -> pandas.DataFrame:
    df = [{"sample": s["name"], "angle": -90.0} for s in samples]
    df = pandas.DataFrame(df, columns=["sample", "angle"])
    df.index = range(len(df))
    return df


def init_coords_bows(regions: List[Dict[str, Any]]) -> pandas.DataFrame:
    columns = [
        "relpath",
        "project",
        "block",
        "panel",
        "level",
        "sample",
        "cohorts",
        "drug",
        "origin_x",
        "origin_y",
        "center_x",
        "center_y",
        "well_x",
        "well_y",
        "mpp",
        "metadata",
    ]

    for region in regions:
        with Image.open(DAO.abs(region["relpath"])) as obj:
            x, y = obj.size
        region["origin_x"] = 0
        region["origin_y"] = 0
        region["center_x"] = int(round(x / 2))
        region["center_y"] = int(round(y / 2))
        region["well_x"] = int(round(x / 2 + x / 10))
        region["well_y"] = int(round(y / 2))
        region["mpp"] = 0
        region["metadata"] = json.dumps({})

    df = pandas.DataFrame(regions, columns=columns)
    df = df.sort_values(by=["project", "block", "panel", "level", "sample", "drug"])
    return df


def get_step_dir(step: Step, **kwargs) -> str:
    assert step.name in Step.__members__.keys()
    if step == Step.S1:
        s = Step.S1.value
    elif step == Step.S2:
        s = Step.S2.value.format(**kwargs)
    else:
        raise NotImplementedError("Unsupported step!")
    return s


class Block:
    def __init__(self, block: Dict[str, Any], project):
        """
        A Block is a directory initially containing three subdirectories:
          1. 'annotations', containing csv files of where regions are
          2. '0_images', containing whole-slide images.
          3. '0_regions', containing regions.

        This class manages access to the three items above.
        """
        self.log = logging.getLogger(__name__)

        self.name = block["name"]
        self.samples = unpack(block)
        self.project = project

        sample_names = (s["name"] for s in self.samples)
        self.log.info(f"Samples in block {self.name}: " + ", ".join(sample_names))

    @property
    def relpath(self) -> str:
        return join(self.project.relpath, self.name)

    @property
    def images(self) -> List[WholeSlideImage]:
        dirpath = join(self.relpath, Step.S0.value)
        regex = self.project.image_regex

        images = []
        for filename in DAO.list_files(dirpath):
            match = regex.fullmatch(filename)
            if match:
                image = WholeSlideImage(**match.groupdict())
                image.relpath = join(dirpath, filename)
                images.append(image)
        return images

    @property
    def regions(self) -> List[Dict[str, Any]]:
        dirpath = join(self.relpath, "0_regions")
        regex = self.project.region_regex

        images = []
        for relpath in DAO.list_files_recursively(dirpath):
            filename = basename(relpath)
            match = regex.fullmatch(filename)
            if match:
                image = match.groupdict()
                image["relpath"] = relpath
                images.append(image)
        return images

    def init(self, field: Field) -> pandas.DataFrame:
        if field == Field.IMAGES_COORDS:
            return init_coords_slides(self.images, self.samples)
        elif field == Field.ANGLES_COARSE:
            return init_angles_coarse(self.samples)
        else:
            return pandas.DataFrame()

    def get(self, field: Field) -> pandas.DataFrame:
        filename = join("annotations", f"{field.value}.csv")
        filepath = join(self.relpath, filename)

        if field == Field.IMAGES_COORDS:
            df_init = init_coords_slides(self.images, self.samples)
            if DAO.is_file(filepath):
                df = DAO.read_csv(filepath)
                df["sample"] = df["sample"].astype(str)
                df = upsert(df_init, using=df, cols=columns_upsert[field])
                return df
            else:
                return df_init

        elif field == Field.ANGLES_COARSE:
            df_init = init_angles_coarse(self.samples)
            if DAO.is_file(filepath):
                df = DAO.read_csv(filepath)
                df["sample"] = df["sample"].astype(str)
                df = upsert(df_init, using=df, cols=columns_upsert[field])
                return df
            else:
                return df_init

        elif field == Field.IMAGES_COORDS_BOW:
            df_init = pandas.DataFrame(
                columns=[
                    "relpath",
                    "project",
                    "block",
                    "panel",
                    "level",
                    "sample",
                    "cohorts",
                    "drug",
                    "origin_x",
                    "origin_y",
                    "center_x",
                    "center_y",
                    "well_x",
                    "well_y",
                    "mpp",
                    "metadata",
                ]
            )
            if DAO.is_file(filepath):
                df = DAO.read_csv(filepath)
                df["sample"] = df["sample"].astype(str)
                df = upsert(df_init, using=df, cols=columns_upsert[field])
                return df
            else:
                return df_init

        elif field == Field.REGIONS_COORDS_BOW:
            df_init = init_coords_bows(self.regions)
            if DAO.is_file(filepath):
                df = DAO.read_csv(filepath)
                df["sample"] = df["sample"].astype(str)
                df = upsert(df_init, using=df, cols=columns_upsert[field])
                return df
            else:
                return df_init

        else:
            raise RuntimeError(f"Unknown field {field.name}!")

    def save(self, df: pandas.DataFrame, field: Field, overwrite: bool = True):
        filename = join("annotations", f"{field.value}.csv")
        filepath = join(self.relpath, filename)

        if not DAO.is_file(filepath) or overwrite:
            DAO.make_dir(dirname(filepath))
            DAO.to_csv(df, filepath)
        else:
            self.log.info("Metadata not written.")

    def clean(self) -> None:
        DAO.rm_dir(join(self.relpath, Step.S1.value))
