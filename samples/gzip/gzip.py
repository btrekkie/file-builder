import gzip
import os

from file_builder import FileBuilder


def gzip_dir(input_dir, output_dir, cache_filename):
    """Compress the files in ``input_dir`` and its subdirectories using gzip.

    For each file in the input directory, this creates a compressed file
    in the output directory with the same name, but with ".gz" appended
    to it. It creates a directory structure in the output directory that
    matches the directory structure in the input directory.

    Arguments:
        input_dir (str): The input directory.
        output_dir (str): The output directory.
        cache_filename (str): The file used to store cached results.
    """
    FileBuilder.build(
        cache_filename, 'gzip_dir_sample', _gzip_with_builder, input_dir,
        output_dir)


def _gzip_file(builder, output_filename, input_filename):
    """Compress ``input_filename`` using gzip.

    Store the results in ``output_filename``.

    Arguments:
        builder (FileBuilder): The ``FileBuilder``.
        output_filename (str): The output filename.
        input_filename (str): The input filename.
    """
    with gzip.open(output_filename, 'wb') as output_file:
        with builder.read_binary(input_filename) as input_file:
            bytes_ = input_file.read(1024)
            while len(bytes_) > 0:
                output_file.write(bytes_)
                bytes_ = input_file.read(1024)


def _gzip_with_builder(builder, input_dir, output_dir):
    """Compress the files in ``input_dir`` and its subdirectories using gzip.

    For each file in the input directory, this creates a compressed file
    in the output directory with the same name, but with ".gz" appended
    to it. It creates a directory structure in the output directory that
    matches the directory structure in the input directory.

    Arguments:
        builder (FileBuilder): The ``FileBuilder``.
        input_dir (str): The input directory.
        output_dir (str): The output directory.
    """
    for dir_, subdirs, subfiles in builder.walk(input_dir):
        for subfile in subfiles:
            input_filename = os.path.join(dir_, subfile)
            output_filename = '{:s}.gz'.format(
                os.path.join(
                    output_dir, os.path.relpath(input_filename, input_dir)))
            builder.build_file(
                output_filename, 'gzip_file', _gzip_file, input_filename)
