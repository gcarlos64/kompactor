# Kompactor
Kompactor is a cli tool for creating and extracting Grand Chase `.kom` files.

The project is splitted in just 2 files, `kom.py`, which is the library
that implement `.kom` files operations and `kompactor.py`, which is
the cli interface built on top of it.

# Usage
You can run the `kompactor.py` like any other python script:
```
$ python kompactor.py
```
By default, with no argument, it will print the help message, which contain the
usage description, as well as examples.

If you're on GNU/Linux, you can execute it directly:
```
$ chmod +x kompactor.py
$ ./kompactor.py
```

# Limitations
Currently, `.kom` creation, extraction and list is only implemented
for the version `V.0.0.2.` (aka `V2`) of the KOM format, as I initially
target handling files from the Season 2. Further versions may be implemented
by me if I start to work with these or by anyone willing to, it's free software
and is always welcome to contributors.

The tool can't handle multiples `.kom` files on a instance neither receive
files instead of directories for `.kom` creation, as I personally
prefer to do it with the shell instead of putting complexity on the tool.
Anyway, this can be considered an improvement if someone decide to implement.

# TODO
This tool in its current state just do its job, nothing more. There's a lot
of room for improvements, like:

- Package it.
- Document the code.
- Implement better error handling.
- Add support for warnings, as well as verbosity level control.
- Add checksum validation on extraction.
- Add support to more KOM versions.
- Add support for handling multiple files (both extracting multiples `.kom`
  and creating from explicit files instead of just with a directory).
