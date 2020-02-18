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
from __future__ import unicode_literals
import sys
if sys.version_info >= (3,):
    unicode = str
    encode = lambda string, encoding: string
else:
    encode = lambda string, encoding: string.encode(encoding)


DEFAULT_STR_FILLER_CHAR = ' '
DEFAULT_INT_FILLER_CHAR = '0'

EOF_LF = '\n'
EOF_CR = '\r'
EOF_CR_LF = EOF_CR + EOF_LF


def is_numerical(typ):
    return typ in (int, float, complex)


def default_truncator(text, len):
    return text[:len]


def default_before_write(cell, text):
    return text and cell.type(text) or text


def default_after_read(cell, text):
    try:
        return text and cell.type(text)
    except (TypeError, ValueError):
        return text


class ContentOverflow(Exception):
    """ Exception raised when the content of a `PFFCell` is larger than the cell itself """

    def __init__(self, content, cell):
        super(ContentOverflow, self).__init__()
        self._content = content
        self._cell = cell

    def __str__(self):
        return "Error: \"%s\" is longer than the cell %s (%d characters max)" % \
               (self._content, self._cell.name, self._cell.size)


class PFFWriter(object):
    """ Object to facilitate writing data in a positional file

    :param f: a file pointer, describing the file where lines will be written
    :param lines: a collection of `PFFLine`s, which will be used to format data and write them in `self.f`
    :param encoding: format to encode data in (utf-8 by default)
                     In python3, it turns out that encoding is handled by the file object, which makes this parameter
                     useless
    :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if too
                         long
    :param eof: char for the End Of Line append after wrire each line, default is `\n`
    :param before_write: function called on the content of each cell before casting it to unicode and writing it
                         (cell: PFFCell, text: Any) -> Any
    """

    def __init__(self, f, lines, encoding='utf-8', autotruncate=True, before_write=None, eof=EOF_LF):
        self._lines = lines
        self._file = f
        self.lcount = 0
        self._encoding = encoding
        self._autotruncate = autotruncate
        self._before_write = before_write
        self._eof = eof

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
        self._file.write(encode(
            line_model.write(vals, autotruncate=self._autotruncate, before_write=self._before_write) + self._eof,
            self._encoding
        ))
        self.lcount += 1


class PFFReader(object):
    """ Object to facilitate writing data in a positional file

    :param f: a file pointer, describing the file where lines will be written
    :param lines: a collection of `PFFLine`s, which will be used to format data and write them in `self.f`
    :param after_read: function called on the content of each cell, after reading it from the source
                       (cell: PFFCell, text: unicode) -> Any

    """

    def __init__(self, f, lines=None, after_read=None):
        self._lines = lines or []
        self._file = f
        self.lcount = 0
        self._after_read = after_read

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
        return line_model.read(line, after_read=self._after_read)


class PFFLine(list):
    """ An ordered collection of `PFFCell`s """

    def __init__(self, *elems):
        super(PFFLine, self).__init__()
        for elem in elems:
            if isinstance(elem, PFFCell):
                self.append(elem)
            elif isinstance(elem, PFFLine):
                self.extend(elem)

    def write(self, vals, autotruncate=True, before_write=None):
        """ Write values in vals in the `PFFCell`s contained in this line, and outputs a str corresponding to them

        :param vals: values to write
        :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if
                             too long
        :param before_write: function called on the content of each cell before casting it to unicode and writing it
                             (cell: PFFCell, text: Any) -> Any
        :return: a str representing the line filled with correct values
        """
        line = ""
        for cell in self:
            try:
                line += cell.write(vals, autotruncate=autotruncate, before_write=before_write)
            except Exception as e:
                print("Error when write cell %s" % cell.name)
                raise e
        return line

    def read(self, line, after_read=None):
        """ Read a line

        :param line: a str that will be read using the current line's `PFFCell`s
        :param after_read: function called on the content of each cell, after reading it from the source
                           (cell: PFFCell, text: unicode) -> Any
        :return: a dict associating every cell's name with their values found in line
        """
        res = {}
        for cell in self:
            line = cell.read(line, res, after_read)
        return res

    def show_debug(self):
        """ Debug view which outputs informations about the cell composing this line

        :return: a string, listing each and every cell, its offset, length, type and name
        """
        offset = 0
        output = u""
        for idx, cell in enumerate(self, 1):
            output += "%3d %5d %3d %s %s\n" % (idx, offset + 1, cell.length, cell.type, cell.name)
            offset += cell.length
        output += "Total len %d\n" % (offset + 1)
        return output

    def append(self, object):
        if isinstance(object, PFFCell):
            super(PFFLine, self).append(object)
        elif isinstance(object, PFFLine):
            self.extend(object)
        else:
            raise TypeError(u"unsupported operand type(s) for +=: '%s' and '%s'" %
                            (type(self).__name__, type(object).__name__))

    def __add__(self, other):
        if isinstance(other, (PFFLine, PFFCell)):
            return PFFLine(self, other)
        raise TypeError(u"unsupported operand type(s) for +: '%s' and '%s'" %
                        (type(self).__name__, type(other).__name__))

    def __iadd__(self, other):
        self.append(other)
        return self

    def __eq__(self, other):
        if len(self) != len(other):
            return False
        for (s, o) in zip(self, other):
            if s != o:
                return False
        return True

    def __ne__(self, other):
        return not self == other


class PFFCell(object):
    """ Represent a cell of Python Flat File

    :param name: name of the field, used to match it in the dict
    :param length: number of chars this cell takes
    :param type: type of the content of this cell, useful to decide of the justifying
    :param filler: char used to filled the blanks in this field, if the content is smaller then `length`
    :param align: either 'l' or 'r' ; side to align the cell content (by default, 'r' if `type` is numeric, else 'l')
    :param default: default value for this field
    :param truncator: function used to truncate the content of the cell to its size
                      (text: unicode, length: int) -> str
    :param before_write: function called on the cell content before casting it to unicode and writing it
                         (cell: PFFCell, text: Any) -> Any
    :param after_read: function called on the cell content, after reading it from the source
                       (cell: PFFCell, text: unicode) -> Any
    """

    def __init__(self, name, length, type=unicode, filler=None, align=None, default=None, truncator=default_truncator,
                 before_write=None, after_read=None):
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
        self._truncator = truncator
        self._before_write = before_write
        self._after_read = after_read

    def _justify(self, content, autotruncate=True):
        if autotruncate:
            content = self._truncator(content, self.length)
        elif len(content) > self.length:
            raise ContentOverflow(content, self)
        if self.align == 'l':
            return content.ljust(self.length, self.filler)
        elif self.align == 'r':
            return content.rjust(self.length, self.filler)

    def write(self, vals, autotruncate=True, before_write=None):
        """ Given a dict of values, takes this field's value, and formats it to fill this cell

        :param vals: dict of values for the cell's line
        :param autotruncate: if True, will truncate a value to its cell size instead of raising a ContentOverflow if
                             too long
        :param before_write: function called on the cell content before casting it to unicode and writing it
                             (cell: PFFCell, text: Any) -> Any
                             Will not be used if a `before_write` as been defined for this PFFCell in __init__
        :return: the corresponding field, justified
        """
        content_val = vals.get(self.name, self.default)
        if content_val is None:
            content_val = self.default
        before_write = self._before_write or before_write or default_before_write
        content_val = before_write(self, content_val)
        content_str = unicode(content_val or "")
        return self._justify(content_str, autotruncate=autotruncate)

    def read(self, line, dest, after_read=None):
        """ Considering this line starts with the current field, reads it

        :param line: line to read, supposed to start with the current cell
        :param dest: dict of values corresponding to the current row, this cell's value will be added to it
        :param after_read: function called on the cell content, after reading it from the source
                           (cell: PFFCell, text: unicode) -> Any
                           Will not be used if a `after_read` as been defined for this PFFCell in __init__
        :return: line, with the current field removed
        """
        cur_field_val = line[:self.length]
        if self.align == 'r':
            cur_field_val = cur_field_val.lstrip(self.filler)
        else:
            cur_field_val = cur_field_val.rstrip(self.filler)
        if not cur_field_val:
            cur_field_val = None
        after_read = self._after_read or after_read or default_after_read
        cur_field_val = after_read(self, cur_field_val)
        dest[self.name] = cur_field_val
        return line[self.length:]

    def __len__(self):
        return self.length

    def __add__(self, other):
        if isinstance(other, (PFFCell, PFFLine)):
            return PFFLine(self, other)
        raise TypeError(u"unsupported operand type(s) for +: '%s' and '%s'" %
                        (type(self).__name__, type(other).__name__))

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == getattr(other, 'name', False) and len(self) == len(other)

    def __ne__(self, other):
        return not self == other


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

    def write(self, vals, autotruncate=True, before_write=None):
        return self.filler * self.length

    def read(self, line, dest, after_read=None):
        return line[self.length:]


class PFFIntCell(PFFCell):
    """
    This cell is a shortcut for a PFFCell of type `int`

    sample:
    cell = PFFIntCell("name', 5)
    assert cell.write({cell.name:2}) == '00002'
    assert cell.write({}) == '00000'
    """

    def __init__(self, name, length, align=None, default=None, truncator=default_truncator, before_write=None, after_read=None):
        super(PFFIntCell, self).__init__(
            name, length, int,
            align=align, default=default,
            truncator=truncator,
            before_write=before_write,
            after_read=after_read
        )


# TODO add a PFFDatetimeCell that take a format

class PFFIntSpaceCell(PFFIntCell):
    """
    This cell is like an PFFIntCell except when no value is exist in the write then the char ('space'; " ") is used

    sample:
    cell = PFFIntSpaceCell("name', 5)
    assert cell.write({cell.name:2}) == '00002'
    assert cell.write({}) == '     ' <- or a classic in cell the result will be '00000'
    """

    def _justify(self, content, autotruncate=True):
        if content:
            return super(PFFIntSpaceCell, self)._justify(content, autotruncate)
        self.filler = DEFAULT_STR_FILLER_CHAR
        value = super(PFFIntSpaceCell, self)._justify(content, autotruncate)
        self.filler = DEFAULT_INT_FILLER_CHAR
        return value


    def read(self, line, dest, after_read=None):
        self.filler = DEFAULT_STR_FILLER_CHAR
        result = super(PFFIntSpaceCell, self).read(line, dest, after_read=after_read)
        self.filler = DEFAULT_INT_FILLER_CHAR
        return result