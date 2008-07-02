# Copyright (C) 2008 by Kai Blin
#
# WOMBAT is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA

from os.path import getsize, join, basename, getmtime
from time import strftime, gmtime
from pylons import config

class File:
    def __init__(self, path):
        self.path = path
        self.type = "Generic file"
        self.fullpath = join(config['app_conf']['media_dir'], path)
        self.size = getsize(self.fullpath)
        self.mtime = getmtime(self.fullpath)

    def getPath(self):
        return self.path

    def getName(self):
        return basename(self.path)

    def getSize(self):
        return self.size

    def getPrettySize(self):
        size = self.size
        i = 0
        size_name = ['B', 'kB', 'MB', 'GB']
        while size > 1024 and i < len(size_name):
            size /= 1024.0
            i += 1
        return "%.2f %s" % (size, size_name[i])

    def getType(self):
        return "file"

    def getMtime(self):
        return self.mtime

    def getLastChanged(self):
        return strftime("%Y-%m-%d %H:%M:%S %Z", gmtime(self.mtime))

