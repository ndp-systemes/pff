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


def is_numerical(typ):
    return typ in (int, float, complex)


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
    :param encoding: format to encode data in (utf-8 by default)
    :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if too
                         long
    """

    def __init__(self, f, lines, encoding='utf-8', autotruncate=False):
        self._lines = lines
        self._file = f
        self.lcount = 0
        self._encoding = encoding
        self._autotruncate = autotruncate

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
        self._file.write(line_model.write(vals, encoding=self._encoding, autotruncate=self._autotruncate) + '\n')
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
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def next(self):
        return self.__next__()

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
            return None
        line_model = line_model or self.chose_line_model(line)
        self.lcount += 1
        return line_model.read(line)


class PFFLine(list):
    """ An ordered collection of `PFFCell`s """

    def __init__(self, *elems):
        super(PFFLine, self).__init__()
        for elem in elems:
            if isinstance(elem, PFFCell):
                self.append(elem)
            elif isinstance(elem, PFFLine):
                self.extend(elem)

    def write(self, vals, encoding, autotruncate=False):
        """ Write values in vals in the `PFFCell`s contained in this line, and outputs a str corresponding to them

        :param vals: values to write
        :param encoding: format to encode the values in
        :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if
                             too long
        :return: a str representing the line filled with correct values
        """
        line = ""
        for cell in self:
            line += cell.write(vals, encoding=encoding, autotruncate=autotruncate)
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

    def show_debug(self):
        """ Debug view which outputs informations about the cell composing this line

        :return: a string, listing each and every cell, its offset, length, type and name
        """
        offset = 0
        output = u""
        for cell in self:
            output += "%5d %3d %s %s\n" % (offset, cell.length, cell.type, cell.name)
            offset += cell.length
        return output


class PFFCell(object):
    """ Represent a cell of Python Flat File

    :param name: name of the field, used to match it in the dict
    :param length: number of chars this cell takes
    :param type: type of the content of this cell, useful to decide of the justifying
    :param filler: char used to filled the blanks in this field, if the content is smaller then `length`
    :param align: either 'l' or 'r' ; side to align the cell content (by default, 'r' if `type` is numeric, else 'l')
    :param default: default value for this field
    """

    def __init__(self, name, length, type=unicode, filler=None, align=None, default=None):
        if align not in ('l', 'r'):
            align = is_numerical(type) and 'r' or 'l'
        if filler is None or len(filler) != 1:
            filler = is_numerical(type) and DEFAULT_INT_FILLER_CHAR or DEFAULT_STR_FILLER_CHAR
        if default is None or len(default) > length:
            default = is_numerical(type) and DEFAULT_INT_FILLER_CHAR or DEFAULT_STR_FILLER_CHAR
        self.name = name
        self.length = length
        self.type = type
        self.filler = filler
        self.align = align
        self.default = default

    def _justify(self, content, autotruncate=False):
        if autotruncate:
            content = content[:self.length]
        elif len(content) > self.length:
            raise ContentOverflow(content, self)
        if self.align == 'l':
            return content.ljust(self.length, self.filler)
        elif self.align == 'r':
            return content.rjust(self.length, self.filler)

    def write(self, vals, encoding, autotruncate=False):
        """ Given a dict of values, takes this field's value, and formats it to fill this cell

        :param vals: dict of values for the cell's line
        :param encoding: format to encode the values in
        :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if
                             too long
        :return: the corresponding field, justified
        """
        content_val = vals.get(self.name, self.default)
        if content_val is None:
            content_val = self.default
        content_str = unicode(self.type(content_val))
        return self._justify(content_str, autotruncate=autotruncate).encode(encoding)

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
        except (TypeError, ValueError):
            pass
        dest[self.name] = cur_field_val
        return line[self.length:]


class PFFBlankCell(PFFCell):
    """ A blank cell, without any content except the filler char
    Implements the same methods as a standard `PFFCell`

    :param length: cell length
    :param name: the field name, will be 'BLANK' if omitted
    :param filler: char used to fill the field, by default a space
    """

    type = None

    def __init__(self, length, name=None, filler=' '):
        super(PFFBlankCell, self).__init__(name or 'BLANK', length, type(None), filler)

    def write(self, vals, encoding, autotruncate=False):
        return self.filler * self.length

    def read(self, line, dest):
        return line[self.length:]
