import json
import os

import pandas

CONFIG = "../config.json"


def get_basepath():
    with open(CONFIG) as file:
        return json.load(file)['basepath']


BASEPATH = get_basepath()


def get_sample_prefix():
    default_sample_prefix = 'SMP'
    with open(CONFIG) as file:
        return json.load(file).get('sample_prefix', default_sample_prefix)


class DAO:
    @staticmethod
    def abs(path):
        return os.path.join(BASEPATH, path)

    @staticmethod
    def read_csv(path):
        return pandas.read_csv(DAO.abs(path))

    @staticmethod
    def to_csv(df, path):
        df.to_csv(DAO.abs(path), index=False)

    @staticmethod
    def list_folders(path):
        abspath = DAO.abs(path)
        return [f for f in os.listdir(abspath)
                if os.path.isdir(os.path.join(abspath, f))]

    @staticmethod
    def list_files(path):
        abspath = DAO.abs(path)
        return [f for f in os.listdir(abspath)
                if os.path.isfile(os.path.join(abspath, f))]

    @staticmethod
    def is_file(path):
        return os.path.isfile(path)

    @staticmethod
    def make_dir(path):
        os.makedirs(DAO.abs(path), exist_ok=True)
