import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class SetupFailedTest(FileBuilderTest):
    """Tests cases where setup alternately fails and succeeds.

    Tests cases where setup for a build file or subbuild operation
    succeeds in one build and fails in the next or vice versa. This test
    case ensures that we don't reuse cached results when this happens.
    "Setup" refers to certain validations and file system operations
    that occur before calling the function passed to ``build_file*`` or
    ``subbuild``.
    """

    def _build_file_twice_build_file(self, builder, filename):
        """Build file function for ``test_build_file_twice``."""
        self._write(filename, 'text')

    def _build_file_twice_subbuild(self, builder):
        """Subbuild function for ``test_build_file_twice``."""
        try:
            builder.build_file(
                os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
                self._build_file_twice_build_file)
            return True
        except Exception:
            return False

    def _build_file_twice_build1(self, builder):
        """The first build function for ``test_build_file_twice``."""
        return builder.subbuild('subbuild', self._build_file_twice_subbuild)

    def _build_file_twice_build2(self, builder):
        """The second build function for ``test_build_file_twice``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
            self._build_file_twice_build_file)
        return builder.subbuild('subbuild', self._build_file_twice_subbuild)

    def test_build_file_twice(self):
        """Test cases where we attempt to build a file twice in one build."""
        result1 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._build_file_twice_build1)
        self.assertTrue(result1)

        result2 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._build_file_twice_build2)
        self.assertFalse(result2)

        result3 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._build_file_twice_build1)
        self.assertTrue(result3)

    def _build_cache_file_build_file(self, builder, filename):
        """Build file function for ``test_build_cache_file``."""
        self._write(filename, 'text')

    def _build_cache_file_subbuild(self, builder):
        """Subbuild function for ``test_build_cache_file``."""
        try:
            builder.build_file(
                os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
                self._build_file_twice_build_file)
            return True
        except Exception:
            return False

    def _build_cache_file_build(self, builder):
        """Build function for ``test_build_cache_file``."""
        return builder.subbuild('subbuild', self._build_cache_file_subbuild)

    def test_build_cache_file(self):
        """Test cases where we attempt to build the cache file."""
        result1 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._build_cache_file_build)

        self.assertTrue(result1)

        os.remove(os.path.join(self._temp_dir, 'Output.txt'))
        os.rename(
            self._cache_filename, os.path.join(self._temp_dir, 'Output.txt'))
        result2 = FileBuilder.build(
            os.path.join(self._temp_dir, 'Output.txt'), 'setup_failed_test',
            self._build_cache_file_build)

        self.assertFalse(result2)
        self.assertTrue(
            os.path.isfile(os.path.join(self._temp_dir, 'Output.txt')))

        os.rename(
            os.path.join(self._temp_dir, 'Output.txt'), self._cache_filename)
        result3 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._build_cache_file_build)

        self.assertTrue(result3)

    def _cant_make_dir_build_file(self, builder, filename):
        """Build file function for ``test_cant_make_dir``."""
        self._write(filename, 'text')

    def _cant_make_dir_subbuild(self, builder):
        """Subbuild function for ``test_cant_make_dir``."""
        try:
            builder.build_file(
                os.path.join(self._temp_dir, 'Foo', 'Bar'), 'build_file',
                self._cant_make_dir_build_file)
            return True
        except Exception:
            return False

    def _cant_make_dir_build1(self, builder):
        """The first build function for ``test_cant_make_dir``."""
        return builder.subbuild('subbuild', self._cant_make_dir_subbuild)

    def _cant_make_dir_build2(self, builder):
        """The second build function for ``test_cant_make_dir``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz.txt'),
            'build_file', self._cant_make_dir_build_file)
        return builder.subbuild('subbuild', self._cant_make_dir_subbuild)

    def test_cant_make_dir(self):
        """Test where we can't create the build file's parent directories."""
        result1 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._cant_make_dir_build1)
        self.assertTrue(result1)

        result2 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._cant_make_dir_build2)
        self.assertFalse(result2)

        result3 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._cant_make_dir_build1)
        self.assertTrue(result3)

    def _subbuild_twice_subbuild1(self, builder):
        """The first subbuild function for ``test_subbuild_twice``."""
        pass

    def _subbuild_twice_subbuild2(self, builder, *args):
        """The second subbuild function for ``test_subbuild_twice``."""
        try:
            builder.subbuild('subbuild1', self._subbuild_twice_subbuild1)
            return True
        except Exception:
            return False

    def _subbuild_twice_build1(self, builder):
        """The first build function for ``test_subbuild_twice``."""
        return builder.subbuild(
            'subbuild2', self._subbuild_twice_subbuild2, True)

    def _subbuild_twice_build2(self, builder):
        """The second build function for ``test_subbuild_twice``."""
        builder.subbuild('subbuild2', self._subbuild_twice_subbuild2, False)
        return builder.subbuild(
            'subbuild2', self._subbuild_twice_subbuild2, True)

    def test_subbuild_twice(self):
        """Test cases where we attempt to perform the same subbuild twice.

        Test cases where we attempt to perform the same subbuild twice
        in one build.
        """
        result1 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._subbuild_twice_build1)
        self.assertTrue(result1)

        result2 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._subbuild_twice_build2)
        self.assertFalse(result2)

        result3 = FileBuilder.build(
            self._cache_filename, 'setup_failed_test',
            self._subbuild_twice_build1)
        self.assertTrue(result3)
