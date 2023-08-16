#!/bin/env python
## A small web application for selecting a 24-bit RGB colour value by
## selecting one from a grid of colours and then refining it by selecting one
## close to it from (two) successive grids.
#
# Copyright (C) 2017-2022 by James MacKay.
#
#-This program is free software: you can redistribute it and/or modify
#-it under the terms of the GNU General Public License as published by
#-the Free Software Foundation, either version 3 of the License, or
#-(at your option) any later version.
#
#-This program is distributed in the hope that it will be useful,
#-but WITHOUT ANY WARRANTY; without even the implied warranty of
#-MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#-GNU General Public License for more details.
#
#-You should have received a copy of the GNU General Public License
#-along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from flask import Flask, request, url_for

import os
import sys

#
# Constants.
#

# The default foreground and background colours in the web pages we serve.
_defaultBackgroundColour = "white"
_defaultForegroundColour = "black"

# The format of the start of an HTML page that contains a colour grid.
#
# Parameters:
#  - title: the page's title
#  - fgColour: the page's foreground colour
#  - bgColour: the page's background colour
_pageStartFmt = """<html>
    <head>
        <title>{title}</title>
        <style type="text/css" media="screen">
body, h1, table, tr, td, div, span {{ margin: 0; padding: 0; }}
body {{ font: 14px Arial, sans-serif; margin: 0.5em;
       background: {bgColour}; color: {fgColour}; }}
h1 {{ font-size: 1.5em; font-variant: small-caps; display: inline; }}
.message {{ float: right; padding: 0.5em 0.5em 0; }}
.message .colour {{ font-weight: bold; }}
.colours {{ width: 100%%; }}
.colours td {{ height: 35px; border: 1px solid {bgColour}; }}
.colours td a {{ display: block; text-decoration: none; color: transparent;
                text-align: center; }}
.colours td a:hover {{ }}
.colours td a:hover .cell1 {{ color: black; }}
.colours td a:hover .cell2 {{ color: white; }}
.grid-metadata {{ display: inline; }}
.reverse {{ float: right; padding: 0 0.5em; color: {fgColour}; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
"""

# The end of an HTML page that contains a colour grid.
_pageEnd = """
    </body>
</html>
"""


# The query argument used to specify the previously-selected colour.
_prevColourArgName = "prev"

# The query argument used to specify that the default foreground and
# background colours are to be reversed.
_reverseColoursArgName = "rev"

# The value that the query argument named '_reverseColoursArgName' must have
# in order for the colours to be reversed.
_reverseColoursArgValue = "1"


#
# Utility functions.
#

def output(w, fmt, *args):
    """
    Outputs to the output stream 'w' the message constructed from the
    format string 'fmt' and any and all arguments 'args'.
    """
    assert w is not None
    assert fmt is not None  # but it can be empty
    print(fmt.format(*args), file = w)

def say(fmt, *args):
    """
    Outputs to standard output the message constructed from the format string
    'fmt' and any and all arguments 'args'.

    See also: debug(), warn(), output().
    """
    assert fmt is not None  # but it can be empty
    output(sys.stdout, fmt, *args)

def debug(fmt, *args):
    """
    Outputs to standard error the message constructed from the format string
    'fmt' and any and all arguments 'args'.

    See also: say(), warn(), output().
    """
    assert fmt is not None  # but it can be empty
    output(sys.stderr, fmt, *args)

def warn(fmt, *args):
    """
    Outputs to standard error a warning message constructed from our
    basename, the format string 'fmt' and any and all arguments 'args'.
    """
    assert fmt is not None  # but it can be empty
    base = os.path.basename(sys.argv[0])
    output(sys.stderr, base + ": " + fmt.format(*args) + ".")


def twoTo(exp):
    """
    Returns the result of raising 2 to the exponent 'exp'.
    """
    assert exp >= 0
    result = 2 ** exp
    assert result > 0
    return result

def bigThenSmallHalf(val):
    """
    Returns a 2-element tuple whose elements sum to 'val': if 'val' is even
    then both elements are equal to half of 'val', otherwise the first
    element is one bigger than the second element.
    """
    assert val >= 0
    res = val // 2
    if val % 2 == 0:
        result = (res, res)
    else:
        result = (res + 1, res)
    assert len(result) == 2
    assert result[0] >= result[1]
    assert val == (result[0] + result[1])
    return result

def printRequestInfo(req):
    """
    Prints to standard output various information contained in the Flask
    request 'req', generally for debugging purposes.
    """
    assert req is not None
    say("dir(request) = [{}]", dir(req))
    say("  url = [{}]", req.url)
    say("  base_url = [{}]", req.base_url)
    say("  url_root = [{}]", req.url_root)
    say("  url_rule = [{}]", req.url_rule)
    say("  query_string = [{}]", req.query_string)
    say("  args = [{}]", req.args)


#
# Exception classes.
#

class InvalidGridDepthException(Exception):
    """
    The class of exception raised when an attempt is made to construct a
    ColourGrid from an invalid grid depth.
    """
    pass

class InvalidHexColourException(Exception):
    """
    The class of exception raised when an invalid hexadecimal representation
    of a colour is encountered.
    """
    pass


#
# Classes.
#

class Colour:
    """
    Represents a colour that can be shown and selected.
    """

    # A string of all of the valid (uppercase) hexadecimal digits, in
    # ascending order.
    _hexDigits = "0123456789ABCDEF"
    assert len(_hexDigits) == 16

    # The number of components a colour has.
    _componentCount = 3  # red, green and blue

    # The maximum number of hexadecimal digits it takes to represent a
    # component of a colour.
    _hexDigitsPerComponent = 2

    # The exponent to raise 2 to to get the number of different values a
    # component of a colour can have, and that number of values.
    _componentValuesCountLog2 = _hexDigitsPerComponent * 4
        # since the number of values a hex digit can represent is (2 ** 4)
    _componentValuesCount = twoTo(_componentValuesCountLog2)

    # The minimum and maximum value a component can have.
    _minComponentValue = 0
    _maxComponentValue = _componentValuesCount - 1

    # The exponent to raise 2 to to get the total number of different colour
    # values, and that total number of different values.
    _valuesCountLog2 = _componentValuesCountLog2 * _componentCount
    _valuesCount = twoTo(_valuesCountLog2)


    def __init__(self, hexColour):
        """
        Initializes us from the hexadecimal string representation 'hex' of
        the colour that we represent, or raises an InvalidHexColourException
        if 'hexColour' isn't a valid hexadecimal string representation of a
        colour.
        """
        self._checkValidHexColour(hexColour)
        self._hex = hexColour

    @classmethod
    def black(cls):
        """
        Returns the instance of this class that represents the colour black.
        """
        result = cls._fromRepeatedComponent(cls._minComponentValue)
        assert result is not None
        return result

    @classmethod
    def white(cls):
        """
        Returns the instance of this class that represents the colour black.
        """
        result = cls._fromRepeatedComponent(cls._maxComponentValue)
        #debug("white = {}", result)
        assert result is not None
        return result

    @classmethod
    def fromComponents(cls, *comps):
        """
        Returns an instance of this class that represents the colour whose
        (decimal) components are given - in order - by 'comps'.
        """
        assert cls.areValidComponents(comps)
        res = ""
        for c in comps:
            #debug("c={}", c)
            part = hex(c)[2:].upper()  # '[2:]' removes the '0x' prefix
            #debug("c={}; part={}", c, part)
            while len(part) < 2:
                part = "0" + part
            res += part
        #debug("components to hex = {}", res)
        result = cls(res)
        assert result is not None
        return result

    @classmethod
    def _fromRepeatedComponent(cls, comp):
        """
        Returns an instance of this class that represents the colour whose
        (decimal) components are all equal to 'comp'.
        """
        assert cls.isValidComponent(comp)
        comps = [comp for i in range(cls.componentCount())]
        result = cls.fromComponents(*comps)
        assert result is not None
        return result


    def hex(self):
        """
        Returns the hexadecimal string representation of this colour.
        """
        result = self._hex
        assert result is not None
        return result

    def component(self, index):
        """
        Returns the component of ours whose 0-based index is 'index'.
        """
        assert index >= 0
        assert index < self.componentCount()
        result = self.components()[index]
        assert result >= self.minimumComponentValue()
        assert result <= self.maximumComponentValue()
        return result

    def components(self):
        """
        Returns a list whose 'i''th element is the 'i''th component of this
        colour.
        """
        start = 0
        incr = self._hexDigitsPerComponent
        pastEnd = incr
        result = []
        val = self._hex
        for i in range(self._componentCount):
            result.append(self._uppercaseHexToDecimal(val[start:pastEnd]))
            start += incr
            pastEnd += incr
        assert result is not None
        assert len(result) == self._componentCount
        assert self.areValidComponents(result)
        return result

    @classmethod
    def componentCount(cls):
        """
        Returns the number of components an instance of this class has in
        its components representation.
        """
        result = cls._componentCount
        assert result > 0
        return result

    @classmethod
    def minimumComponentValue(cls):
        """
        Returns the smallest value that a component of a Colour can have.
        """
        result = cls._minComponentValue
        assert result >= 0
        return result

    @classmethod
    def maximumComponentValue(cls):
        """
        Returns the largest value that a component of a Colour can have.
        """
        result = cls._maxComponentValue
        assert result >= 0
        return result

    @classmethod
    def valuesCountLog2(cls):
        """
        Returns the exponent to raise 2 to to get the total number of
        different colour values.
        """
        result = cls._valuesCountLog2
        assert result >= 0
        return result


    @classmethod
    def isValidHexColour(cls, hexColour):
        """
        Returns True iff 'hexColour' is a valid hexadecimal string
        representation of a colour in an instance of this class.
        """
        result = True
        if hexColour is None:
            result = False
        else:
            try:
                cls._checkValidHexColour(hexColour)
            except InvalidHexColourException:
                result = False
        return result

    @classmethod
    def areValidComponents(cls, colourComps):
        """
        Returns True iff 'colourComps' is a valid components representation
        of an instance of this class.
        """
        result = False
        if colourComps is not None and \
           len(colourComps) == cls.componentCount():
            result = True
            for c in colourComps:
                if not cls.isValidComponent(c):
                    result = False
                    break  # for
        return result

    @classmethod
    def isValidComponent(cls, comp):
        """
        Returns True iff 'comp' is a valid component of a Colour.
        """
        return (comp >= cls.minimumComponentValue()) and \
            (comp <= cls.maximumComponentValue())


    def canAddToAllComponents(self, adj):
        """
        Returns True iff 'adj' could be added to each of our components
        without any of them becoming bigger than the maximumComponentValue().
        """
        assert adj >= 0
        result = True
        max = self.maximumComponentValue() - adj
        for c in self.components():
            if c > max:
                result = False
                break  # for
        return result

    def addToAllComponents(self, adj):
        """
        Returns a new Colour each of whose components is the same as the
        corresponding component in 'self' with 'adj' added to it.
        """
        assert adj >= 0
        assert self.canAddToAllComponents(adj)
        comps = [x + adj for x in self.components()]
        result = Colour.fromComponents(*comps)
        assert result is not None
        return result

    def __lt__(self, other):
        return self.compare(self, other) < 0

    def __gt__(self, other):
        return self.compare(self, other) > 0

    def __le__(self, other):
        return self.compare(self, other) <= 0

    def __ge__(self, other):
        return self.compare(self, other) >= 0

    def __eq__(self, other):
        return self.compare(self, other) == 0

    def __ne__(self, other):
        return self.compare(self, other) != 0

    @classmethod
    def compare(cls, c1, c2):
        """
        Compares the Colour instances 'c1' and 'c2' so that when we're used
        to sort a group of Colours they appear in groups, where the Colours
        within a group are in order of increasing lightness.

        We return an integer whose value is less than, equal to or greater
        than zero iff, respectively, 'c1' is less than, equal to or greater
        than 'c2'.
        """
        assert c1 is not None
        assert c2 is not None
        assert c1.componentCount() == c2.componentCount()
        result = 0
        n = c1.componentCount()  # == c2.componentCount()
        if n > 0:
            # We consider Colours who have fewer components with the same
            # largest values to be less than those that have more such
            # components. (So if the components are RGB, for example, then
            # primary colours are less than/come before non-primary ones,
            # and greyscale colours are greater than/come after non-greyscale
            # ones.)
            maxInds1 = c1.largestComponentsIndices()
            maxInds2 = c2.largestComponentsIndices()
            numMaxInds1 = len(maxInds1)
            numMaxInds2 = len(maxInds2)
            result = numMaxInds2 - numMaxInds1
            if result == 0:
                # We consider the Colour whose lowest "largest component"
                # index is lower than the other's lowest such index to be the
                # smaller of the two Colours.
                assert numMaxInds1 == numMaxInds2
                for j in range(numMaxInds1):
                    result = maxInds2[j] - maxInds1[j]
                    if result != 0:
                        break  # for
                if result == 0:
                    # They have the same "largest component" indices. We
                    # consider the one with the largest largest component to
                    # be greater than the other one.
                    assert maxInds1 == maxInds2
                    ind = maxInds1[0]
                    result = c2.component(ind) - c1.component(ind)
                    if result == 0:
                        # The largest component value for both Colours is the
                        # same, so we order them based on the sum of the
                        # values of their other components.
                        result = c2.sumOfComponentsIgnoring(maxInds2) - \
                                     c1.sumOfComponentsIgnoring(maxInds1)
                        if result == 0:
                            # Mostly for definiteness, if the sums are equal
                            # then sort them by their hex representation.
                            hex1 = c1.hex()
                            hex2 = c2.hex()
                            if hex1 < hex2:    # => result < 0
                                result = -1
                            elif hex1 > hex2:  # => result > 0
                                result = 1
                            else:
                                result = 0
        assert result is not None
        return result

    def areAllComponentsEqual(self):
        """
        Returns True iff all of our components are equal to each other.
        """
        result = True
        val = None
        for c in self.components():
            if val is None:  # first component
                val = c
                assert val is not None
            elif c != val:
                result = False
                break  # for
        return result

    def largestComponentsIndices(self):
        """
        Returns a list - sorted in ascending order - of the indices of those
        of our components whose values are larger than those of all of its
        other components. (Thus all of our components whose indices are in
        our result are equal to each other.)
        """
        maxVal = self.minimumComponentValue() - 1
        i = 0
        for c in self.components():
            if c > maxVal:
                result = [i]
                maxVal = c
            elif c == maxVal:
                result.append(i)
            i += 1
        assert result is not None
        assert (len(result) == 0) == (self.componentCount() == 0)
        #assert "'result' is sorted in ascending order"
        return result

    def sumOfComponentsIgnoring(self, indices):
        """
        Returns the sum of all of our components except the ones whose
        0-based indices are in the set 'indices'.
        """
        assert indices is not None
        result = 0
        i = 0
        for c in self.components():
            if i not in indices:
                result += c
            i += 1
        assert result is not None
        return result


    def allInRegion(self, endColour, componentStepSize):
        """
        Generates all of the colours in the region of 'colour space' whose
        inclusive lower bound is 'self' and whose inclusive upper bound is
        'endColour', where the components of the generated colours are
        incremented by 'componentStepSize'.
        """
        assert endColour is not None
        assert componentStepSize > 0
        #debug("allInRegion({}, {}, {})", self, endColour, componentStepSize)
        result = self
        yield result

        # The components earlier in a Colour's list of components will change
        # faster than the later ones.
        startComps = self.components()
        endComps = endColour.components()
        numComps = self.componentCount()
        while result is not None:
            comps = result.components()[:]  # copy of the list
            result = None
            for i in range(numComps):
                newComp = comps[i] + componentStepSize
                if newComp <= endComps[i]:
                    # Create the next Colour by incrementing the previous
                    # colour's 'i''th component by 'componentStepSize'.
                    assert self.isValidComponent(newComp)
                    comps[i] = newComp
                    result = Colour.fromComponents(*comps)
                    assert result is not None
                    yield result
                    break  # for
                else:
                    # The current component can't be increased any more and
                    # still be in the region, so reset it back to the
                    # corresponding component in 'self' and try to increment
                    # the next component (if there is one: otherwise we're
                    # done).
                    comps[i] = startComps[i]
                    assert result is None
        assert result is None  # we reached the end of the region


    def __str__(self):
        """
        Returns our string representation.
        """
        result = "colour(" + \
            ", ".join([str(c) for c in self.components()]) + ")"
        assert result
        return result

    def __repr__(self):
        """
        Returns the representation of us that, when eval'ed, will create an
        object that's the same as this one.
        """
        result = self.__class__.__name__ + "(" + self.hex() + ")"
        assert result
        return result


    @classmethod
    def _checkValidHexColour(cls, hexColour):
        """
        Checks that 'hexColour' is a valid hexadecimal string representation
        of a colour in an instance of this class, raising an
        InvalidHexColourException iff it isn't.
        """
        assert hexColour is not None
        n = cls._hexDigitsPerComponent * cls._componentCount
        if len(hexColour) != n:
            raise InvalidHexColourException("'{}' is an invalid hexadecimal "
                "representation of a colour because it doesn't contain "
                "exactly {} hexadecimal digits.".format(hexColour, n))
        for ch in hexColour:
            if ch not in cls._hexDigits:
                raise InvalidHexColourException("'{}' is an invalid "
                    "hexadecimal representation of a colour because it "
                    "contains '{}', which is not a valid (uppercase) "
                    "hexadecimal digit.".format(hexColour, ch))

    @classmethod
    def _uppercaseHexToDecimal(cls, hexNum):
        """
        Returns the decimal number that represents the same value as the
        uppercase hexadecimal number 'hexNum'.

        Raises a ValueError if one or more of the characters in 'hexNum'
        isn't an uppercase hexadecimal digit.
        """
        result = 0
        digits = cls._hexDigits
        max = len(digits)
        for d in hexNum:
            result *= max
            result += digits.index(d)
        assert result >= 0
        assert result < (max ** len(hexNum))
        return result


class ColourGridCell(object):
    """
    Represents a single cell in a ColourGrid.
    """

    def __init__(self, firstColour, midColour, lastColour,
                 rowIndex, columnIndex):
        """
        Initializes us with information about the cell: the first and last
        Colours 'firstColour' and 'lastColour' that the cell represents, the
        Colour 'midColour' that is (near) the middle of the range of colours
        that the cell represents, and the 0-based indices of the row and
        column of the cell in its grid.
        """
        assert firstColour is not None
        assert midColour is not None
        assert lastColour is not None
        assert rowIndex >= 0
        assert columnIndex >= 0
        self._firstColour = firstColour
        self._midColour = midColour
        self._lastColour = lastColour
        self._rowIndex = rowIndex
        self._columnIndex = columnIndex

    def firstColour(self):
        """
        Returns the first Colour in the range of colours that this cell
        represents.
        """
        result = self._firstColour
        assert result is not None
        return result

    def middleColour(self):
        """
        Returns the a Colour near/at the middle of the range of colours that
        this cell represents.
        """
        result = self._firstColour
        assert result is not None
        return result

    def lastColour(self):
        """
        Returns the last Colour in the range of colours that this cell
        represents.
        """
        result = self._firstColour
        assert result is not None
        return result

    def rowIndex(self):
        """
        Returns the 0-based index of the grid row that this cell is in.
        """
        result = self._rowIndex
        assert result >= 0
        return result

    def columnIndex(self):
        """
        Returns the 0-based index of the grid column that this cell is in.
        """
        result = self._columnIndex
        assert result >= 0
        return result


class ColourGrid(object):
    """
    Represents a grid of colours.
    """

    # The exponent to raise 2 to get the number of cells in all grids (except
    # possibly the last, which may be smaller), and that number of cells.
    #
    # That exponent should be such that:
    #
    #   - it results in reasonable sized grids on most/all monitors, and
    #   - the exponent is evenly divisible by the number of components each
    #     each colour is divided into (i.e. Colour.componentCount()).
    #
    # The second condition ensures that in each grid the gap between colours
    # can be the same integer value (without rounding). (Note that in the
    # last grid the gap will always be 1.)
    _cellCountLog2 = 3 * Colour.componentCount()
    assert _cellCountLog2 % Colour.componentCount() == 0


    @classmethod
    def first(cls):
        """
        Returns the instance of this class that represents all of the colours.
        """
        result = cls(0, Colour.black())
        assert result is not None
        return result

    def __init__(self, depth, startColour):
        """
        Initializes us with the 0-based depth 'depth' of this grid and the
        first Colour 'startColour' in it. Raises an InvalidGridDepthException
        if 'depth' isn't a valid grid depth.
        """
        assert depth >= 0
        assert startColour is not None
        stepSizeLog2 = self._colourComponentStepSizeLog2(depth)
            # also checks that that depth is valid
        self._componentStepSizeLog2 = stepSizeLog2
        self._depth = depth
        self._firstColour = startColour

        if depth == 0:
            self._lastColour = Colour.white()
        else:
            adj = twoTo(self._colourComponentStepSizeLog2(depth - 1)) - 1
            assert adj > 0
            self._lastColour = startColour.addToAllComponents(adj)

        # Note: most monitors are wider than they are tall, so there are as
        # many or more columns than rows (though they're not usually twice as
        # wide, so grid cells will usually be taller than they are wide).
        if stepSizeLog2 > 0:
            # We're not at maximum depth, so we're a full grid.
            sz2 = self._cellCountLog2
        elif depth == 0:
            # All of the colours fit in the first grid, which may be smaller
            # than a full grid.
            sz2 = Colour.valuesCountLog2()
        else:
            # There are no deeper grids than us. The step size for grids one
            # level less deep determines our dimensions.
            assert depth > 0
            sz2 = self._colourComponentStepSizeLog2(depth - 1)
            assert sz2 > 0  # since it's not the deepest grid
            sz2 *= Colour.componentCount()
        (self._columnCountLog2, self._rowCountLog2) = bigThenSmallHalf(sz2)

    def subgridFrom(self, startColour):
        """
        Returns the instance of our class that represents the subgrid - that
        is, the grid at one greater level of depth - whose first Colour is
        'startColour'.
        """
        assert self.hasSubgrids()
        assert startColour is not None
        result = self.__class__(self.depth() + 1, startColour)
        assert result is not None
        assert result.depth() == self.depth() + 1
        return result

    def hasSubgrids(self):
        """
        Returns True iff this grid can have subgrids.
        """
        return (self._componentStepSizeLog2 > 0)


    def rowCount(self):
        """
        Returns the number of rows in this grid.
        """
        result = twoTo(self._rowCountLog2)
        assert result > 0
        return result

    def columnCount(self):
        """
        Returns the number of columns in this grid.
        """
        result = twoTo(self._columnCountLog2)
        assert result > 0
        return result

    def cellCount(self):
        """
        Returns the number of cells in this grid.
        """
        result = self.rowCount() * self.columnCount()
        assert result > 0
        return result

    def depth(self):
        """
        Returns our depth: the number of grids after the first/main grid we
        are.
        """
        result = self._depth
        assert result >= 0
        return result

    def colourComponentStepSize(self):
        """
        Returns the step size between the components of colours in this grid.
        """
        result = twoTo(self._componentStepSizeLog2)
        assert result > 0
        return result

    def firstColour(self):
        """
        Returns the first colour in this grid.
        """
        result = self._firstColour
        assert result is not None
        return result

    def lastColour(self):
        """
        Returns the last colour in this grid.
        """
        result = self._lastColour
        assert result is not None
        return result

    def allCells(self):
        """
        Generates the ColourGridCells that represent the cells of this grid,
        in row-major order (so the column changes faster than the row).
        """
        numRows = self.rowCount()
        numCols = self.columnCount()
        stepSize = self.colourComponentStepSize()
        ri = 0
        ci = 0
        allColours = list(self._firstColour.allInRegion(self._lastColour,
                                                        stepSize))
        allColours.sort()
        for firstColour in allColours:
            assert ri < numRows
            assert ci < numCols
            if stepSize == 1:
                midColour = lastColour = firstColour
            else:
                #debug("firstColour = {}; stepSize = {}", str(firstColour), stepSize)
                midColour = firstColour.addToAllComponents(stepSize // 2)
                lastColour = firstColour.addToAllComponents(stepSize - 1)
            yield ColourGridCell(firstColour, midColour, lastColour, ri, ci)
            ci += 1
            if ci >= numCols:
                ci = 0
                ri += 1

    @classmethod
    def _colourComponentStepSize(cls, depth):
        """
        Returns the step size between the components of colours in a grid of
        depth 'depth', or raises an InvalidGridDepthException if 'depth'
        isn't a valid grid depth.

        See also: _colourComponentStepSizeLog2().
        """
        assert depth >= 0
        result = twoTo(cls._colourComponentStepSizeLog2(depth))
        assert result > 0
        return result

    @classmethod
    def _colourComponentStepSizeLog2(cls, depth):
        """
        Returns the exponent to raise 2 to to get the step size between the
        components of colours in a grid of depth 'depth', or raises an
        InvalidGridDepthException if 'depth' isn't a valid grid depth.

        See also: _colourComponentStepSize().
        """
        assert depth >= 0
        # Calculate 'result', where (2 ** result) is the number of colours
        # that each cell in the grid represents.
        cellsLog2 = cls._cellCountLog2
        isValid = True
        result = Colour.valuesCountLog2()
        result -= ((depth + 1) * cellsLog2)
            # the combination of the current grid and the one at each
            # preceding level of depth divides the number of colours a cell
            # represents by the number of cells in the grid (which is
            # equivalent to subtracting 'cellsLog2' from 'result' once for
            # each such grid)
        if result > 0:
            # We need to 'split' the colours each cell represents across all
            # of the components: we've chosen the grid size so that the
            # colours can be split evenly across all of those components.
            assert result % Colour.componentCount() == 0
            result //= Colour.componentCount()
        elif depth == 0:
            # All of the colours fit in the first (depth == 0) grid.
            assert Colour.valuesCountLog2() <= cellsLog2
                # since result <= 0 (and depth == 0)
            result = 0
        elif result < -cellsLog2:
            # This case exists solely to avoid deep recursion (see below)
            # ending a raised exception when 'depth' is large. Our condition
            # may be more cautious than is strictly necessary.
            isValid = False
        else:
            # The step size is at most 1 (2 ** 0), so 'depth' is valid iff
            # the step size at the preceding depth isn't also 1 (that is, if
            # its exponent isn't 0).
            result = 0  # only used if 'isValid' is True
            isValid = (cls._colourComponentStepSizeLog2(depth - 1) > 0)

        if not isValid:
            # Cells of grids at the previous depth represent a single colour,
            # so there's no reason for grids at a lower depth.
            raise InvalidGridDepthException("The colour grid depth '{}' is "
                "invalid since grids of that depth aren't needed to select "
                "a colour.".format(depth))
        assert result >= 0
        return result


class PageBuilder(object):
    """
    Builds the contents of HTML pages.
    """

    # One level of indentation.
    _oneIndent = " " * 4

    # The default title of a page.
    _defaultTitle = "Colour Grid"

    # The maximum length that a colour cell's link text can have: otherwise
    # it will be abbreviated.
    #
    # This maximum exists in order to keep the cell widths - and hence the
    # table widths - reasonable.
    _maximumLinkTextLength = 6

    def __init__(self, grid, req, title = None):
        """
        Initializes us with the ColourGrid 'grid' whose contents are to be
        included in the page requested by the Flask request 'req', If 'title'
        isn't None then it's used as the page's title; otherwise a default
        title is used.
        """
        assert grid is not None
        assert req is not None
        # 'title' can be None
        self._grid = grid
        self._request = req
        if title is not None:
            self._title = title
        else:
            self._title = self._defaultTitle
        self._message = None  # see setMessage()
        self._bgColour = _defaultBackgroundColour
        self._fgColour = _defaultForegroundColour
        self._doReverseColours = False

    def reverseColours(self):
        """
        Reverses/switches the default foreground and background colours in
        the page we build.
        """
        self._doReverseColours = True

    def setMessage(self, msg):
        """
        Sets 'msg' to be the message that is to be included in the page we
        build.

        Note: we must be called before build() if the message is to be
        included in the latter's output.
        """
        assert msg is not None
        #debug("Set message to [{}]", msg)
        self._message = msg

    def build(self):
        """
        Builds the page and returns its contents as a string.
        """
        grid = self._grid
        lvl = 0
        (fgColour, bgColour) = (self._fgColour, self._bgColour)
        queryArgs = {}
        if self._doReverseColours:
            (fgColour, bgColour) = (bgColour, fgColour)
            queryArgs[_reverseColoursArgName] = _reverseColoursArgValue
        res = [_pageStartFmt.format(title = self._title,
                                fgColour = fgColour, bgColour = bgColour)]
        lvl += 2
        msg = self._message
        if msg is not None:
            self._indent(lvl, res)
            res.append("<div class=\"message\">{}</div>".format(msg))
        self._indent(lvl, res)
        res.append("<table class=\"colours\" cellspacing=\"0\">\n")
        lvl += 1
        for cell in grid.allCells():
            isRowStart = (cell.columnIndex() == 0)
            if isRowStart:
                if cell.rowIndex() > 0:
                    lvl -= 1
                    self._indent(lvl, res)
                    res.append("</tr>\n")
                self._indent(lvl, res)
                res.append("<tr>\n")
                lvl += 1
            res.append(self._buildCell(cell, lvl, queryArgs))
        lvl -= 2  # one for the last column and one for the last row
        self._indent(lvl, res)
        res.append("</table>")

        # Add a grid metadata section.
        self._indent(lvl, res)
        res.append("<div class=\"grid-metadata\">\n")
        lvl += 1
        self._indent(lvl, res)
        res.append("<span>%d x %d = %d colours: #%s-#%s / %d</span>" %
                   (grid.rowCount(), grid.columnCount(), grid.cellCount(),
                    grid.firstColour().hex(), grid.lastColour().hex(),
                    grid.colourComponentStepSize()))
        lvl -= 1
        self._indent(lvl, res)
        res.append("</div> <!-- grid-metadata -->\n")

        # Add a link to reverse the colours.
        self._indent(lvl, res)
        res.append("<a class=reverse href=\"%s\">reverse</a>\n" %
                   self._reverseColoursUrl())

        res.append(_pageEnd)  # already indented

        result = "".join(res)
        assert result is not None
        return result

    @classmethod
    def _indent(cls, level, c):
        """
        Appends string(s) representing 'level' levels of indentation to the
        end of the list 'c'.
        """
        assert level >= 0
        assert c is not None
        if level > 0:
            c.append(cls._oneIndent * level)

    def _buildCell(self, cell, lvl, queryArgs):
        """
        Builds the HTML fragment (indented 'lvl' levels) that represents the
        ColourGridCell 'cell' in the page we're building and returns it as a
        string. The mappings in the dict 'queryArgs' are intended to be used
        in the URL in the (main) hyperlink in the cell, if it has one.
        """
        assert cell is not None
        assert lvl >= 0
        assert queryArgs is not None  # though it may be empty
        bgHex = cell.middleColour().hex()
        res = []

        self._indent(lvl, res)
        res.append("<td style=\"background: #%s; color: #%s;\">\n" %
                   (bgHex, bgHex))
        lvl += 1
        self._indent(lvl, res)
        res.extend(["<a href=\"", self._cellLinkUrl(cell, queryArgs),
                    "\">", self._cellText(cell), "</a>\n"])
        lvl -= 1
        self._indent(lvl, res)
        res.append("</td>\n")

        result = "".join(res)
        assert result is not None
        return result

    def _reverseColoursUrl(self):
        """
        Returns the URL that can be used to reload this page, but with its
        default foreground and background colours reversed/switched.
        """
        req = self._request
        queryArgs = req.args
        numQueryArgs = len(queryArgs)
        res = [req.base_url]
        prefix = "?"
        if _reverseColoursArgName in queryArgs:
            # Remove the query argument that reverses the colours.
            for k, v in queryArgs.items():
                if k != _reverseColoursArgName:
                    res.extend([prefix, k, "=", v])
                    prefix = "&"
        else:
            # Add the query argument that reverses the colours.
            if numQueryArgs > 0:
                res.append(prefix)
                res.append(req.query_string.decode())
                prefix = "&"
            res.extend([prefix, _reverseColoursArgName, "=",
                        _reverseColoursArgValue])
        #debug("   res=[{}]", str(res))
        result = "".join(res)
        assert result is not None
        return result

    def _cellLinkUrl(self, cell, queryArgs):
        """
        Returns (a string representation of) the URL for the hyperlink in the
        representation of the ColourGridCell 'cell'. Any and all mappings in
        the dict 'queryArgs' will be added to the URL as query arguments (or
        as part of the URL if the target endpoint recognizes them.)
        """
        assert cell is not None
        result = url_for("grid", depth = self._grid.depth() + 1,
                         startHexColour = cell.firstColour().hex(),
                         **queryArgs)
        assert result is not None
        return result

    def _cellText(self, cell):
        """
        Returns the (plain) text that is the contents of the table cell
        corresponding to the ColourGridCell 'cell'.
        """
        assert cell is not None
        ch = "+"
        result = "<span class=\"cell1\">{}</span><span " \
                 "class=\"cell2\">{}</span>".format(ch, ch)
        # hex = cell.middleColour().hex()
        # maxLen = self._maximumLinkTextLength
        # result = hex[0:(maxLen // 2)] + " "
        # if len(hex) <= maxLen:
        #     result += hex[(maxLen // 2):]
        # else:
        #     result += "..."
        assert result is not None
        return result


class LastPageBuilder(PageBuilder):
    """
    The PageBuilder to build the HTML pages for
    """

    # override
    def _cellLinkUrl(self, cell, queryArgs):
        assert cell is not None
        result = url_for("first", prev = cell.firstColour().hex(),
                         **queryArgs)
        assert result is not None
        return result


#
# Functions.
#

def gridPage(grid, req, msg = None):
    """
    Returns a string containing the contents of the HTML page for the
    ColourGrid 'grid', where the page was requested using the Flask request
    'req'. The page's contents will include the message 'msg' unless 'msg'
    is None.
    """
    assert grid is not None
    assert req is not None
    # 'msg' can be None
    if grid.colourComponentStepSize() == 1:
        b = LastPageBuilder(grid, req)
    else:
        b = PageBuilder(grid, req)
    if msg is not None:
        b.setMessage(msg)

    # Process the request arguments.
    #debug("rev = [{}]", req.args.get(_reverseColoursArgName))
    if req.args.get(_reverseColoursArgName) == _reverseColoursArgValue:
        b.reverseColours()

    result = b.build()
    assert result is not None
    return result


#
# Routes.
#

app = Flask(__name__)


@app.route("/")
def first():
    """
    Routes to the main/first colour grid page. Iff 'prev' isn't None then it
    is the hexadecimal string representation of the last colour that was
    selected.
    """
    #printRequestInfo(request)
    msg = request.args.get(_prevColourArgName)
    if msg is not None:
        msg = "Last colour selected: <span class=\"colour\">#{}</span>\n". \
              format(msg)
    return gridPage(ColourGrid.first(), request, msg)


@app.route("/<int:depth>/<startHexColour>")
def grid(depth, startHexColour):
    #printRequestInfo(request)
    result = None
    if depth >= 0:
        try:
            result = gridPage(ColourGrid(depth, Colour(startHexColour)),
                              request)
            assert result is not None
        except InvalidHexColourException:
            pass
        except InvalidGridDepthException:
            pass
        except:
            result = "<p>Internal server error.</p>", 500
            assert result is not None
    if result is None:
        result = "<p>Page not found.</p>", 404
    assert result is not None
    return result


def main(args):
    """
    Performs the action specified by the command line arguments 'args' that
    were passed to us when we were run as a standalone script and returns the
    exit code that we should exit with.
    """
    result = 0
    port = None
    numArgs = len(args)
    #debug("   args = {}, numArgs = {}", args, numArgs)
    if numArgs == 1:
        #debug("    first arg = {}", args[0])
        try:
            port = int(args[0])
        except ValueError:
            warn("invalid port number: {}", args[0])
            result = 2
    elif numArgs > 1:
        warn("too many arguments")
        result = 1

    if result == 0:
        app.run(debug = True, port = port)
    return result

if __name__ == '__main__':
    rc = main(sys.argv[1:])
    sys.exit(rc)
