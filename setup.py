## Uses setuptools to create distributable versions of this application.
#
# Note: this is based heavily on code from
# https://flask.palletsprojects.com/en/2.1.x/patterns/distribute/
#
# Copyright (C) 2022 by James MacKay.
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

"""
A small web application for selecting a 24-bit RGB colour value by
selecting one from a grid of colours and then refining it by selecting one
close to it from (two) successive grids.
"""

from setuptools import setup, find_packages

setup(
    name = 'ColourGrid',
    version = '1.0',
    author = 'James MacKay',
    author_email = 'jgm@steelcandy.org',
    url = 'https://github.com/steelcandy2/ColourGrid',
    long_description = __doc__,
    license = 'GPL3',
    description = 'Web application for selecting RGB colours from ' + \
                  'successive grids of them.',
    packages = find_packages(),
    include_package_data = True,  # since we don't currently have any
    zip_safe = False,
    install_requires = ['Flask'],
)
