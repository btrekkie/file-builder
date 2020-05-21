import functools
import os

from .. import FileBuilder
from .. import FileComparison
from .file_builder_test import FileBuilderTest


class CachingTest(FileBuilderTest):
    """Tests that ``FileBuilder`` reuses cached results when it should."""

    def setUp(self):
        super().setUp()
        self._build_number = 0

    def _caching_build_file(self, builder, filename, arg1, arg2):
        """Build file function for ``test_caching``."""
        self._write(filename, 'Build {:d}'.format(self._build_number))
        return self._build_number

    def _caching_subbuild(self, build_file_args, builder, arg1, arg2):
        """Subbuild function for ``test_caching``."""
        func_name, file_comparison_name, subarg1, subarg2 = build_file_args
        result = builder.build_file_with_comparison(
            os.path.join(self._temp_dir, 'Output.txt'),
            FileComparison[file_comparison_name], func_name,
            self._caching_build_file, subarg1, arg2=subarg2)
        return [self._build_number, result]

    def _caching_build_func(
            self, subbuild_args, build_file_args, builder, arg1, arg2):
        """Build function for ``test_caching``."""
        func_name, subarg1, subarg2 = subbuild_args
        result = builder.subbuild(
            func_name,
            functools.partial(self._caching_subbuild, build_file_args),
            subarg1, arg2=subarg2)
        return [self._build_number] + result

    def _caching_build(self, build_args, subbuild_args, build_file_args):
        """Execute the build operation for ``test_caching``."""
        self._build_number += 1
        arg1, arg2 = build_args
        return FileBuilder.build(
            self._cache_filename, 'caching_test',
            functools.partial(
                self._caching_build_func, subbuild_args, build_file_args),
            arg1, arg2=arg2)

    def test_caching(self):
        """Test that ``FileBuilder`` reuses cached results when it should."""
        filename = os.path.join(self._temp_dir, 'Output.txt')
        result1 = self._caching_build(
            (0, 0), ('subbuild', 0, 0),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([1, 1, 1], result1)
        self._check_contents(filename, 'Build 1')

        result2 = self._caching_build(
            (1, 0), ('subbuild', 0, 0),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([2, 1, 1], result2)
        self._check_contents(filename, 'Build 1')

        result3 = self._caching_build(
            (1, 1), ('subbuild', 0, 0),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([3, 1, 1], result3)
        self._check_contents(filename, 'Build 1')

        result4 = self._caching_build(
            (1, 1), ('subbuild2', 0, 0),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([4, 4, 1], result4)
        self._check_contents(filename, 'Build 1')

        result5 = self._caching_build(
            (1, 1), ('subbuild2', 1, 0),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([5, 5, 1], result5)
        self._check_contents(filename, 'Build 1')

        result6 = self._caching_build(
            (1, 1), ('subbuild2', 1, 1),
            ('build_file', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([6, 6, 1], result6)
        self._check_contents(filename, 'Build 1')

        result7 = self._caching_build(
            (1, 1), ('subbuild3', 1, 1),
            ('build_file2', FileComparison.METADATA.name, 0, 0))
        self.assertEqual([7, 7, 7], result7)
        self._check_contents(filename, 'Build 7')

        result8 = self._caching_build(
            (1, 1), ('subbuild4', 1, 1),
            ('build_file2', FileComparison.HASH.name, 0, 0))
        self.assertEqual([8, 8, 7], result8)
        self._check_contents(filename, 'Build 7')

        result9 = self._caching_build(
            (1, 1), ('subbuild5', 1, 1),
            ('build_file2', FileComparison.HASH.name, 1, 0))
        self.assertEqual([9, 9, 9], result9)
        self._check_contents(filename, 'Build 9')

        result10 = self._caching_build(
            (1, 1), ('subbuild6', 1, 1),
            ('build_file2', FileComparison.HASH.name, 1, 1))
        self.assertEqual([10, 10, 10], result10)
        self._check_contents(filename, 'Build 10')

        result11 = self._caching_build(
            (1, 1), ('subbuild7', 1, 1),
            ('build_file2', FileComparison.HASH.name, 1, 1))
        self.assertEqual([11, 11, 10], result11)
        self._check_contents(filename, 'Build 10')
