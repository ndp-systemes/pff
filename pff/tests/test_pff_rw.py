# -*- coding: utf8 -*-
#
# Copyright (C) 2019 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import unittest
from StringIO import StringIO
from datetime import date
from pff import PFFWriter, PFFReader, PFFLine, PFFCell, ContentOverflow


class TestPFFRW(unittest.TestCase):
    def setUp(self):
        super(TestPFFRW, self).setUp()

        # Setup
        self.virtual_file = StringIO()
        name_cell = PFFCell('name', 8)
        age_cell = PFFCell('age', 3, type=int)
        score_cell = PFFCell('score', 8, type=float, align='l', filler='#', default='418.0')
        birth_cell = PFFCell('birthday', 10)
        favourite_pokemon_cell = PFFCell('favourite', 128, align='r', default="Evoli")
        town_cell = PFFCell('town', 16)
        region_cell = PFFCell('region', 16)

        # Lines
        self.short_line = PFFLine(name_cell, age_cell, score_cell)
        self.long_line = PFFLine(name_cell, age_cell, birth_cell, favourite_pokemon_cell)
        self.other_line = PFFLine(town_cell, region_cell)

        # Writer
        self.writer = PFFWriter(self.virtual_file, [self.short_line, self.long_line])
        # Reader
        self.reader = PFFReader(self.virtual_file, [self.short_line, self.long_line])


class TestPFFWrite(TestPFFRW):
    def test_00_default_write_is_ok(self):
        self.writer.writerow({'name': "Sacha", 'age': 11, 'score': 42.0})
        self.assertEqual(self.virtual_file.getvalue(), "Sacha   01142.0####\n")

    def test_01_force_line_model(self):
        self.writer.writerow({'name': "Sacha", 'age': 11, 'birthday': date(1996, 2, 27), 'favourite': "Pikachu"},
                             self.long_line)
        self.assertEqual(self.virtual_file.getvalue(), "Sacha   0111996-02-27" + " " * 120 + " Pikachu\n")

    def test_02_change_chose_line_model(self):
        self.writer.chose_line_model = lambda vals: self.writer._lines[1]
        self.writer.writerow({'name': "Sacha", 'age': 11, 'birthday': date(1996, 2, 27), 'favourite': "Pikachu"})
        self.assertEqual(self.virtual_file.getvalue(), "Sacha   0111996-02-27" + " " * 120 + " Pikachu\n")

    def test_03_default_value_when_none_given(self):
        self.writer.writerow({'name': "Sacha", 'age': 11})
        self.assertEqual(self.virtual_file.getvalue(), "Sacha   011418.0###\n")

    def test_04_content_overflow_is_not_raised_by_default(self):
        self.writer.writerow({'name': "La team Rocket", 'age': 11, 'score': 7.0}, self.short_line)
        self.assertEqual(self.virtual_file.getvalue(), "La team 0117.0#####\n")

    def test_05_autotruncates_prevents_content_overflow(self):
        special_writer = PFFWriter(self.virtual_file, [self.short_line, self.long_line], autotruncate=False)
        with self.assertRaises(ContentOverflow):
            special_writer.writerow({'name': "La team Rocket", 'age': 11, 'score': 7.0}, self.short_line)


class TestPFFRead(TestPFFRW):
    def test_00_read_standard_line(self):
        self.virtual_file.write("Sacha   01142.0####\n")
        self.virtual_file.seek(0)
        cur_dict = self.reader.readline()
        self.assertDictEqual(cur_dict, {'name': "Sacha", 'age': 11, 'score': 42.0})

    def test_01_force_line_model(self):
        self.virtual_file.write("Sacha   0111996-02-27" + " " * 120 + " Pikachu\n")
        self.virtual_file.seek(0)
        cur_dict = self.reader.readline(self.long_line)
        self.assertDictEqual(cur_dict,
                             {'name': "Sacha", 'age': 11, 'birthday': '1996-02-27', 'favourite': "Pikachu"})

    def test_02_change_chose_line_model(self):
        self.virtual_file.write("Sacha   0111996-02-27" + " " * 120 + " Pikachu\n")
        self.virtual_file.seek(0)
        self.reader.chose_line_model = lambda line: self.reader._lines[1]
        cur_dict = self.reader.readline()
        self.assertDictEqual(cur_dict,
                             {'name': "Sacha", 'age': 11, 'birthday': '1996-02-27', 'favourite': "Pikachu"})


class TestPFFOperatorOverload(unittest.TestCase):
    def setUp(self):
        super(TestPFFOperatorOverload, self).setUp()

        self.name_cell = PFFCell('name', 8)
        self.age_cell = PFFCell('age', 3, type=int)
        self.score_cell = PFFCell('score', 8, type=float, align='l', filler='#', default='418.0')
        self.birth_cell = PFFCell('birthday', 10)

    def test_00_cell_equality(self):
        self.assertEqual(PFFCell('name', 8), PFFCell('name', 8))
        self.assertNotEqual(PFFCell('name', 8), PFFCell('name', 4))
        self.assertNotEqual(PFFCell('name', 8), PFFCell('eman', 8))

    def test_01_line_equality(self):
        self.assertEqual(PFFLine(self.name_cell, self.age_cell, self.birth_cell),
                         PFFLine(self.name_cell, self.age_cell, self.birth_cell))
        self.assertNotEqual(PFFLine(self.name_cell, self.age_cell, self.birth_cell),
                            PFFLine(self.name_cell, self.age_cell))
        self.assertNotEqual(PFFLine(self.name_cell, self.age_cell, self.birth_cell),
                            PFFLine(self.name_cell, self.age_cell, self.score_cell))
        self.assertNotEqual(PFFLine(self.name_cell, self.age_cell, self.birth_cell),
                            PFFLine(self.name_cell, self.birth_cell, self.age_cell))

    def test_10_cell_addition(self):
        self.assertEqual(self.name_cell + self.age_cell, PFFLine(self.name_cell, self.age_cell))
        self.assertEqual(self.name_cell + PFFLine(self.age_cell, self.birth_cell),
                         PFFLine(self.name_cell, self.age_cell, self.birth_cell))

    def test_11_line_addition(self):
        line = PFFLine(self.name_cell, self.age_cell)

        self.assertEqual(line + self.birth_cell, PFFLine(self.name_cell, self.age_cell, self.birth_cell))
        self.assertEqual(line + PFFLine(self.birth_cell, self.score_cell),
                         PFFLine(self.name_cell, self.age_cell, self.birth_cell, self.score_cell))

    def test_12_line_with_cell_added(self):
        line = PFFLine(self.name_cell, self.age_cell)
        line += self.birth_cell

        self.assertEqual(line, PFFLine(self.name_cell, self.age_cell, self.birth_cell))

    def test_13_line_with_line_added(self):
        line = PFFLine(self.name_cell, self.age_cell)
        line += PFFLine(self.birth_cell, self.score_cell)
        self.assertEqual(line, PFFLine(self.name_cell, self.age_cell, self.birth_cell, self.score_cell))


if __name__ == '__main__':
    unittest.main()
