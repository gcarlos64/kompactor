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

from kom import Kom

def eprint(*args, **kwargs):
    print('Error:', *args, file=sys.stderr, **kwargs)

def print_help(executable_name):
    print('Usage:', executable_name, '<option> <file> [out_file]')
    print()
    print('Options:')
    print('  -c, --create    Create a kom file from directory <file> named [out_file], if')
    print('                  specified. Otherwise, create a file of the same name of <file>')
    print('                  suffixed by .kom on the same directory of <file>. Directories')
    print('                  inside <file> are ignored.')
    print('  -l, --list      List file entries')
    print('  -k, --keep-crc  Keeps crc.xml. Write the extracted or generated crc.xml')
    print('                  next to the created or extracted files.')
    print('  -x, --extract   Extract <file> into [out_file] directory, if specified.')
    print('                  Otherwise, extract into a directory of the same name of the')
    print('                  <file> minus its suffix in the same directory.')
    print()
    print('Examples:')
    print(' ', executable_name, '-l file.kom    # List entries from file.kom.')
    print(' ', executable_name, '-x file.kom    # Extract file.kom into a directory named "file".')
    print(' ', executable_name, '-c dir         # Create dir.kom from the directory "dir".')
    print(' ', executable_name, '-c dir out.kom # Create out.kom from the directory "dir".')

def main(argv):
    if len(argv) == 1:
        print_help(argv[0])
        sys.exit(0)

    try:
        opts, args = getopt.getopt(argv[1:], 'chklx',
                                   ['create', 'help', 'keep-crc', 'list', 'extract'])
    except Exception as e:
        eprint(e)
        sys.exit(1)

    action = ''
    keep_crc = False
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print_help(argv[0])
            sys.exit(0)

        elif opt in ('-c', '--create'):
            action = 'c' if (action == '') else 'error'

        elif opt in ('-l', '--list'):
            action = 'l' if (action == '') else 'error'

        elif opt in ('-x', '--extract'):
            action = 'x' if (action == '') else 'error'

        elif opt in ('-k', '--keep-crc'):
            keep_crc = True

    if action == '':
        eprint('No actions specified. You should specify one')
        sys.exit(1)
    elif action == 'error':
        eprint('Multiple actions specified. You should specify just one')
        sys.exit(1)

    args_len = len(args)
    if args_len == 0:
        eprint('You should specify an input file or directory')
        sys.exit(1)
    elif args_len > 2:
        eprint('More than 2 files specified.',
               'You should specify just a single input file with optionally',
               'a second output file')
        sys.exit(1)
    else:
        in_file_path = args[0]

    if action == 'x':
        out_file_path = args[1] if args_len == 2 else args[0].rsplit('.', 1)[0]
        try:
            kom = Kom.from_kom_file(in_file_path)
            kom.extract(out_file_path, keep_crc)
        except Exception as e:
            eprint(e)
            sys.exit(1)

    elif action == 'c':
        out_file_path = args[1] if args_len == 2 else args[0] + '.kom'
        try:
            kom = Kom.from_files(in_file_path, 2)
            with open(out_file_path, 'wb') as f:
                f.write(kom.to_file())

            if keep_crc:
                crc_path = os.path.join(os.path.split(out_file_path)[0], 'crc.xml')
                with open(crc_path, 'wb') as f:
                    f.write(kom.crc)

        except Exception as e:
            eprint(e)
            sys.exit(1)

    elif action == 'l':
        try:
            kom = Kom.from_kom_file(in_file_path)
            for entry in kom.entries:
                print(entry.name)
        except Exception as e:
            eprint(e)
            sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)
