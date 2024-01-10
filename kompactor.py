#!/usr/bin/env python3

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
 
import getopt
import sys
import os
import errno

from kom import Kom

help_message = '''
Usage: {executable} <action> <options> <file-list>

Actions:
  -c, --create        Create a kom file from directory <file-list>. If a
                      directory was specified, include all regular files from
                      it. Files named "crc.xml" or with name length higher than
                      60 characters are ignored.

      --examples      Show some usage examples.

  -h, --help          Show this help message.

  -l, --list          List file entries on KOM files specified on <file-list>.

  -x, --extract       Extract the KOM file specified on the first element of
                      <file-list> entirely. If additional files specified on
                      <file-list>, extract only them from the KOM instead.

Options:
  -f, --force         Force overwriting files. This has no effect when trying
                      to overwrite directories, since it is not allowed.

  -k, --keep-crc      Keeps crc.xml. Write the extracted or generated crc.xml
                      next to the created or extracted files.

  -o  --output <arg>  Specify the output KOM file for creation or the output
                      directory for extraction, creating it if it doesn't
                      exists. If not specified, extracted files goes on the
                      current directory and created KOM files goes to a file
                      named "a.kom", also in the current directory.
'''

examples = '''
Examples:
 {executable} -l file.kom
   List entries from file.kom.

 {executable} -x file.kom
   Extract file.kom on the current directory.

 {executable} -kx file.kom -o dir
   Extract file.kom on the directory "dir", as well as its "crc.xml".

 {executable} -c dir file1 file2 -o out.kom
   Create out.kom from the contents of directory "dir" plus file1 and file2.
'''


def eprint(*args, **kwargs):
    print('Error:', *args, file=sys.stderr, **kwargs)

def print_help(executable_name):
    print(help_message.format(executable=executable_name))

def print_examples(executable_name):
    print(examples.format(executable=executable_name))

def extract(kom, i, out_file_path, force_overwrite):
    try:
        kom.extract(i, out_file_path, force_overwrite)
    except FileExistsError as e:
        eprint('Trying to overwrite "%s" file' % e.filename)
        sys.exit(e.errno)
    except IsADirectoryError as e:
        eprint('Trying to overwrite "%s" directory' % e.filename)
        sys.exit(e.errno)

    if i == 'crc':
        print('Extracted crc.xml')
    else:
        print('Extracted', kom.entries[i].name)

def write(file_path, data, force_overwrite):
    if not force_overwrite and os.path.isfile(file_path):
        eprint('Trying to overwrite "%s" file' % file_path)
        sys.exit(errno.EEXIST)

    try:
        with open(file_path, 'wb') as f:
            f.write(data)
    except IsADirectoryError as e:
        eprint('Trying to overwrite "%s" directory' % e.filename)
        sys.exit(e.errno)

def main(argv):
    if len(argv) == 1:
        print_help(argv[0])
        sys.exit(0)

    try:
        opts, args = getopt.gnu_getopt(argv[1:], 'cfhklo:x',
                                       ['create', 'force', 'help', 'keep-crc',
                                        'list', 'output=', 'extract', 'examples'])
    except Exception as e:
        eprint(e)
        sys.exit(1)

    action = ''
    force_overwrite = False
    keep_crc = False
    out_file_path = None
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print_help(argv[0])
            sys.exit(0)

        elif opt == '--examples':
            print_examples(argv[0])
            sys.exit(0)

        elif opt in ('-c', '--create'):
            action = 'create' if (action == '') else 'error'

        elif opt in ('-l', '--list'):
            action = 'list' if (action == '') else 'error'

        elif opt in ('-x', '--extract'):
            action = 'extract' if (action == '') else 'error'

        elif opt in ('-f', '--force'):
            force_overwrite = True

        elif opt in ('-k', '--keep-crc'):
            keep_crc = True

        elif opt in ('-o', '--output'):
            out_file_path = arg

    if action == '':
        eprint('No actions specified. You should specify one')
        sys.exit(1)
    elif action == 'error':
        eprint('Multiple actions specified. You should specify just one')
        sys.exit(1)

    args_len = len(args)
    if args_len == 0:
        eprint('You should specify at least one input file or directory')
        sys.exit(1)

    if action == 'extract':
        in_file_path = args[0]
        file_list = args[1:]
        if not out_file_path:
            out_file_path = os.path.relpath(os.getcwd())

        kom = Kom.from_kom_file(in_file_path)

        index_list = [i for i in range(len(kom.entries))
                      if kom.entries[i].name in file_list or
                      file_list == []]

        if len(index_list) == 0:
            eprint('No valid file entry was provided for extraction')
            sys.exit(1)

        for i in index_list:
            extract(kom, i, out_file_path, force_overwrite)

        if keep_crc:
            extract(kom, 'crc', out_file_path, force_overwrite)

    elif action == 'create':
        file_list = []
        if not out_file_path:
            out_file_path = os.path.join(os.path.relpath(os.getcwd()), 'a.kom')

        kom = Kom(2)

        for f in args:
            file_list.extend([f] if os.path.isfile(f) else [e.path for e in os.scandir(f)])

        for file_path in file_list:
            file_name = os.path.split(file_path)[1]
            if file_name == 'crc.xml':
                print('Ignoring', file_name)
                continue

            kom.add_file(file_path)
            print('Included', file_name)

        write(out_file_path, kom.to_file(), force_overwrite)
        print('Created', os.path.split(out_file_path)[1])

        if keep_crc:
            crc_path = os.path.join(os.path.split(out_file_path)[0], 'crc.xml')
            write(crc_path, kom.crc_xml, force_overwrite)
            print('Written crc.xml')

    # TODO: handle errors, format output better and add header
    elif action == 'list':
        for f in args:
            kom = Kom.from_kom_file(f)
            for entry in kom.entries:
                print('{}: {} {} {}'.format(f, entry.name, entry.compressed_size,
                                            entry.uncompressed_size))

if __name__ == "__main__":
    main(sys.argv)
