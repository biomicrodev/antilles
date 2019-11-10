import json
import logging
from functools import reduce
from os.path import join
from typing import Tuple, Iterator, List

import numpy
import openslide
import pandas
from pandas import DataFrame

from antilles.block import Field, Step, Block
from antilles.pipeline.annotate import annotate_slides
from antilles.project import Project
from antilles.utils import upsert
from antilles.utils.image import get_mpp_from_openslide
from antilles.utils.io import DAO
from antilles.utils.math import pol2cart


def calc_bbox(dims: Tuple[float, float],
              center: Tuple[int, int],
              angle: float,
              **kwargs) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    width, height = dims
    c_x, c_y = center
    span = kwargs.get('span', 90.0)
    radius_inner = kwargs.get('radius_inner', 400)
    radius_outer = kwargs.get('radius_outer', 800)

    n_divisions = 200
    n_div0 = int(n_divisions * float(span) / 360.0)
    n_div1 = n_divisions - n_div0

    hspan = span / 2.0
    angles0 = numpy.linspace(angle - hspan, angle + hspan, n_div0)
    angles1 = numpy.linspace(angle + hspan, angle + 360 - hspan, n_div1)

    min_dx, max_dx = None, None
    min_dy, max_dy = None, None

    for r, angles in zip([radius_outer, radius_inner], [angles0, angles1]):
        for a in angles:
            dx, dy = pol2cart(r, a)

            if min_dx is None:
                min_dx = dx
            if max_dx is None:
                max_dx = dx

            if min_dy is None:
                min_dy = dy
            if max_dy is None:
                max_dy = dy

            min_dx, max_dx = min(min_dx, dx), max(max_dx, dx)
            min_dy, max_dy = min(min_dy, dy), max(max_dy, dy)

    min_x = int(max(c_x + min_dx, 0))
    max_x = int(min(c_x + max_dx, width))
    dx = max_x - min_x

    min_y = int(max(c_y + min_dy, 0))
    max_y = int(min(c_y + max_dy, height))
    dy = max_y - min_y

    return (min_x, min_y), (dx, dy)


def get_extraction_sequence(settings: dict) -> Iterator[dict]:
    for key in ['samples', 'devices', 'coords', 'angles']:
        if key not in settings.keys():
            raise ValueError(f'Key not found: {key}')

    regions = settings['coords'].to_dict('records')
    sample_angles = settings['angles'].to_dict('records')
    sample_angles = {s['sample']: float(s['angle']) for s in sample_angles}

    for region in regions:
        # get wells from payload
        device_name = next(s['device'] for s in settings['samples']
                           if s['name'] == region['sample'])
        payload = next(d['payload'] for d in settings['devices']
                       if d['name'] == device_name)
        wells = next(l['wells'] for l in payload
                     if l['level'] == region['level'])

        src = region['relpath']

        for well in wells:
            fields = {
                'project': region['project'],
                'block': region['block'],
                'panel': region['panel'],
                'level': region['level'],
                'sample': region['sample'],
                'drug': well['drug']}

            params = {
                'center': (int(region['center_x']),
                           int(region['center_y'])),
                'angle': sample_angles[region['sample']] + well['angle']}

            yield {'src': src,
                   'fields': fields,
                   'params': params}


def microns2pixels(dct: dict, keys: List[str], mpp: float):
    for key in keys:
        try:
            dct[key] /= mpp
        except TypeError:
            pass
    return dct


def get_filepath(step: Step, fields: dict, output_order: List[str]) -> str:
    for key in ['project', 'block', 'panel', 'level', 'sample', 'drug']:
        if key not in fields.keys():
            raise ValueError(f'Key not found: {key}')

    fields['level'] = 'LVL' + str(fields['level'])

    dirpath = join(fields['project'], fields['block'], step.value)
    dirpath = join(dirpath, *(fields[o] for o in output_order))
    DAO.make_dir(dirpath)

    filename_order = ['project', 'block', 'panel', 'level', 'sample', 'drug']
    filename = '_'.join(fields[f] for f in filename_order) + '.tif'
    filepath = join(dirpath, filename)

    fields['level'] = int(fields['level'][len('LVL'):])

    return filepath


def extract_image(src: str, dst: str, params: dict) -> dict:
    with openslide.OpenSlide(DAO.abs(src)) as obj:
        dims = obj.dimensions
        mpp = get_mpp_from_openslide(obj)
        params = microns2pixels(params, ['radius_inner', 'radius_outer'], mpp)
        origin, size = calc_bbox(dims=dims, **params)

        image = obj.read_region(origin, 0, size)
        image = image.convert('RGB')
        image.save(DAO.abs(dst))

    cx = params['center'][0] - origin[0]
    cy = params['center'][1] - origin[1]

    r_init = 400 / mpp
    dx, dy = pol2cart(r_init, params['angle'])
    wx, wy = int(round(cx + dx)), int(round(cy + dy))

    return {'oxy': origin,
            'cxy': (cx, cy),
            'wxy': (wx, wy),
            'dims': size}


def upsert_translate(df: DataFrame, using: DataFrame):
    cols = ['project', 'block', 'panel', 'level', 'sample', 'drug']

    df_old = df.copy()
    df = upsert(df, using, cols)

    for i, row in df.iterrows():
        ind = (row[col] == df_old[col] for col in cols)
        ind = reduce((lambda x, y: x & y), ind)
        df_row = df[ind]

        if len(df_row) == 1:
            diff_x = int(df.loc[i, ['origin_x']]) - int(df_row['origin_x'])
            diff_y = int(df.loc[i, ['origin_y']]) - int(df_row['origin_y'])
            df.loc[i, ['center_x']] = int(df_row['center_x']) - diff_x
            df.loc[i, ['center_y']] = int(df_row['center_y']) - diff_y
            df.loc[i, ['well_x']] = int(df_row['well_x']) - diff_x
            df.loc[i, ['well_y']] = int(df_row['well_y']) - diff_y

    return df


class Extractor:
    def __init__(self, project: Project, block: Block):
        self.log = logging.getLogger(__name__)
        self.project = project
        self.block = block

    def adjust(self):
        coords = self.block.get(Field.COORDS_SLIDES)
        angles = self.block.get(Field.ANGLES_COARSE)

        annotate_slides(coords, angles)

        self.block.save(coords, Field.COORDS_SLIDES)
        self.block.save(angles, Field.ANGLES_COARSE)

    def extract(self, params: dict):
        self.log.info('Extracting wedges ... ')
        self.extract_wedges(params['wedge'])
        self.log.info('Extracting wedges complete.')

    def extract_wedges(self, params: dict):
        self.block.clean()

        # regions_prev = self.block.get(Field.COORDS_BOW)
        regions = self._extract_wedges(params)
        # regions = upsert_translate(regions, using=regions_prev)

        self.block.save(regions, Field.COORDS_BOW)

    def _extract_wedges(self, params: dict) -> DataFrame:
        output_order = self.project.config['output_order']

        settings = {
            'samples': self.block.samples,
            'devices': self.project.config['devices'],
            'coords': self.block.get(Field.COORDS_SLIDES),
            'angles': self.block.get(Field.ANGLES_COARSE)
        }

        regions = []
        regions_to_extract = get_extraction_sequence(settings)
        for region in regions_to_extract:
            src = region['src']
            dst = get_filepath(Step.S1, region['fields'], output_order)
            coords = extract_image(src, dst, {**params, **region['params']})

            regions.append({**region['fields'], **{
                'relpath': dst,
                'origin_x': coords['oxy'][0],
                'origin_y': coords['oxy'][1],
                'center_x': coords['cxy'][0],
                'center_y': coords['cxy'][1],
                'well_x': coords['wxy'][0],
                'well_y': coords['wxy'][1],
                'width': coords['dims'][0],
                'height': coords['dims'][1],
                'metadata': json.dumps({})
            }})

        columns = ['relpath', 'project', 'block', 'panel', 'level', 'sample',
                   'drug', 'origin_x', 'origin_y', 'center_x', 'center_y',
                   'well_x', 'well_y', 'metadata']
        regions = pandas.DataFrame(regions, columns=columns)
        return regions
