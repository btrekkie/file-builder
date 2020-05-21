import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class SwapDirsAndFilesTest(FileBuilderTest):
    """Tests ``FileBuilder`` when files and directories are swapped.

    Tests ``FileBuilder`` when a filename was a file and became a
    directory or vice versa.
    """

    def _write_to_file(self, builder, filename):
        """Write the word "text" to the specified file."""
        self._write(filename, 'text')

    def _swap_build1(self, builder):
        """First build function for ``test_swap`` and ``test_swap_norm_case``.
        """
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo1'), 'build_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo2', 'Bar', 'Baz'), 'build_file',
            self._write_to_file)

    def _swap_build2(self, builder):
        """The second build function for ``test_swap``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'build_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo2'), 'build_file',
            self._write_to_file)

    def test_swap(self):
        """Test swapping files and directories between builds.

        Test ``FileBuilder`` where a filename that was a file in one
        build is a directory in the subsequent build and vice versa.
        """
        FileBuilder.build(self._cache_filename, 'swap_test', self._swap_build1)

        self._check_contents(os.path.join(self._temp_dir, 'Foo1'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Foo2', 'Bar', 'Baz'), 'text')

        FileBuilder.build(self._cache_filename, 'swap_test', self._swap_build2)

        self._check_contents(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'text')
        self._check_contents(os.path.join(self._temp_dir, 'Foo2'), 'text')

    def _write_and_raise(self, builder, filename):
        """Build file function for ``test_swap_error``."""
        self._write(filename, 'text')
        raise RuntimeError()

    def _swap_error_build(self, builder):
        """Build function for ``test_swap_error``."""
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo1'), 'build_file_raise',
                self._write_and_raise)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo2', 'Bar', 'Baz'),
                'build_file_raise', self._write_and_raise)
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'build_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo2'), 'build_file',
            self._write_to_file)

    def test_swap_error(self):
        """Test swapping files and directories when we catch exceptions.

        Test ``FileBuilder`` where a filename was a file during a
        ``build_file`` function that resulted in a caught exception and
        is a directory later in the build or vice versa.
        """
        FileBuilder.build(
            self._cache_filename, 'swap_test', self._swap_error_build)
        self._check_contents(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'text')
        self._check_contents(os.path.join(self._temp_dir, 'Foo2'), 'text')

    def _swap_build_norm_case(self, builder):
        """Build function for ``test_swap_norm_case``."""
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz')),
            'build_file', self._write_to_file)
        builder.build_file(
            os.path.normcase(os.path.join(self._temp_dir, 'Foo2')),
            'build_file', self._write_to_file)

    def test_swap_norm_case(self):
        """Test swapping files and directories between builds.

        Test ``FileBuilder`` where a filename that was a file in one
        build is a directory in the subsequent build and vice versa. The
        filenames are norm-cased in one of the builds but not the other.
        """
        FileBuilder.build(self._cache_filename, 'swap_test', self._swap_build1)

        self._check_contents(os.path.join(self._temp_dir, 'Foo1'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Foo2', 'Bar', 'Baz'), 'text')

        FileBuilder.build(
            self._cache_filename, 'swap_test', self._swap_build_norm_case)

        self._check_contents(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'text')
        self._check_contents(os.path.join(self._temp_dir, 'Foo2'), 'text')
        self.assertEqual(
            set([
                os.path.normcase('Foo1'), os.path.normcase('Foo2'),
                os.path.basename(self._cache_filename)]),
            set(os.listdir(self._temp_dir)))

    def _swap_error_norm_case_build(self, builder):
        """Build function for ``test_swap_error_norm_case``."""
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo1'), 'build_file_raise',
                self._write_and_raise)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo2', 'Bar', 'Baz'),
                'build_file_raise', self._write_and_raise)
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz')),
            'build_file', self._write_to_file)
        builder.build_file(
            os.path.normcase(os.path.join(self._temp_dir, 'Foo2')),
            'build_file', self._write_to_file)

    def test_swap_norm_case_error(self):
        """Test swapping files and directories when we catch exceptions.

        Test ``FileBuilder`` where a filename was a file during a
        ``build_file`` function that resulted in a caught exception and
        is a directory later in the build or vice versa. The filenames
        are norm-cased in one of the file builds but not the other.
        """
        FileBuilder.build(
            self._cache_filename, 'swap_test',
            self._swap_error_norm_case_build)

        self._check_contents(
            os.path.join(self._temp_dir, 'Foo1', 'Bar', 'Baz'), 'text')
        self._check_contents(os.path.join(self._temp_dir, 'Foo2'), 'text')
        self.assertEqual(
            set([
                os.path.normcase('Foo1'), os.path.normcase('Foo2'),
                os.path.basename(self._cache_filename)]),
            set(os.listdir(self._temp_dir)))
