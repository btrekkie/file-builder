import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class BuildDirsTest(FileBuilderTest):
    """Tests correct determination of whether build directories are present.

    Tests correct determination of whether the parent directories of
    output files are present.
    """

    def _build_dirs_build_file1(self, builder, filename):
        """The build file function for the first build function."""
        self._write(filename, 'text')

    def _build_dirs_build1(self, builder):
        """The first build function."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'build_file1', self._build_dirs_build_file1)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'build_file1', self._build_dirs_build_file1)

    def _build_dirs_build_file2(self, builder, filename):
        """The first build file function for the second build function."""
        self.assertTrue(builder.exists(os.path.join(self._temp_dir, 'Dir1')))
        raise RuntimeError()

    def _build_dirs_build_file3(self, builder, filename):
        """The second build file function for the second build function."""
        self.assertTrue(builder.is_dir(os.path.join(self._temp_dir, 'Dir2')))
        self._write(filename, 'text')

    def _build_dirs_build_file4(self, builder, filename):
        """The third build file function for the second build function."""
        self._write(filename, 'text')

    def _build_dirs_build_file5(self, builder, filename):
        """The fourth build file function for the second build function."""
        raise RuntimeError()

    def _build_dirs_build2(self, builder):
        """The second build function."""
        self.assertFalse(builder.exists(os.path.join(self._temp_dir, 'Dir1')))
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
                'build_file2', self._build_dirs_build_file2)
        self.assertFalse(builder.exists(os.path.join(self._temp_dir, 'Dir1')))
        self.assertFalse(
            builder.exists(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertFalse(
            builder.exists(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))

        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output2.txt'),
                'build_file2', self._build_dirs_build_file2)
        self.assertFalse(builder.exists(os.path.join(self._temp_dir, 'Dir1')))
        self.assertFalse(
            builder.exists(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertFalse(
            builder.exists(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))

        builder.build_file(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
            'build_file4', self._build_dirs_build_file4)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output2.txt'),
                'build_file5', self._build_dirs_build_file5)
        self.assertTrue(builder.is_dir(os.path.join(self._temp_dir, 'Dir3')))
        self.assertTrue(
            builder.is_dir(os.path.join(self._temp_dir, 'Dir3', 'Subdir')))

        self.assertFalse(builder.exists(os.path.join(self._temp_dir, 'Dir2')))
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'build_file3', self._build_dirs_build_file3)
        self.assertTrue(builder.is_dir(os.path.join(self._temp_dir, 'Dir2')))
        self.assertTrue(builder.is_dir(os.path.join(self._temp_dir, 'Dir3')))
        self.assertTrue(
            builder.is_dir(os.path.join(self._temp_dir, 'Dir3', 'Subdir')))

    def _build_dirs_build3(self, builder):
        """The third build function."""
        self.assertFalse(
            builder.exists(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output2.txt')))
        self.assertTrue(builder.exists(os.path.join(self._temp_dir, 'Dir2')))
        self.assertTrue(
            builder.exists(os.path.join(self._temp_dir, 'Dir2', 'Subdir')))
        self.assertTrue(builder.exists(os.path.join(self._temp_dir, 'Dir3')))
        self.assertTrue(
            builder.exists(os.path.join(self._temp_dir, 'Dir3', 'Subdir')))
        builder.declare_read(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output2.txt'))
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output2.txt'),
            'text')

    def test_build_dirs(self):
        """Test correct determination of whether build directories are present.
        """
        FileBuilder.build(
            self._cache_filename, 'build_dirs_test', self._build_dirs_build1)
        FileBuilder.build(
            self._cache_filename, 'build_dirs_test', self._build_dirs_build2)

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'text')
        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Dir1')))

        self._write(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output2.txt'),
            'text')
        self._write(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output2.txt'),
            'text')
        FileBuilder.build(
            self._cache_filename, 'build_dirs_test', self._build_dirs_build3)

        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Dir1')))
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output2.txt'),
            'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output2.txt'),
            'text')
