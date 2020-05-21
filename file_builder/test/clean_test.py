import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class CleanTest(FileBuilderTest):
    """Tests ``FileBuilder.clean.``"""

    def _build_file(self, builder, filename):
        """Build file function for ``test_clean`` that doesn't raise."""
        self._write(filename, 'text')

    def _build_file_error(self, builder, filename):
        """Build file function for ``test_clean`` that raises an exception."""
        self._write(filename, 'text')
        raise RuntimeError()

    def _build(self, builder):
        """Build function for ``test_clean``."""
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
                'build_file_error', self._build_file_error)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'build_file', self._build_file)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
                'build_file_error', self._build_file_error)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir4', 'Output.txt'),
            'build_file_dont_create', self._build_file)

    def test_clean(self):
        """Test ``FileBuilder.clean``."""
        FileBuilder.build(self._cache_filename, 'clean_test', self._build)
        FileBuilder.clean(self._cache_filename, 'clean_test')

        self.assertEqual([], os.listdir(self._temp_dir))

        os.mkdir(os.path.join(self._temp_dir, 'Dir1'))
        FileBuilder.build(self._cache_filename, 'clean_test', self._build)
        FileBuilder.clean(self._cache_filename, None)

        self.assertEqual(['Dir1'], os.listdir(self._temp_dir))
        self.assertEqual([], os.listdir(os.path.join(self._temp_dir, 'Dir1')))

        self._clean_temp_dir()
        os.makedirs(os.path.join(self._temp_dir, 'Dir3', 'Subdir'))
        self._write(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'File.txt'),
            'external')
        FileBuilder.build(self._cache_filename, 'clean_test', self._build)
        FileBuilder.clean(self._cache_filename, 'clean_test')

        self.assertEqual(['Dir3'], os.listdir(self._temp_dir))
        self.assertEqual(
            ['Subdir'], os.listdir(os.path.join(self._temp_dir, 'Dir3')))
        self.assertEqual(
            ['File.txt'],
            os.listdir(os.path.join(self._temp_dir, 'Dir3', 'Subdir')))
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'File.txt'),
            'external')

        self._clean_temp_dir()
        FileBuilder.build(self._cache_filename, 'clean_test', self._build)
        os.makedirs(os.path.join(self._temp_dir, 'Dir1', 'Subdir'))
        self._write(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'external')
        self._write(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'external')
        os.makedirs(os.path.join(self._temp_dir, 'Dir3', 'Subdir'))
        self._write(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
            'external')
        FileBuilder.clean(self._cache_filename, 'clean_test')

        self.assertEqual(
            set(['Dir1', 'Dir3']), set(os.listdir(self._temp_dir)))
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'external')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
            'external')
