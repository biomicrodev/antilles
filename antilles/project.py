import json
import logging
import re
from os.path import join

from antilles.block import Block

from antilles.io import DAO, get_sample_prefix


def validate(config):
    keys = ['name', 'slide_regex', 'image_regex', 'output_order', 'blocks',
            'devices']
    for key in keys:
        if key not in config.keys():
            raise ValueError(f'{key} not in project.json!')


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


class Project:
    filename = 'project.json'

    def __init__(self, project_name):
        self.log = logging.getLogger(__name__)

        self.name = project_name

        block_names_os = DAO.list_folders(self.relpath)
        block_names_conf = (b['name'] for b in self.config['blocks'])

        self.log.info(f"Project {self.name} init")
        self.log.info("Blocks on file system: " + ", ".join(block_names_os))
        self.log.info("Blocks in json file: " + ", ".join(block_names_conf))

    @property
    def relpath(self):
        return self.name

    @property
    def config(self):
        filepath = join(self.relpath, self.filename)
        with open(DAO.abs(filepath)) as file:
            config = json.load(file)
            validate(config)
            return config

    @property
    def image_regex(self):
        regex = self.config['image_regex']
        return re.compile(regex)

    @property
    def slide_regex(self):
        regex = self.config['slide_regex']
        return re.compile(regex)

    @property
    def blocks(self):
        blocks_os = DAO.list_folders(self.relpath)
        blocks_p = self.config['blocks']

        if set(blocks_os) != set(b['name'] for b in blocks_p):
            raise ValueError('Blocks in file system and blocks in '
                             'project.json do not match!')

        blocks = []
        for name in blocks_os:
            samples = next(unpack(b) for b in blocks_p if b['name'] == name)
            blocks.append(Block(name, self, samples))

        return blocks

    def block(self, name):
        for b in self.blocks:
            if b.name == name:
                return b

        raise ValueError(f'Block {name} not found in {self.name}!')
