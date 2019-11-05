import unittest

import pandas

from antilles.utils import upsert


class TestUpsert(unittest.TestCase):
    def test_upsert_01(self):
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

    def test_upsert_02(self):
        df1 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "str1"},
            {"value1": 1, "value2": "B", "value3": "str2"},
            {"value1": 1, "value2": "C", "value3": "str3"},
            {"value1": 2, "value2": "A", "value3": "str4"},
            {"value1": 2, "value2": "B", "value3": "str5"},
            {"value1": 2, "value2": "C", "value3": "str6"},
        ])

        df2 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "str11"},
            {"value1": 1, "value2": "B", "value3": "str12"},
            {"value1": 1, "value2": "C", "value3": "str13"},
            {"value1": 2, "value2": "A", "value3": "str14"},
            {"value1": 2, "value2": "B", "value3": "str15"},
            {"value1": 2, "value2": "C", "value3": "str16"},
        ])

        df3 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "str11"},
            {"value1": 1, "value2": "B", "value3": "str12"},
            {"value1": 1, "value2": "C", "value3": "str13"},
            {"value1": 2, "value2": "A", "value3": "str14"},
            {"value1": 2, "value2": "B", "value3": "str15"},
            {"value1": 2, "value2": "C", "value3": "str16"},
        ])

        self.assertTrue(df3.equals(upsert(df1, df2, ['value1', 'value2'])))

    def test_upsert_03(self):
        df1 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "X", "value4": 0},
            {"value1": 2, "value2": "A", "value3": "X", "value4": 0},
            {"value1": 3, "value2": "A", "value3": "X", "value4": 0},
            {"value1": 4, "value2": "A", "value3": "X", "value4": 0},
        ])

        df2 = pandas.DataFrame([
            {"value1": 3, "value2": "A", "value3": "X", "value4": 3},
            {"value1": 4, "value2": "A", "value3": "X", "value4": 4},
        ])

        df3 = pandas.DataFrame([
            {"value1": 1, "value2": "A", "value3": "X", "value4": 0},
            {"value1": 2, "value2": "A", "value3": "X", "value4": 0},
            {"value1": 3, "value2": "A", "value3": "X", "value4": 3},
            {"value1": 4, "value2": "A", "value3": "X", "value4": 4},
        ])

        self.assertTrue(
            df3.equals(upsert(df1, df2, ['value1', 'value2'])))


if __name__ == '__main__':
    unittest.main()
