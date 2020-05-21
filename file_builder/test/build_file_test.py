import functools
import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class BuildFileTest(FileBuilderTest):
    """Tests build file operations."""

    def _atomicity_build_file_inner(self, builder, filename):
        """Nested build file function for ``test_atomicity``."""
        dir_ = os.path.dirname(filename)
        self.assertTrue(builder.exists(dir_))
        self.assertTrue(builder.is_dir(dir_))
        self.assertFalse(builder.is_file(dir_))

        self._write(filename, 'old text')
        self.assertFalse(builder.exists(filename))
        self.assertFalse(builder.is_file(filename))

        outer_filename = os.path.join(self._temp_dir, 'Dir1', 'Output1.txt')
        self.assertFalse(builder.exists(outer_filename))
        self.assertFalse(builder.is_file(outer_filename))

        outer_dir = os.path.join(self._temp_dir, 'Dir1')
        self.assertTrue(builder.exists(outer_dir))
        self.assertTrue(builder.is_dir(outer_dir))
        self.assertFalse(builder.is_file(outer_dir))
        self._write(filename, 'text')

    def _atomicity_build_file_outer(
            self, should_files_exist, builder, filename):
        """Outer build file function for ``test_atomicity``."""
        dir_ = os.path.dirname(filename)
        self.assertTrue(builder.exists(dir_))
        self.assertTrue(builder.is_dir(dir_))
        self.assertFalse(builder.is_file(dir_))

        self._write(filename, 'text')
        self.assertFalse(builder.exists(filename))
        self.assertFalse(builder.is_file(filename))
        with self.assertRaises(FileNotFoundError):
            builder.read_text(filename)
        with self.assertRaises(FileNotFoundError):
            builder.read_binary(filename)
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(filename)

        inner_filename = os.path.join(self._temp_dir, 'Dir2', 'Output2.txt')
        inner_dir = os.path.join(self._temp_dir, 'Dir2')
        self.assertEqual(should_files_exist, builder.exists(inner_filename))
        self.assertEqual(should_files_exist, builder.exists(inner_dir))
        builder.build_file(
            inner_filename, 'build_file_inner',
            self._atomicity_build_file_inner)

        self.assertFalse(builder.exists(filename))
        self.assertFalse(builder.is_file(filename))
        self.assertTrue(builder.exists(inner_filename))
        self.assertTrue(builder.is_file(inner_filename))
        self.assertTrue(builder.exists(inner_dir))
        self.assertTrue(builder.is_dir(inner_dir))
        self.assertFalse(builder.is_file(inner_dir))

    def _atomicity_build_file(self, builder, filename):
        """Non-nesting build file function for ``test_atomicity``."""
        dir_ = os.path.dirname(filename)
        self.assertTrue(builder.exists(dir_))
        self.assertTrue(builder.is_dir(dir_))
        self.assertFalse(builder.is_file(dir_))

        self._write(filename, 'old text')
        self.assertFalse(builder.exists(filename))
        self.assertFalse(builder.is_file(filename))

        filename1 = os.path.join(self._temp_dir, 'Dir1', 'Output1.txt')
        filename2 = os.path.join(self._temp_dir, 'Dir2', 'Output2.txt')
        dir1 = os.path.join(self._temp_dir, 'Dir1')
        dir2 = os.path.join(self._temp_dir, 'Dir2')
        self.assertTrue(builder.exists(filename1))
        self.assertTrue(builder.is_file(filename1))
        self.assertTrue(builder.exists(filename2))
        self.assertTrue(builder.is_file(filename2))
        self.assertTrue(builder.exists(dir1))
        self.assertTrue(builder.is_dir(dir1))
        self.assertFalse(builder.is_file(dir1))
        self.assertTrue(builder.exists(dir2))
        self.assertTrue(builder.is_dir(dir2))
        self.assertFalse(builder.is_file(dir2))
        self._write(filename, 'text')

    def _atomicity_build(self, should_files_exist, builder):
        """Build function for ``test_atomicity``."""
        filename1 = os.path.join(self._temp_dir, 'Dir1', 'Output1.txt')
        filename2 = os.path.join(self._temp_dir, 'Dir2', 'Output2.txt')
        self.assertEqual(should_files_exist, builder.exists(filename1))
        self.assertEqual(should_files_exist, builder.is_file(filename1))
        if not should_files_exist:
            with self.assertRaises(FileNotFoundError):
                builder.read_text(filename1)
        self.assertEqual(should_files_exist, builder.exists(filename2))
        builder.build_file(
            filename1, 'build_file_outer',
            functools.partial(
                self._atomicity_build_file_outer, should_files_exist))

        self.assertTrue(builder.exists(filename1))
        self.assertTrue(builder.is_file(filename1))
        builder.declare_read(filename1)
        with builder.read_text(filename2):
            pass

        filename3 = os.path.join(self._temp_dir, 'Dir3', 'Output3.txt')
        dir3 = os.path.join(self._temp_dir, 'Dir3')
        self.assertFalse(builder.exists(filename3))
        self.assertFalse(builder.is_file(filename3))
        self.assertFalse(builder.exists(dir3))
        self.assertFalse(builder.is_dir(dir3))
        builder.build_file(filename3, 'build_file', self._atomicity_build_file)

        self.assertTrue(builder.exists(filename3))
        self.assertTrue(builder.is_file(filename3))
        with builder.read_binary(filename3):
            pass
        self.assertTrue(builder.exists(dir3))
        self.assertTrue(builder.is_dir(dir3))
        self.assertFalse(builder.is_file(dir3))

    def test_atomicity(self):
        """Test that the build file operation is atomic.

        That is, in the virtual state of the file system, the output
        file shouldn't be created until the build file function returns,
        at which point it receives its final contents.
        """
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._atomicity_build, False))

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output2.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Output3.txt'), 'text')

        self._clean_temp_dir()
        os.mkdir(os.path.join(self._temp_dir, 'Dir1'))
        self._write(
            os.path.join(self._temp_dir, 'Dir1', 'Output1.txt'), 'wrong text')
        os.mkdir(os.path.join(self._temp_dir, 'Dir2'))
        self._write(
            os.path.join(self._temp_dir, 'Dir2', 'Output2.txt'),
            'also wrong text')
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._atomicity_build, True))

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output2.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Output3.txt'), 'text')

    def _file_not_created_build_file(self, builder, filename):
        """Build file function for ``test_file_not_created``."""
        self.assertTrue(builder.is_dir(os.path.join(self._temp_dir, 'Foo')))
        self.assertTrue(
            builder.is_dir(os.path.join(self._temp_dir, 'Foo', 'Bar')))

    def _file_not_created_build(self, builder, does_dir_exist):
        """Build function for ``test_file_not_created``."""
        filename = os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt')
        with self.assertRaises(Exception):
            builder.build_file(
                filename, 'build_file', self._file_not_created_build_file)

        self.assertEqual(
            does_dir_exist,
            builder.is_dir(os.path.join(self._temp_dir, 'Foo')))
        self.assertEqual(
            does_dir_exist,
            builder.exists(os.path.join(self._temp_dir, 'Foo', 'Bar')))
        self.assertFalse(builder.exists(filename))
        self.assertFalse(builder.is_file(filename))
        with self.assertRaises(FileNotFoundError):
            builder.read_text(filename)

    def test_file_not_created(self):
        """Test where the build file function doesn't create the output file.
        """
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            self._file_not_created_build, False)

        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Foo')))

        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            self._file_not_created_build, False)

        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Foo')))

        os.makedirs(os.path.join(self._temp_dir, 'Foo', 'Bar'))
        self._write(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt'), 'text')
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            self._file_not_created_build, True)

        self.assertTrue(
            os.path.isdir(os.path.join(self._temp_dir, 'Foo', 'Bar')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt')))

    def _error_build_file(self, builder, filename):
        """Build file function for ``test_error``."""
        self.assertFalse(builder.exists(filename))
        raise RuntimeError()

    def _error_build(self, should_foo_exist, should_bar_exist, builder):
        """Build function for ``test_error``."""
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt'),
                'build_file', self._error_build_file)
        self.assertEqual(
            should_foo_exist,
            builder.is_dir(os.path.join(self._temp_dir, 'Foo')))
        self.assertEqual(
            should_bar_exist,
            builder.exists(os.path.join(self._temp_dir, 'Foo', 'Bar')))
        self.assertFalse(
            builder.exists(
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt')))

    def test_error(self):
        """Test the case where the build file function raises an exception."""
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._error_build, False, False))
        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Foo')))

        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._error_build, False, False))
        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Foo')))

        os.mkdir(os.path.join(self._temp_dir, 'Foo'))
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._error_build, True, False))
        self.assertTrue(os.path.isdir(os.path.join(self._temp_dir, 'Foo')))
        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'Foo', 'Bar')))

        os.mkdir(os.path.join(self._temp_dir, 'Foo', 'Bar'))
        self._write(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt'), 'text')
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            functools.partial(self._error_build, True, True))
        self.assertTrue(
            os.path.isdir(os.path.join(self._temp_dir, 'Foo', 'Bar')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Output.txt')))

    def _rollback_build_file(self, builder, filename):
        """Build file function for ``test_rollback*`` that creates the file."""
        self._write(filename, 'Something')

    def _rollback_build_file_dont_create(self, builder, filename):
        """Build file function that doesn't create the file."""
        pass

    def _rollback_build_file_error(self, builder, filename):
        """Build file function for ``test_rollback*`` that raises an exception.
        """
        raise RuntimeError()

    def _rollback_build_success(self, builder):
        """Build function for ``test_rollback_after_success``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'build_file', self._rollback_build_file)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
                'build_file_dont_create',
                self._rollback_build_file_dont_create)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
                'build_file_error', self._rollback_build_file_error)

    def _rollback_build(self, builder):
        """Build function for ``test_rollback``."""
        self._rollback_build_success(builder)
        raise RuntimeError()

    def test_rollback(self):
        """Test rolling back a build due to an exception in the build function.
        """
        dirs = [
            os.path.join(self._temp_dir, 'Dir1'),
            os.path.join(self._temp_dir, 'Dir2'),
            os.path.join(self._temp_dir, 'Dir3')]
        with self.assertRaises(RuntimeError):
            FileBuilder.build(
                self._cache_filename, 'build_file_test', self._rollback_build)

        for dir_ in dirs:
            self.assertFalse(os.path.exists(dir_))

        for dir_ in dirs:
            os.mkdir(dir_)
        with self.assertRaises(RuntimeError):
            FileBuilder.build(
                self._cache_filename, 'build_file_test', self._rollback_build)

        for dir_ in dirs:
            self.assertTrue(os.path.isdir(dir_))
            self.assertFalse(os.path.exists(os.path.join(dir_, 'Subdir')))

        for dir_ in dirs:
            os.mkdir(os.path.join(dir_, 'Subdir'))
            self._write(os.path.join(dir_, 'Subdir', 'Output.txt'), 'external')
        with self.assertRaises(RuntimeError):
            FileBuilder.build(
                self._cache_filename, 'build_file_test', self._rollback_build)

        for dir_ in dirs:
            self._check_contents(
                os.path.join(dir_, 'Subdir', 'Output.txt'), 'external')

    def test_rollback_after_success(self):
        """Test rolling back a build after a successful build.

        Test rolling back a build due to an exception in the build
        function after a previous build completed successfully.
        """
        dirs = [
            os.path.join(self._temp_dir, 'Dir1'),
            os.path.join(self._temp_dir, 'Dir2'),
            os.path.join(self._temp_dir, 'Dir3')]
        FileBuilder.build(
            self._cache_filename, 'build_file_test',
            self._rollback_build_success)

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'Something')
        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Dir2')))
        self.assertFalse(os.path.exists(os.path.join(self._temp_dir, 'Dir3')))

        os.makedirs(os.path.join(self._temp_dir, 'Dir2', 'Subdir'))
        os.makedirs(os.path.join(self._temp_dir, 'Dir3', 'Subdir'))
        for dir_ in dirs:
            self._write(os.path.join(dir_, 'Subdir', 'Output.txt'), 'external')
        with self.assertRaises(RuntimeError):
            FileBuilder.build(
                self._cache_filename, 'build_file_test', self._rollback_build)

        for dir_ in dirs:
            self._check_contents(
                os.path.join(dir_, 'Subdir', 'Output.txt'), 'external')

    def _clean_build_file_inner(self, builder, filename):
        """Nested build file function for ``test_clean``."""
        self._write(filename, 'text')

    def _clean_build_file_outer(self, builder, filename, inner_filename):
        """Outer build file function for ``test_clean``."""
        self._write(filename, 'outer')
        builder.build_file(
            inner_filename, 'build_file_inner', self._clean_build_file_inner)

    def _clean_build_file_dont_create(self, builder, filename):
        """Build file function for ``test_clean`` that doesn't create the file.
        """
        pass

    def _clean_build_file_error(self, builder, filename):
        """Build file function for ``test_clean`` that raises an exception."""
        raise RuntimeError()

    def _clean_build(self, builder):
        """Build function for ``test_clean``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'build_file_inner', self._clean_build_file_inner)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'Output.txt'),
                'build_file_dont_create', self._clean_build_file_dont_create)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'Output.txt'),
            'build_file_outer', self._clean_build_file_outer,
            os.path.join(self._temp_dir, 'Dir4', 'Subdir', 'Output.txt'))
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir5', 'Subdir', 'Output.txt'),
                'build_file_error', self._clean_build_file_error)

    def test_clean(self):
        """Test ``FileBuilder.clean``."""
        dirs = [
            os.path.join(self._temp_dir, 'Dir1'),
            os.path.join(self._temp_dir, 'Dir2'),
            os.path.join(self._temp_dir, 'Dir3'),
            os.path.join(self._temp_dir, 'Dir4'),
            os.path.join(self._temp_dir, 'Dir5')]
        FileBuilder.build(
            self._cache_filename, 'build_file_test', self._clean_build)
        FileBuilder.clean(self._cache_filename, 'build_file_test')

        self.assertEqual([], os.listdir(self._temp_dir))

        for dir_ in dirs:
            os.mkdir(dir_)
        FileBuilder.build(
            self._cache_filename, 'build_file_test', self._clean_build)
        FileBuilder.clean(self._cache_filename, 'build_file_test')

        self.assertFalse(os.path.exists(self._cache_filename))
        for dir_ in dirs:
            self.assertTrue(os.path.isdir(dir_))
            self.assertFalse(os.path.exists(os.path.join(dir_, 'Subdir')))

        for dir_ in dirs:
            os.mkdir(os.path.join(dir_, 'Subdir'))
            self._write(os.path.join(dir_, 'Subdir', 'Output.txt'), 'external')
        FileBuilder.build(
            self._cache_filename, 'build_file_test', self._clean_build)
        FileBuilder.clean(self._cache_filename, 'build_file_test')

        self.assertFalse(os.path.exists(self._cache_filename))
        for dir_ in dirs:
            self.assertTrue(os.path.isdir(os.path.join(dir_, 'Subdir')))
            self.assertFalse(
                os.path.exists(os.path.join(dir_, 'Subdir', 'Output.txt')))

    def _cache_file_conflict_build_file(self, builder, filename):
        """Build file function for ``test_cache_file_conflict``."""
        self._write(filename, 'text')

    def _cache_file_conflict_build(self, builder, filename):
        """Build function for ``test_cache_file_conflict``."""
        builder.build_file(
            filename, 'build_file', self._cache_file_conflict_build_file)

    def test_cache_file_conflict(self):
        """Test conflicts involving the cache file.

        Test cases where the cache filename is a directory or where we
        try to create a directory with the same filename as the cache
        file.
        """
        with self.assertRaises(NotADirectoryError):
            FileBuilder.build(
                os.path.join(self._temp_dir, 'Foo', 'Bar'), 'build_file_test',
                self._cache_file_conflict_build,
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz', 'File.txt'))
        self.assertEqual([], os.listdir(self._temp_dir))

        os.makedirs(os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz'))
        with self.assertRaises(IsADirectoryError):
            FileBuilder.build(
                os.path.join(self._temp_dir, 'Foo', 'Bar'), 'build_file_test',
                self._cache_file_conflict_build,
                os.path.join(self._temp_dir, 'File.txt'))

        self.assertEqual(['Foo'], os.listdir(self._temp_dir))
        self.assertTrue(
            os.path.isdir(os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz')))

        self._clean_temp_dir()
        FileBuilder.build(
            os.path.join(self._temp_dir, 'Foo', 'Bar'), 'build_file_test',
            self._cache_file_conflict_build,
            os.path.join(self._temp_dir, 'File.txt'))
        with self.assertRaises(NotADirectoryError):
            FileBuilder.build(
                os.path.join(self._temp_dir, 'Foo', 'Bar'), 'build_file_test',
                self._cache_file_conflict_build,
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz', 'File.txt'))

        self.assertEqual(
            set(['Foo', 'File.txt']), set(os.listdir(self._temp_dir)))
        self.assertEqual(
            ['Bar'], os.listdir(os.path.join(self._temp_dir, 'Foo')))
        self.assertTrue(
            os.path.isfile(os.path.join(self._temp_dir, 'Foo', 'Bar')))
        self._check_contents(os.path.join(self._temp_dir, 'File.txt'), 'text')
