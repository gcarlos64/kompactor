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

from kom import Kom, IgnoredFile, MultipleFilesError

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

  -p, --print         Like extract, but print the files on stdout instead.

  -x, --extract       Extract the KOM file specified on the first element of
                      <file-list> entirely. If additional files specified on
                      <file-list>, extract only them from the KOM instead.

Options:
  -f, --force         Force overwriting files. This has no effect when trying
                      to overwrite directories, since it is not allowed.

  -i, --ignore        Allows to ignore files.

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

overwrite_file_err_msg = 'Unable to overwrite "%s" file. It it was intentional, run with -f option'
overwrite_dir_err_msg = 'Unable to overwrite "%s" directory'
no_action_err_msg = 'No actions specified. You should specify one'
multiple_actions_err_msg = 'Multiple actions specified. You should specify just one'
no_input_err_msg = 'You should specify at least one input file or directory'
kom_not_valid_err_msg = '"%s" is not a valid KOM file'
no_file_entry_err_msg = 'No valid file entry was provided for extraction'
ignore_err_msg = 'Unable to ignore %s. If it was intentional, run with -i option'
include_err_msg = 'Unable to include multiples files named "%s"'
bad_extract_output_err_msg = 'Unable to extract, the output %s is a regular file'
extract_no_entry_err_msg = 'Unable to extract "%s" from KOM, there is no such entry'

def eprint(*args, **kwargs):
    print('Error:', *args, file=sys.stderr, **kwargs)

def print_help(executable_name):
    print(help_message.format(executable=executable_name))

def print_examples(executable_name):
    print(examples.format(executable=executable_name))

def write(data, file_path, force_overwrite):
    if not force_overwrite and os.path.isfile(file_path):
        eprint(overwrite_file_err_msg % file_path)
        sys.exit(errno.EEXIST)

    try:
        with open(file_path, 'wb') as f:
            f.write(data)
    except IsADirectoryError as e:
        eprint(overwrite_dir_err_msg % e.filename)
        sys.exit(e.errno)

def main(argv):
    if len(argv) == 1:
        print_help(argv[0])
        sys.exit(0)

    try:
        opts, args = getopt.gnu_getopt(argv[1:], 'cfhiklpo:x',
                                       ['create', 'force', 'help', 'ignore',
                                        'keep-crc', 'list', 'print', 'output=',
                                        'extract', 'examples'])
    except Exception as e:
        eprint(e)
        sys.exit(1)

    action = ''
    force_overwrite = False
    keep_crc = False
    ignore_files = False
    out_path= None
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

        elif opt in ('-p', '--print'):
            action = 'print' if (action == '') else 'error'

        elif opt in ('-x', '--extract'):
            action = 'extract' if (action == '') else 'error'

        elif opt in ('-f', '--force'):
            force_overwrite = True

        elif opt in ('-k', '--keep-crc'):
            keep_crc = True

        elif opt in ('-i', '--ignore'):
            ignore_files = True

        elif opt in ('-o', '--output'):
            out_path = arg

    if action == '':
        eprint(no_action_err_msg)
        sys.exit(1)
    elif action == 'error':
        eprint(multiple_actions_err_msg)
        sys.exit(1)

    args_len = len(args)
    if args_len == 0:
        eprint(no_input_err_msg)
        sys.exit(1)

    if action == 'extract':
        in_file_path = args[0]

        try:
            kom = Kom.from_kom_file(in_file_path)
        except:
            eprint(kom_not_valid_err_msg % in_file_path)
            sys.exit(1)

        entry_list = args[1:] if len(args) > 1 else [e for e in kom.entries]
        if keep_crc and 'crc.xml' not in entry_list:
            entry_list.append('crc.xml')

        if out_path:
            if os.path.isfile(out_path):
                eprint(bad_extract_output_err_msg % out_path)
                sys.exit(1)
            elif not os.path.isdir(out_path):
                os.makedirs(out_path)
        else:
            out_path = os.path.relpath(os.getcwd())

        for e in entry_list:
            file_name = e if type(e) == str else e.name
            out_file_path = os.path.join(out_path, file_name)
            try:
                write(kom.extract(e), out_file_path, force_overwrite)
            except TypeError:
                eprint(extract_no_entry_err_msg % file_name)
                sys.exit(1)
            print('Extracted', file_name)

    elif action == 'print':
        in_file_path = args[0]

        try:
            kom = Kom.from_kom_file(in_file_path)
        except:
            eprint(kom_not_valid_err_msg % in_file_path)
            sys.exit(1)

        entry_list = args[1:] if len(args) > 1 else [e for e in kom.entries]
        if keep_crc and 'crc.xml' not in entry_list:
            entry_list.append('crc.xml')

        for e in entry_list:
            try:
                file_name = e if type(e) == str else e.name
                sys.stdout.buffer.write(kom.extract(e))
            except ValueError as e:
                eprint(extract_no_entry_err_msg % file_name)
                sys.exit(1)

    elif action == 'create':
        file_list = []
        if not out_path:
            out_path = os.path.join(os.path.relpath(os.getcwd()), 'a.kom')

        kom = Kom(2)

        for f in args:
            file_list.extend([f] if os.path.isfile(f) else [e.path for e in os.scandir(f)])

        for file_path in file_list:
            file_name = os.path.split(file_path)[1]

            try:
                kom.add_file(file_path)
            except IgnoredFile:
                if ignore_files:
                    print('Ignoring', file_name)
                    pass
                else:
                    eprint(ignore_err_msg % file_name)
                    sys.exit(1)
                pass
            except MultipleFilesError as e:
                eprint(include_err_msg % e.file_name)
                sys.exit(1)
            else:
                print('Included', file_name)

        write(kom.to_file(), out_path, force_overwrite)
        print('Created', os.path.split(out_path)[1])

        if keep_crc:
            crc_path = os.path.join(os.path.split(out_path)[0], 'crc.xml')
            write(kom.crc_xml, crc_path, force_overwrite)
            print('Written crc.xml')

    # TODO: handle errors, format output better and add header
    elif action == 'list':
        for f in args:
            try:
                kom = Kom.from_kom_file(f)
            except:
                eprint(kom_not_valid_err_msg  % f)
                sys.exit(1)

            for entry in kom.entries:
                print('{}: {} {} {}'.format(f, entry.name, entry.compressed_size,
                                            entry.uncompressed_size))

if __name__ == "__main__":
    main(sys.argv)
