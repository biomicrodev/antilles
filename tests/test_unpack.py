import json
import unittest

from antilles.block import unpack


class TestBlockUnpack(unittest.TestCase):
    def setUp(self):
        with open("./assets/project1.json") as file:
            self.project1 = json.load(file)
        with open("./assets/project2.json") as file:
            self.project2 = json.load(file)
        with open("./assets/project3.json") as file:
            self.project3 = json.load(file)

    def test_unpack_01(self):
        block = self.project1['block']
        sample = self.project1['samples']
        self.assertEqual(unpack(block), sample)

    def test_unpack_02(self):
        block = self.project2['block']
        sample = self.project2['samples']
        self.assertEqual(unpack(block), sample)

    def test_unpack_03(self):
        block = self.project3['block']
        sample = self.project3['samples']
        self.assertEqual(unpack(block), sample)


if __name__ == '__main__':
    unittest.main()
