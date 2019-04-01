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

DEFAULT_STR_FILLER_CHAR = ' '
DEFAULT_INT_FILLER_CHAR = '0'


def is_numerical(t):
    return t in (int, float, complex)


class ContentOverflow(Exception):
    """ Exception raised when the content of a `PFFCell` is larger than the cell itself """

    def __init__(self, content, cell):
        super(ContentOverflow, self).__init__()
        self._content = content
        self._cell = cell

    def __str__(self):
        return "Error: \"%s\" is longer than the cell %s (%d characters max)" %\
               (self._content, self._cell.name, self._cell.size)


class PFFWriter(object):
    """ Object to facilitate writing data in a positional file

    :param f: a file pointer, describing the file where lines will be written
    :param lines: a collection of `PFFLine`s, which will be used to format data and write them in `self.f`
    """

    def __init__(self, f, lines):
        self._lines = lines
        self._file = f
        self.lcount = 0

    def chose_line_model(self, vals):
        """ Can be overwritten
        Function to chose which line model (`PFFLine`) will be used to write the next line, with values `vals`

        By default, always takes the first line model
        """
        return self._lines[0]

    def writerow(self, vals, line_model=None):
        """ Write the row with values `vals` in the associated file

        :param vals: dict containing the row values
        :param line_model: `PFFLine` to use for this row. If None, then `self.chose_line_model` is called
        """
        line_model = line_model or self.chose_line_model(vals)
        self._file.write(line_model.write(vals) + '\n')
        self.lcount += 1


class PFFReader(object):
    """ Object to facilitate writing data in a positional file

    :param f: a file pointer, describing the file where lines will be written
    :param lines: a collection of `PFFLine`s, which will be used to format data and write them in `self.f`
    """

    def __init__(self, f, lines):
        self._lines = lines
        self._file = f
        self.lcount = 0

    def __iter__(self):
        while True:
            yield self.readline()

    def __next__(self):
        return self.readline()

    def chose_line_model(self, line):
        """ Can be overwritten
        Function to chose which line model (`PFFLine`) will be used to read the next line

        By default, always takes the first line model
        """
        return self._lines[0]

    def readline(self, line_model=None):
        """ Read a line in file `self.f`, and extract the positional data in it

        :param line_model: `PFFLine` to use for this row. If None, then `self.chose_line_model` is called
        :return: a dict associating every cell's name with their values found in line
        """
        line = self._file.readline()
        if not line:
            raise StopIteration
        line_model = line_model or self.chose_line_model(line)
        return line_model.read(line)


class PFFLine(list):
    """ An ordered collection of `PFFCell`s """

    def __init__(self, *cells):
        super(PFFLine, self).__init__(cells)

    def write(self, vals):
        """ Write values in vals in the `PFFCell`s contained in this line, and outputs a str corresponding to them

        :param vals: values to write
        :return: a str representing the line filled with correct values
        """
        line = ""
        for cell in self:
            line += cell.write(vals)
        return line

    def read(self, line):
        """ Read a line

        :param line: a str that will be read using the current line's `PFFCell`s
        :return: a dict associating every cell's name with their values found in line
        """
        res = {}
        for cell in self:
            line = cell.read(line, res)
        return res


class PFFCell(object):
    """ Represent a cell of Python Flat File

    :param name: name of the field, used to match it in the dict
    :param length: number of chars this cell takes
    :param type: type of the content of this cell, useful to decide of the justifying
    :param filler: char used to filled the blanks in this field, if the content is smaller then `length`
    :param align: either 'l' or 'r' ; side to align the cell content (by default, 'r' if `type` is numeric, else 'l')
    :param default: default value for this field
    """

    def __init__(self, name, length, type=str, filler=None, align=None, default=''):
        if align not in ('l', 'r'):
            align = is_numerical(type) and 'r' or 'l'
        if filler is None or len(filler) != 1:
            filler = is_numerical(type) and DEFAULT_INT_FILLER_CHAR or DEFAULT_STR_FILLER_CHAR
        self.name = name
        self.length = length
        self.type = type
        self.filler = filler
        self.align = align
        self.default = default

    def _justify(self, content):
        if len(content) > self.length:
            raise ContentOverflow(content, self)
        if self.align == 'l':
            return content.ljust(self.length, self.filler)
        elif self.align == 'r':
            return content.rjust(self.length, self.filler)

    def write(self, vals):
        """ Given a dict of values, takes this field's value, and formats it to fill this cell

        :param vals: dict of values for the cell's line
        :return: the corresponding field, justified
        """
        content_str = str(vals.get(self.name, self.default))
        return self._justify(content_str)

    def read(self, line, dest):
        """ Considering this line starts with the current field, reads it

        :param line: line to read, supposed to start with the current cell
        :param dest: dict of values corresponding to the current row, this cell's value will be added to it
        :return: line, with the current field removed
        """
        cur_field_val = line[:self.length]
        if self.align == 'r':
            cur_field_val = cur_field_val.lstrip(self.filler)
        else:
            cur_field_val = cur_field_val.rstrip(self.filler)
        if not cur_field_val:
            cur_field_val = self.default
        try:
            cur_field_val = self.type(cur_field_val)
        except TypeError:
            pass
        dest[self.name] = cur_field_val
        return line[self.length:]
