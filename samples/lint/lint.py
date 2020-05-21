import os
import subprocess

from file_builder import FileBuilder


def lint_dir(root_dir, cache_filename):
    """Print the output of ``flake8`` on the ``*.py`` files in ``root_dir``.

    Print the result of executing the ``flake8`` shell command on all of
    the ``*.py`` files in the specified directory, including
    subdirectories.

    Arguments:
        root_dir (str): The directory.
        cache_filename (str): The file used to store cached results.
    """
    output = FileBuilder.build(
        cache_filename, 'flake8_dir_sample', _lint_with_builder, root_dir)
    print(output, end='')


def _lint_with_builder(builder, root_dir):
    """Return the output of ``flake8`` on the ``*.py`` files in ``root_dir``.

    Return the result of executing the ``flake8`` shell command on all
    of the ``*.py`` files in the specified directory, including
    subdirectories.

    Arguments:
        builder (FileBuilder): The ``FileBuilder``.
        root_dir (str): The directory.

    Returns:
        str: The output.
    """
    output = []
    for filename in _python_files_in_dir(builder, root_dir):
        file_output = builder.subbuild('lint_file', _lint_file, filename)
        output.append(file_output)
    return ''.join(output)


def _python_files_in_dir(builder, root_dir):
    """Return a list of the ``*.py`` files in the specified directory.

    This includes subdirectories.

    Arguments:
        builder (FileBuilder): The ``FileBuilder``.
        root_dir (str): The directory.

    Returns:
        list<str>: The files.
    """
    python_files = []
    for dir_, subdirs, subfiles in builder.walk(root_dir):
        for subfile in subfiles:
            if subfile.endswith('.py'):
                python_files.append(os.path.join(dir_, subfile))
    return python_files


def _lint_file(builder, filename):
    """Return the output from running ``flake8`` on the specified file.

    Arguments:
        builder (FileBuilder): The ``FileBuilder``.
        filename (str): The file.

    Returns:
        str: The output.
    """
    builder.declare_read(filename)
    process = subprocess.run(['flake8', filename], capture_output=True)
    return process.stdout.decode()
