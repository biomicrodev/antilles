import unittest

import pandas

from antilles.utils import upsert


class TestUpsert(unittest.TestCase):
    def test_upsert(self):
        df1 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "str1"},
            {"value1": 1, "value2": "B", "value3": "str2"},
            {"value1": 1, "value2": "C", "value3": "str3"},
            {"value1": 2, "value2": "A", "value3": "str4"},
            {"value1": 2, "value2": "B", "value3": "str5"},
            {"value1": 2, "value2": "C", "value3": "str6"},
        ])

        df2 = pandas.DataFrame([
            {"value1": 2, "value2": "C", "value3": "updated_str"},
            {"value1": 2, "value2": "D", "value3": "new_str"}
        ])

        df3 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "str1"},
            {"value1": 1, "value2": "B", "value3": "str2"},
            {"value1": 1, "value2": "C", "value3": "str3"},
            {"value1": 2, "value2": "A", "value3": "str4"},
            {"value1": 2, "value2": "B", "value3": "str5"},
            {"value1": 2, "value2": "C", "value3": "updated_str"},
            {"value1": 2, "value2": "D", "value3": "new_str"},
        ])

        self.assertTrue(df3.equals(upsert(df1, df2, ['value1', 'value2'])))


if __name__ == '__main__':
    unittest.main()
