import json
import logging
import re
from os.path import join

from antilles.block import Block
from antilles.utils.io import DAO


def validate(config):
    # TODO: add deeper key-value pair checking
    keys = ['name', 'slide_regex', 'image_regex', 'output_order', 'blocks',
            'devices']
    for key in keys:
        if key not in config.keys():
            raise ValueError(f'{key} not in project.json!')


class Project:
    filename = 'project.json'

    def __init__(self, project_name):
        """
        A Project is a directory containing a project.json file and one or more
        subdirectories, each of which represents a block belonging to the
        project.
        """
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

        return [Block(b, self) for b in blocks_p]

    def block(self, name):
        for b in self.blocks:
            if b.name == name:
                return b

        raise ValueError(f'Block {name} not found in {self.name}!')
