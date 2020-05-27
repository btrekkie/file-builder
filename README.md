# Summary
The `FileBuilder` class performs caching for operations that depend on files and
file contents. It is useful for "build" operations that are performed repeatedly
on a group of files that mostly stay the same between builds. By caching
arbitrary information about those files, it can significantly speed up build
operations.

An example use case would be linting all of the source code files in a given
directory. By caching the lint results for each of the files, `FileBuilder`
would ensure we don't re-lint any files that haven't changed since the last
build.

A more complex example would be scanning all of the files in a directory for
mathematical formulas, and generating image files for each of those formulas.
`FileBuilder` would ensure that we only scan files that have changed since the
last build, since it would already have cached the set of formulas that appears
in each of the unchanged files. Furthermore, `FileBuilder` would ensure that we
only generate image files for formulas that don't already have image files,
since it would reuse the appropriate images from the previous build.

`FileBuilder`'s interface makes it appear as though each time we build we start
over from scratch, while still achieving the aforementioned performance
benefits.

# Features
* Speed up a build operation by using caching.
* Build operations are arbitrary functions passed as arguments to `FileBuilder`.
* Protects against exceptions raised by the build function by means of a
  rollback feature.
* `FileBuilder` is thread-safe, so a build process may be parallelized using
  multithreading or multiprocessing.
* Build functions can have version numbers. If the implementation of a build
  function changes, we can force that function to be rerun in the next build by
  changing its version.
* Provides a `clean` method for removing any output files created by a build
  operation.
* Compatible with Python 3.4 and above.

# Limitations
* `FileBuilder` does not expose any information about the state from the
  previous build. For example, it does not provide a list of the files that have
  changed since the last build. (Ugly workarounds are possible.)
* Batching is not supported. To use the lint example, it could be that it is
  faster to lint a group of files all at once by passing all of their filenames
  to the linter, compared to linting them one at a time. Normally, it's not
  possible to take advantage of batching, except by using clunky workarounds.
* `FileBuilder` does not allow for the direct manipulation of any output files
  from the last build. If an output file needs to be changed, then we have to
  regenerate that file from scratch.

# Example
`FileBuilder` is perhaps best introduced with an example. The `lint_dir`
function below lints all of the Python files in a given directory, using the
`flake8` command:

```python
import os, subprocess
from file_builder import FileBuilder

def lint_dir(root_dir, cache_filename):
    # Equivalent to lint_with_builder(-, root_dir)
    output = FileBuilder.build(
        cache_filename, 'lint_dir', lint_with_builder, root_dir)
    print(output, end='')

def lint_with_builder(builder, root_dir):
    output = []
    for filename in python_files_in_dir(builder, root_dir):
        # Equivalent to lint_file(-, filename), but with caching
        file_output = builder.subbuild('lint_file', lint_file, filename)
        output.append(file_output)
    return ''.join(output)

def python_files_in_dir(builder, root_dir):
    python_files = []
    for dir_, subdirs, subfiles in builder.walk(root_dir):
        for subfile in subfiles:
            if subfile.endswith('.py'):
                python_files.append(os.path.join(dir_, subfile))
    return python_files

def lint_file(builder, filename):
    builder.declare_read(filename)

    # Return the output of the flake8 command
    process = subprocess.run(['flake8', filename], capture_output=True)
    return process.stdout.decode()
```

# Description
Calling `FileBuilder.build` or `FileBuilder.build_versioned` runs a build
operation. There are two types of cacheable operations that may occur during a
build: "build file" operations, triggered by calling `FileBuilder.build_file` or
`FileBuilder.build_file_with_comparison`, and "subbuild" operations, triggered
by calling `FileBuilder.subbuild`. Whenever we call `build_file`,
`build_file_with_comparison`, or `subbuild`, we check whether the result is
cached. If so, we use the cached result. If not, we obtain the result by calling
the function that was supplied as an argument.

For this to work properly, the functions used to rebuild files or execute
subbuilds must obey certain rules:

* They must be functional. That is, they must depend only on their arguments and
  on the contents of the file system, and they may not have any side effects.
  (Irrelevant side effects like printing to standard output or writing to a log
  file are permitted.)
* They must be deterministic. For their given arguments, and given the current
  contents of the file system, they must produce the same results - or at least
  equivalent results from the application's perspective.
* All file system operations on the relevant files must be performed by calling
  a `FileBuilder` method. For example, it is invalid to call `os.path.isdir`;
  the function must call `FileBuilder.is_dir` instead. This does not apply to
  "irrelevant" files that we are not operating on, such as log files, temporary
  files, or external binary files.
* As a corollary, we may only read from files passed to the `read_text`,
  `read_binary`, and `declare_read` methods. Again, this does not apply to
  "irrelevant" files.
* Another corollary: We may only write to a (relevant) file during a call to
  `build_file` or `build_file_with_comparison` for that file.

If these restrictions are followed, then the behavior of `FileBuilder.build` is
equivalent to the following:

* Remove all files created during the previous build.
* Call the function passed as an argument to `FileBuilder.build`.
* Whenever we call `build_file`, `build_file_with_comparison`, or `subbuild`,
  call the function passed as an argument.
* If the function passed to `FileBuilder.build` doesn't raise an exception,
  return that function's return value.
* If the function passed to `FileBuilder.build` raises an exception, roll back.
  That is, remove all of the files created during the current build, and restore
  all of the files written during the previous build.

Even though this is what `FileBuilder.build` appears to be doing, this is not
what actually happens behind the scenes. In reality, whenever we can use a
previously cached result instead of calling a function passed as an argument to
a `FileBuilder` method, we do so. Using a cached result is legitimate if the
filename and function name are the same, the arguments to the function are the
same, the optional version is the same, and all of the file system operations
have the same results.

In addition, to save time, `FileBuilder` doesn't initially delete any of the
files written during the previous build. It's possible that many of these files
won't need to be touched at all, because their cache entries are still valid.
For this and other reasons, the results of `FileBuilder`'s file system methods,
such as `is_file` and `list_dir`, depend on the virtual state of the file system
maintained by `FileBuilder`, not simply on the real state of the file system.

`FileBuilder` does its best to deal with concurrent external changes to files
and directories, but it makes no guarantees.

`FileBuilder` is thread-safe. A build process may be parallelized using
multithreading or multiprocessing. However, be aware that the global interpreter
lock affects the effectiveness of multithreading with regard to parallelism; see
<https://wiki.python.org/moin/GlobalInterpreterLock>.

# Documentation
See <https://btrekkie.github.io/file-builder/index.html> for API documentation.

# Additional examples
* [`lint`](samples/lint): A re-presentation of the Lint example.
* [`gzip`](samples/gzip): A simple example that illustrates
  `FileBuilder.build_file`.
* [`parallel_seam_carving`](samples/parallel_seam_carving): Demonstrates one
  possible approach to parallelizing a build.
