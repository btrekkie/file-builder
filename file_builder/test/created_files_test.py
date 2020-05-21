import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class CreatedFilesTest(FileBuilderTest):
    """Tests ``FileBuilder``'s caching behavior when files are created.

    Tests that ``FileBuilder`` is able to reuse a cache entry when some
    of the operations' results depend on files created earlier in that
    cache entry.
    """

    def _build_file(self, builder, filename):
        """Build file function for ``CreatedFilesTest``."""
        self._write(filename, 'text')

    def _subbuild1(self, builder):
        """The first subbuild function for ``CreatedFilesTest``."""
        self.assertFalse(
            builder.is_dir(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertFalse(
            builder.is_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))
        builder.exists(os.path.join(self._temp_dir, 'Dir2'))
        builder.walk(os.path.join(self._temp_dir, 'Dir2'))

        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'build_file', self._build_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
            'build_file', self._build_file)

        self.assertTrue(
            builder.is_dir(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertTrue(
            builder.is_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))
        self.assertTrue(builder.exists(os.path.join(self._temp_dir, 'Dir2')))
        self.assertEqual(
            ['Output.txt'],
            builder.list_dir(os.path.join(self._temp_dir, 'Dir2', 'Subdir')))
        builder.walk(os.path.join(self._temp_dir, 'Dir2'))
        builder.declare_read(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'))
        return self._build_number

    def _subbuild2(self, builder):
        """The second subbuild function for ``CreatedFilesTest``."""
        self.assertTrue(
            builder.is_file(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))
        with self.assertRaises(IsADirectoryError):
            builder.declare_read(os.path.join(self._temp_dir, 'Dir2'))
        self.assertTrue(
            builder.is_file(os.path.join(self._temp_dir, 'Dir1', 'File1.txt')))
        self.assertTrue(
            builder.is_file(os.path.join(self._temp_dir, 'Dir1', 'File3.txt')))
        self.assertFalse(
            builder.exists(os.path.join(self._temp_dir, 'Dir2', 'File4.txt')))

    def _subbuild3(self, builder):
        """The third subbuild function for ``CreatedFilesTest``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'File1.txt'), 'build_file',
            self._build_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'File2.txt'), 'build_file',
            self._build_file)
        builder.build_file(
            os.path.join(
                self._temp_dir, 'Dir1', 'Subdir2', 'Subdir3', 'Output.txt'),
            'build_file', self._build_file)

        result = builder.subbuild('subbuild1', self._subbuild1)

        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'File3.txt'), 'build_file',
            self._build_file)
        builder.subbuild('subbuild2', self._subbuild2)

        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'File4.txt'), 'build_file',
            self._build_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'File5.txt'),
            'build_file', self._build_file)
        self.assertTrue(
            builder.is_dir(os.path.join(self._temp_dir, 'Dir2', 'Subdir')))
        self.assertTrue(
            builder.is_file(os.path.join(self._temp_dir, 'Dir1', 'File1.txt')))
        self.assertTrue(
            builder.exists(os.path.join(self._temp_dir, 'Dir1', 'File3.txt')))
        builder.walk(os.path.join(self._temp_dir))
        return result

    def _build1(self, builder):
        """The first build function for ``CreatedFilesTest``."""
        return builder.subbuild('subbuild1', self._subbuild1)

    def _build2(self, builder):
        """The second build function for ``CreatedFilesTest``."""
        return builder.subbuild('subbuild3', self._subbuild3)

    def test_created_files(self):
        """Test ``FileBuilder``'s caching behavior when files are created.

        Test that ``FileBuilder`` is able to reuse a cache entry when
        some of the operations' results depend on files created earlier
        in that cache entry.
        """
        self._build_number = 1
        result1 = FileBuilder.build(
            self._cache_filename, 'created_files_test', self._build1)

        self.assertEqual(1, result1)

        self._build_number = 2
        result2 = FileBuilder.build(
            self._cache_filename, 'created_files_test', self._build1)

        self.assertEqual(1, result2)

        self._build_number = 3
        result3 = FileBuilder.build(
            self._cache_filename, 'created_files_test', self._build2)

        self.assertEqual(1, result3)

        self._build_number = 4
        result4 = FileBuilder.build(
            self._cache_filename, 'created_files_test', self._build2)

        self.assertEqual(1, result4)

        self._build_number = 5
        self._write(
            os.path.join(self._temp_dir, 'Dir2', 'CacheBuster.txt'), 'text')
        result5 = FileBuilder.build(
            self._cache_filename, 'created_files_test', self._build2)

        self.assertEqual(5, result5)
