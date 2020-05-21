`samples/gzip` is a sample project for the "file-builder" library. It
illustrates the `FileBuilder.build_file` method.

This provides a `gzip_dir` function, which compresses all of the files in a
given input directory (including subdirectories) using gzip. For each file in
the input directory, `gzip_dir` creates a compressed file in the output
directory with the same name, but with ".gz" appended to it. It creates a
directory structure in the output directory that matches the directory structure
in the input directory.
