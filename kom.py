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
from xml.dom.minidom import Document

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
    def relative_offset(self):
        return self._relative_offset

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
                           self._relative_offset)

    @property
    def crc32(self):
        return zlib.crc32(self._data)

    def __init__(self, name, uncompressed_size, compressed_size, relative_offset, data):
        self._name = name if (type(name) is str) else name.decode('ascii').rstrip('\0')
        self._uncompressed_size = uncompressed_size
        self._compressed_size = compressed_size
        self._relative_offset = relative_offset

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
        uncompressed_size = os.path.getsize(file_path)

        with open(file_path, 'rb') as f:
            data = zlib.compress(f.read())

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
        self._data = raw_data[self._relative_offset :
                              self._relative_offset + self._compressed_size]

class Crc:
    @property
    def xml(self):
        try:
            return self._xml
        except AttributeError:
            return self.gen_xml()

    def __init__(self, version):
        # version must be an integer
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

    def append_entry(self, entry):
        dom_file_item = self._dom.createElement('Item')
        dom_file_item.setAttribute('Name', entry.name)
        dom_file_item.setAttribute('Size', str(entry.uncompressed_size))
        dom_file_item.setAttribute('Version', '0')
        dom_file_item.setAttribute('CheckSum', '%08x' % entry.crc32)
        self._dom_files.appendChild(dom_file_item)

    def gen_xml(self):
        self._xml = self._dom.toprettyxml(indent='    ', encoding='ascii')
        return self._xml

class Kom:
    header_size = 60

    @property
    def entries(self):
        return self._entries

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
    def crc(self):
        return self._entries[-1].uncompressed_data

    def __init__(self, entries, version):
        self._entries = entries
        self._version = version

    @classmethod
    def from_kom_file(cls, file_path):
        entries = []

        with open(file_path, 'rb') as f:
            header = f.read(Kom.header_size)
            f.seek(Kom.header_size)

            raw_version, entry_count = struct.unpack_from('<27s25xI4x', header)
            version = int(raw_version.decode('ascii').split('.')[-2])

            entries_size = Entry.metadata_size * entry_count
            raw_entries = f.read(entries_size)
            f.seek(Kom.header_size + entries_size)

            raw_data = f.read()

            offset = 0
            for i in range(entry_count):
                entry = Entry.from_kom_data(raw_entries[offset :
                                                        offset + Entry.metadata_size],
                                            raw_data)
                entries.append(entry)
                offset += Entry.metadata_size

        return cls(entries, version)

    @classmethod
    def from_files(cls, in_dir_path, version):
        entries = []

        crc = Crc(version)

        relative_offset = 0
        for file_name in sorted(os.listdir(in_dir_path)):
            file_path = os.path.join(in_dir_path, file_name)

            if os.path.isdir(file_path):
                continue

            if file_name == 'crc.xml':
                continue

            if len(file_name) > 60:
                raise Exception('the file {:!} is nammed bigger than 60 characters'.format(file_path))

            entry = Entry.from_file(file_path, relative_offset)
            relative_offset += entry.compressed_size

            crc.append_entry(entry)
            entries.append(entry)

        entry = Entry.from_data(crc.xml, 'crc.xml', relative_offset)
        entries.append(entry)

        return cls(entries, version)

    def to_file(self):
        entries_metadata = bytearray()
        data = bytearray()

        raw_version = 'KOG GC TEAM MASSFILE '.encode('ascii') + \
                      self.version_str.encode('ascii')

        # I don't know what is that "1" number here, but it seems that any .kom
        # file has it in that place.
        header = struct.pack('<27s25x2I', raw_version, len(self._entries), 1)

        for e in self._entries:
            entries_metadata += e.packed_metadata
            data += e.data

        return header + entries_metadata + data

    def extract(self, out_dir, keep_crc=False):
        try:
            os.makedirs(out_dir)
        except FileExistsError as e:
            if os.path.isdir(out_dir):
                pass
            else:
                raise e

        offset = 0
        entries = self._entries if keep_crc else self._entries[:-1]
        for entry in entries:
            try:
                out_file_path = os.path.join(out_dir, entry.name)

                with open(out_file_path, 'wb') as f:
                    f.write(entry.uncompressed_data)

            except Exception as e:
                raise e
