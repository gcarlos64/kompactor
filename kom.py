# Copyright (C) 2024 Carlos E. Gallo <gacrlos@disroot.org>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import struct
import sys
import os
import zlib
from xml.dom.minidom import Document, parseString

class Entry:
    metadata_size = 72

    @property
    def name(self):
        return self._name

    @property
    def uncompressed_size(self):
        return self._uncompressed_size

    @property
    def compressed_size(self):
        return self._compressed_size

    @property
    def data(self):
        return self._data

    @property
    def compressed_data(self):
        return self._data

    @property
    def uncompressed_data(self):
        return zlib.decompress(self._data)

    @property
    def packed_metadata(self):
        return struct.pack('<60s3I',
                           self._name.encode('ascii'),
                           self._uncompressed_size,
                           self._compressed_size,
                           self.relative_offset)

    @property
    def crc32(self):
        return zlib.crc32(self._data)

    def __init__(self, name, uncompressed_size, compressed_size, relative_offset, data):
        self._name = name if (type(name) is str) else name.decode('ascii').rstrip('\0')
        self._uncompressed_size = uncompressed_size
        self._compressed_size = compressed_size
        self.relative_offset = relative_offset

        # This is compressed data
        self._data = data

    @classmethod
    def from_kom_data(cls, entry_metadata, raw_data):
        # entry_metadata must be a 72 lenghted bytearray and raw_data is the
        # entire kom file minus all its metadata
        e = cls(*struct.unpack_from('<60s3I', entry_metadata), None)
        e._read(raw_data)
        return e

    @classmethod
    def from_file(cls, file_path, relative_offset):
        name = os.path.split(file_path)[1]

        if len(name) > 60:
            raise Exception('the file "%s" is nammed bigger than 60 characters' % name)


        with open(file_path, 'rb') as f:
            data = zlib.compress(f.read())

        uncompressed_size = os.path.getsize(file_path)
        compressed_size = len(data)
        return cls(name, uncompressed_size, compressed_size, relative_offset, data)

    @classmethod
    def from_data(cls, raw_data, name, relative_offset):
        name = name
        uncompressed_size = len(raw_data)
        data = zlib.compress(raw_data)
        compressed_size = len(data)
        return cls(name, uncompressed_size, compressed_size, relative_offset, data)

    # Read the kom file data segment
    def _read(self, raw_data):
        self._data = raw_data[self.relative_offset :
                              self.relative_offset + self._compressed_size]

class Crc:
    @property
    def xml(self):
        if self._parsed:
            return self._dom.toxml(encoding='ascii')
        else:
            return self._dom.toprettyxml(indent='    ', encoding='ascii')

    def __init__(self, version, entry=None):
        # version must be an integer

        if entry:
            self._dom = parseString(entry.uncompressed_data)
            self._parsed = True

        else:
            self._dom = Document()

            dom_file_info = self._dom.createElement('FileInfo')
            self._dom.appendChild(dom_file_info)

            dom_version = self._dom.createElement('Version')
            dom_file_info.appendChild(dom_version)

            dom_version_item = self._dom.createElement('Item')
            dom_version_item.setAttribute('Name', Kom.format_version(version))
            dom_version.appendChild(dom_version_item)

            self._dom_files = self._dom.createElement('File')
            dom_file_info.appendChild(self._dom_files)

            self._parsed = False

    def append_entry(self, entry):
        dom_file_item = self._dom.createElement('Item')
        dom_file_item.setAttribute('Name', entry.name)
        dom_file_item.setAttribute('Size', str(entry.uncompressed_size))
        dom_file_item.setAttribute('Version', '0')
        dom_file_item.setAttribute('CheckSum', '%08x' % entry.crc32)
        self._dom_files.appendChild(dom_file_item)

class Kom:
    header_info_size = 60

    @property
    def entries(self):
        return self._entries

    @property
    def crc_entry(self):
        return self._crc_entry

    @property
    def version(self):
        return self._version

    @staticmethod
    def format_version(version):
        return 'V.0.%d.' % version

    @property
    def version_str(self):
        return Kom.format_version(self._version)

    @property
    def crc_xml(self):
        return self._crc.xml

    def __init__(self, version, entries=[], crc=None):
        self._version = version
        self._entries = entries

        if crc:
            self._crc = crc
            self._crc_entry = self._entries[-1]
            del self._entries[-1]
        else:
            self._crc = None
            self._crc_entry = None

    @classmethod
    def from_kom_file(cls, file_path):
        entries = []

        with open(file_path, 'rb') as f:
            header = f.read(Kom.header_info_size)
            f.seek(Kom.header_info_size)

            raw_version, entry_count = struct.unpack_from('<27s25xI4x', header)
            version = int(raw_version.decode('ascii').split('.')[-2])

            entries_size = Entry.metadata_size * entry_count
            raw_entries = f.read(entries_size)
            f.seek(Kom.header_info_size + entries_size)

            raw_data = f.read()

        offset = 0
        for i in range(entry_count):
            entry = Entry.from_kom_data(raw_entries[offset :
                                                    offset + Entry.metadata_size],
                                        raw_data)
            entries.append(entry)
            offset += Entry.metadata_size

        crc = Crc(version, entry=entries[-1])

        return cls(version, entries=entries, crc=crc)

    def add_file(self, file_path):
        file_name = os.path.split(file_path)[1]

        if file_name == 'crc.xml':
            return

        if len(file_name) > 60:
            return

        for e in self._entries:
            if e.name == file_name:
                return

        entry = Entry.from_file(file_path, self._relative_offset)
        self._entries.append(entry)

    def to_file(self):
        self._crc = Crc(self._version)
        entries_metadata = bytearray()
        data = bytearray()

        raw_version = 'KOG GC TEAM MASSFILE '.encode('ascii') + \
                      self.version_str.encode('ascii')

        # I don't know what is that "1" number here, but it seems that any .kom
        # file has it in that place.
        header_info = struct.pack('<27s25x2I', raw_version, len(self._entries) + 1, 1)

        self._sort_entries()
        for entry in self._entries:
            self._crc.append_entry(entry)
            entries_metadata += entry.packed_metadata
            data += entry.data

        entry = Entry.from_data(self._crc.xml, 'crc.xml', self._relative_offset)
        entries_metadata += entry.packed_metadata
        data += entry.data

        return header_info + entries_metadata + data

    def extract(self, entry_index, out_dir):
        try:
            os.makedirs(out_dir)
        except FileExistsError as e:
            if os.path.isdir(out_dir):
                pass
            else:
                raise e

        entry = self._crc_entry if entry_index == 'crc' else self._entries[entry_index]
        out_file_path = os.path.join(out_dir, entry.name)
        with open(out_file_path, 'wb') as f:
            f.write(entry.uncompressed_data)

    @property
    def _relative_offset(self):
        if len(self._entries) == 0:
            return 0
        else:
            last_entry = self._entries[-1]
            return last_entry.relative_offset + last_entry.compressed_size

    def _sort_entries(self):
        self._entries.sort(key=lambda x: x.name)

        # Recalculate relative offsets
        relative_offset = 0
        for e in self._entries:
            e.relative_offset = relative_offset
            relative_offset += e.compressed_size
