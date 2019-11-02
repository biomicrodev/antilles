import logging
from enum import Enum
from os.path import join, dirname

import pandas

from antilles.image import get_slide_dims
from antilles.io import DAO, get_sample_prefix
from antilles.math import init_arrow_coords
from antilles.utils import upsert

columns = ['relpath', 'project', 'block', 'level', 'sample', 'panel',
           'center_x', 'center_y']
columns_sort_by = ['block', 'level', 'sample', 'panel']
columns_upsert = ['project', 'block', 'panel', 'level', 'sample']


def unpack(block):
    samples = []

    b_samples = block['samples']
    if isinstance(b_samples, int):
        if 'device' not in block.keys():
            raise ValueError('Device not specified for block!')

        cohorts = None
        if 'cohorts' in block.keys():
            cohorts = block['cohorts']

        for s in range(b_samples):
            samples.append({
                'name': get_sample_prefix() + str(s + 1),
                'device': block['device'],
                'cohorts': cohorts
            })

    elif isinstance(b_samples, list):
        device = block.get('device', None)
        cohorts = block.get('cohorts', None)

        for s in b_samples:
            if isinstance(s, dict):
                if 'name' not in s.keys():
                    raise ValueError('Sample name not specified!')
                if device is None and 'device' not in s.keys():
                    raise ValueError('Device not specified!')

                samples.append({
                    'name': s['name'],
                    'device': s['device'] if device is None else device,
                    'cohorts': cohorts
                })

            elif isinstance(s, str):
                if device is None:
                    raise ValueError('Device not specified!')

                samples.append({
                    'name': s,
                    'device': device,
                    'cohorts': cohorts
                })

            else:
                raise ValueError('Unknown sample type!')

    return samples


class Field(Enum):
    ANGLES_COARSE = 'ANGLES_COARSE'
    COORDS_SLIDES = 'COORDS_SLIDES'
    COORDS_IMAGES = 'COORDS_IMAGES'


class Block:
    def __init__(self, block, project):
        self.log = logging.getLogger(__name__)

        self.name = block['name']
        self.samples = unpack(block)
        self.project = project

        sample_names = (s['name'] for s in self.samples)
        self.log.info(f"Samples in block {self.name}: " +
                      ", ".join(sample_names))

    @property
    def relpath(self):
        return join(self.project.relpath, self.name)

    @property
    def slides(self):
        dirpath = join(self.relpath, '0_slides')
        regex = self.project.slide_regex

        slides = []
        for filename in DAO.list_files(dirpath):
            match = regex.fullmatch(filename)
            if match:
                d = match.groupdict()
                d['relpath'] = join(dirpath, filename)
                slides.append(d)
        return slides

    @property
    def images(self):
        dirpath = join(self.relpath, '0_images')
        regex = self.project.image_regex

        images = []
        for filename in DAO.list_files(dirpath):
            match = regex.fullmatch(filename)
            if match:
                d = match.groupdict()
                d['relpath'] = join(dirpath, filename)
                images.append(d)
        return images

    def init_coords_slides(self):
        df = []
        for slide in self.slides:
            dims = get_slide_dims(slide['relpath'])
            coords = init_arrow_coords(dims, len(self.samples))
            for i, sample in enumerate(self.samples):
                df.append({**slide, **{
                    'sample': sample['name'],
                    'center_x': coords[i][0],
                    'center_y': coords[i][1]
                }})

        df = pandas.DataFrame(df, columns=columns) \
            .sort_values(by=columns_sort_by)
        df.index = range(len(df))
        return df

    def get_coords_slides(self):
        filename = join('annotations', f'{Field.COORDS_SLIDES.name}.csv')
        filepath = join(self.relpath, filename)

        coords_init = self.init_coords_slides()
        if DAO.is_file(filepath):
            coords = DAO.read_csv(filepath)
            coords = upsert(coords, coords_init, columns_upsert)
            exists = True

        else:
            coords = coords_init
            exists = False

        return coords, exists

    def init_angles_coarse(self):
        df = [{'sample': s['name'], 'angle': -90} for s in self.samples]
        df = pandas.DataFrame(df, columns=['sample', 'angle'])
        df.index = range(len(df))
        return df

    def get_angles_coarse(self):
        angles_init = self.init_angles_coarse()

        filename = join('annotations', f'{Field.ANGLES_COARSE.name}.csv')
        filepath = join(self.relpath, filename)
        if DAO.is_file(filepath):
            angles = DAO.read_csv(filepath)
            angles = upsert(angles, angles_init, ['sample'])
            exists = True

        else:
            angles = angles_init
            exists = False

        return angles, exists

    def save(self, df, field, overwrite=True):
        filename = join('annotations', f'{field.name}.csv')
        filepath = join(self.relpath, filename)

        if not DAO.is_file(filepath) or overwrite:
            DAO.make_dir(dirname(filepath))
            DAO.to_csv(df, filepath)
        else:
            print('Metadata not written.')
