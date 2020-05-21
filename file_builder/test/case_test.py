import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class CaseTest(FileBuilderTest):
    """Tests filename casing (uppercase vs. lowercase).

    This test case is mostly only useful on Windows, because Windows
    filenames are case-insensitive.
    """

    def _build_file(self, builder, filename):
        """Build file function for ``CaseTest`` that doesn't raise."""
        self._write(filename, 'text')

    def _build_file_error(self, builder, filename):
        """Build file function for ``CaseTest`` that raises an exception."""
        self._write(filename, 'text')
        raise RuntimeError()

    def _build1(self, builder):
        """The first build function for ``CaseTest``."""
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir1', 'Output.txt')),
            'build_file', self._build_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir2', 'Output.txt'),
            'build_file', self._build_file)
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir3', 'Output.txt')),
            'build_file', self._build_file)

    def _build2(self, builder, preexisting=False):
        """The second build function for ``CaseTest``.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            preexisting (bool): Whether some of the files and
                directories that this build operates on already exist,
                though perhaps with a different case, per the
                implementation of ``test_preexisting``.
        """
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt'),
            'build_file', self._build_file)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.normcase(
                    os.path.join(
                        self._temp_dir, 'Dir1', 'Subdir', 'Output2.txt')),
                'build_file', self._build_file_error)

        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir1', 'Output2.txt'),
                'build_file', self._build_file_error)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir3', 'Output.txt'),
                'build_file', self._build_file_error)
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir1', 'Output.txt')),
            'build_file', self._build_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir2', 'Output.txt'),
            'build_file', self._build_file)

        builder.build_file(
            os.path.join(self._temp_dir, 'Dir3', 'Output.txt'), 'build_file',
            self._build_file)
        builder.build_file(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir3', 'Output2.txt')),
            'build_file', self._build_file)

        if preexisting:
            dir1_case = os.path.normcase('Dir1')
            dir2_case = 'Dir2'
            subdir2_case = os.path.normcase('Subdir2')
        else:
            dir1_case = 'Dir1'
            dir2_case = os.path.normcase('Dir2')
            subdir2_case = 'Subdir2'

        self.assertEqual(
            set([dir1_case, dir2_case, 'Dir3']),
            set(builder.list_dir(self._temp_dir)))
        self.assertEqual(
            ['Subdir'], builder.list_dir(os.path.join(self._temp_dir, 'Dir1')))
        self.assertEqual(
            set([os.path.normcase('Subdir1'), subdir2_case]),
            set(builder.list_dir(os.path.join(self._temp_dir, 'Dir2'))))
        self.assertEqual(
            [os.path.normcase('Output.txt')],
            builder.list_dir(os.path.join(self._temp_dir, 'Dir2', 'Subdir1')))
        self.assertEqual(
            set(['Output.txt', os.path.normcase('Output2.txt')]),
            set(builder.list_dir(os.path.join(self._temp_dir, 'Dir3'))))

        expected_walk = [
            (self._temp_dir, [dir1_case, dir2_case, 'Dir3'], []),
            (os.path.join(self._temp_dir, dir1_case), ['Subdir'], []),
            (
                os.path.join(self._temp_dir, dir1_case, 'Subdir'), [],
                ['Output.txt']),
            (
                os.path.join(self._temp_dir, dir2_case),
                [os.path.normcase('Subdir1'), subdir2_case], []),
            (
                os.path.join(
                    self._temp_dir, dir2_case, os.path.normcase('Subdir1')),
                [], [os.path.normcase('Output.txt')]),
            (
                os.path.join(self._temp_dir, dir2_case, subdir2_case), [],
                ['Output.txt']),
            (
                os.path.join(self._temp_dir, 'Dir3'), [],
                ['Output.txt', os.path.normcase('Output2.txt')]),
        ]

        normalized_walk = self._normalize_walk(builder.walk(self._temp_dir))
        normalized_expected_walk = self._normalize_walk(expected_walk)
        self.assertEqual(
            self._walk_map(normalized_expected_walk),
            self._walk_map(normalized_walk))

    def _check_build2(self):
        """Check the file system resulting after executing ``_build2``."""
        self.assertEqual(
            set([
                'Dir1', os.path.normcase('Dir2'), 'Dir3',
                os.path.basename(self._cache_filename)]),
            set(os.listdir(self._temp_dir)))
        self.assertEqual(
            ['Subdir'], os.listdir(os.path.join(self._temp_dir, 'Dir1')))
        self.assertEqual(
            ['Output.txt'],
            os.listdir(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertEqual(
            set([os.path.normcase('Subdir1'), 'Subdir2']),
            set(os.listdir(os.path.join(self._temp_dir, 'Dir2'))))
        self.assertEqual(
            [os.path.normcase('Output.txt')],
            os.listdir(os.path.join(self._temp_dir, 'Dir2', 'Subdir1')))
        self.assertEqual(
            ['Output.txt'],
            os.listdir(os.path.join(self._temp_dir, 'Dir2', 'Subdir2')))
        self.assertEqual(
            set(['Output.txt', os.path.normcase('Output2.txt')]),
            set(os.listdir(os.path.join(self._temp_dir, 'Dir3'))))

    def test_build_change(self):
        """Test file casing when using two different build functions.

        Test that ``FileBuilder`` sets the files' casing correctly when
        we build multiple times using different build functions.
        """
        FileBuilder.build(self._cache_filename, 'case_test', self._build1)
        FileBuilder.build(self._cache_filename, 'case_test', self._build2)
        self._check_build2()

    def _ensure_case(self, filename):
        r"""Ensure that the case of the specified filename is correct.

        Ensure that the case of the specified filename's base name (the
        last component in its path) matches that of
        ``os.path.basename(filename)``. For example, since Windows is
        case-insensitive, if there is a file named ``C:\Foo\Bar``, then
        ``_ensure_case('C:\\Foo\\bar')`` will rename the file to
        ``bar``. However, ``_ensure_case('C:\\foo\\Bar')`` would have no
        effect.
        """
        os.rename(filename, filename)

    def test_external_change(self):
        """Test changing the file system between two build operations.

        Test that ``FileBuilder`` sets the files' casing correctly when
        we change the casing between two build operations.
        """
        FileBuilder.build(self._cache_filename, 'case_test', self._build2)

        self._check_build2()

        self._ensure_case(
            os.path.normcase(os.path.join(self._temp_dir, 'Dir1')))
        self._ensure_case(
            os.path.normcase(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self._ensure_case(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'Output.txt')))
        self._ensure_case(os.path.join(self._temp_dir, 'Dir2'))
        self._ensure_case(os.path.join(self._temp_dir, 'Dir2', 'Subdir1'))
        self._ensure_case(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir1', 'Output.txt'))
        self._ensure_case(
            os.path.normcase(os.path.join(self._temp_dir, 'Dir2', 'Subdir2')))
        self._ensure_case(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir2', 'Output.txt')))
        self._ensure_case(
            os.path.normcase(os.path.join(self._temp_dir, 'Dir3')))
        self._ensure_case(
            os.path.normcase(
                os.path.join(self._temp_dir, 'Dir3', 'Output.txt')))
        self._ensure_case(os.path.join(self._temp_dir, 'Dir3', 'Output2.txt'))
        FileBuilder.build(self._cache_filename, 'case_test', self._build2)

        self._check_build2()

    def test_preexisting(self):
        """Test a build that acts on some preexisting files and directories.

        Test that ``FileBuilder`` sets the files' casing correctly when
        the initial build involves some preexisting files.
        """
        os.mkdir(os.path.normcase(os.path.join(self._temp_dir, 'Dir1')))
        os.mkdir(os.path.join(self._temp_dir, 'Dir2'))
        os.mkdir(
            os.path.normcase(os.path.join(self._temp_dir, 'Dir2', 'Subdir2')))
        os.mkdir(os.path.join(self._temp_dir, 'Dir3'))
        self._write(
            os.path.join(self._temp_dir, 'Dir3', 'Output2.txt'), 'preexisting')
        FileBuilder.build(
            self._cache_filename, 'case_test', self._build2, True)

        self.assertEqual(
            set([
                os.path.normcase('Dir1'), 'Dir2', 'Dir3',
                os.path.basename(self._cache_filename)]),
            set(os.listdir(self._temp_dir)))
        self.assertEqual(
            ['Subdir'], os.listdir(os.path.join(self._temp_dir, 'Dir1')))
        self.assertEqual(
            ['Output.txt'],
            os.listdir(os.path.join(self._temp_dir, 'Dir1', 'Subdir')))
        self.assertEqual(
            set([os.path.normcase('Subdir1'), os.path.normcase('Subdir2')]),
            set(os.listdir(os.path.join(self._temp_dir, 'Dir2'))))
        self.assertEqual(
            [os.path.normcase('Output.txt')],
            os.listdir(os.path.join(self._temp_dir, 'Dir2', 'Subdir1')))
        self.assertEqual(
            ['Output.txt'],
            os.listdir(os.path.join(self._temp_dir, 'Dir2', 'Subdir2')))
        self.assertEqual(
            set(['Output.txt', os.path.normcase('Output2.txt')]),
            set(os.listdir(os.path.join(self._temp_dir, 'Dir3'))))
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir3', 'Output2.txt'), 'text')
