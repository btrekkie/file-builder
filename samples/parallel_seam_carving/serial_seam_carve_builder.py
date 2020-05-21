import os

from file_builder import FileBuilder
from PIL import Image

from .seam_carver import SeamCarver


class SerialSeamCarveBuilder:
    """Performs seam carving on the images in an input directory in serial.

    This provides a point of comparison with
    ``ParallelSeamCarveBuilder``. See ``build``.
    """

    @staticmethod
    def build(input_dir, output_dir, cache_filename):
        """Do seam carving on images in ``input_dir`` and its subdirectories.

        For each image file in the input directory, this creates a
        smaller image file in the output directory with the same name.
        It creates a directory structure in the output directory that
        matches the directory structure in the input directory.

        Arguments:
            input_dir (str): The input directory.
            output_dir (str): The output directory.
            cache_filename (str): The file used to store cached results.
        """
        FileBuilder.build(
            cache_filename, 'seam_carve_dir_sample',
            SerialSeamCarveBuilder._build_dir, input_dir, output_dir)

    @staticmethod
    def _build_file(builder, output_filename, input_filename):
        """Perform seam carving on ``input_filename``.

        This may also scale the image. Store the results in
        ``output_filename``.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            output_filename (str): The output filename.
            input_filename (str): The input filename.
        """
        builder.declare_read(input_filename)
        input_image = Image.open(input_filename)
        input_image.thumbnail((400, 400))
        output_image = SeamCarver().carve(
            input_image, max(1, input_image.width // 2))
        output_image.save(output_filename)

    @staticmethod
    def _image_files(builder, dir_):
        """Return a list of the image files in the specified directory.

        This includes subdirectories.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            dir_ (str): The directory.

        Returns:
            list<str>: The files.
        """
        image_files = []
        for subdir, subdirs, subfiles in builder.walk(dir_):
            for subfile in subfiles:
                if subfile.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(subdir, subfile))
        return image_files

    @staticmethod
    def _build_dir(builder, input_dir, output_dir):
        """Do seam carving on images in ``input_dir`` and its subdirectories.

        For each image file in the input directory, this creates a
        smaller image file in the output directory with the same name.
        It creates a directory structure in the output directory that
        matches the directory structure in the input directory.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            input_dir (str): The input directory.
            output_dir (str): The output directory.
        """
        input_filenames = SerialSeamCarveBuilder._image_files(
            builder, input_dir)
        for input_filename in input_filenames:
            output_filename = os.path.join(
                output_dir, os.path.relpath(input_filename, input_dir))
            builder.build_file(
                output_filename, 'seam_carve_file',
                SerialSeamCarveBuilder._build_file, input_filename)
