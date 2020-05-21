import os
from pathlib import Path

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class SimpleOperationsTest(FileBuilderTest):
    """Tests the behavior of simple operations in ``FileBuilder``."""

    def _check_read(self, builder):
        """Test ``FileBuilder.*read*`` for ``test_operations``."""
        filename = os.path.join(self._temp_dir, 'Foo', 'Bar', 'Alpha.txt')
        with builder.read_text(filename) as file_:
            self.assertEqual('12345', file_.read())
        with builder.read_text(os.path.normcase(filename)) as file_:
            self.assertEqual('12345', file_.read())
        with builder.read_binary(filename) as file_:
            self.assertEqual(b'12345', file_.read())
        with builder.read_binary(os.path.normcase(filename)) as file_:
            self.assertEqual(b'12345', file_.read())
        with builder.read_text(os.fsencode(filename)) as file_:
            self.assertEqual('12345', file_.read())
        with builder.read_binary(os.fsencode(filename)) as file_:
            self.assertEqual(b'12345', file_.read())
        with builder.read_text(Path(filename)) as file_:
            self.assertEqual('12345', file_.read())
        with builder.read_binary(Path(filename)) as file_:
            self.assertEqual(b'12345', file_.read())

    def _check_list_dir(self, builder):
        """Test ``FileBuilder.list_dir`` for ``test_operations``."""
        self.assertEqual(
            set(['Foo', 'Sunday', 'Monday']),
            set(builder.list_dir(self._temp_dir)))
        self.assertEqual(
            ['Bar'], builder.list_dir(os.path.join(self._temp_dir, 'Foo')))
        self.assertEqual(
            set(['Baz', 'Alpha.txt']),
            set(builder.list_dir(os.path.join(self._temp_dir, 'Foo', 'Bar'))))
        self.assertEqual(
            set(['Baz', 'Alpha.txt']),
            set(
                builder.list_dir(
                    os.path.normcase(
                        os.path.join(self._temp_dir, 'Foo', 'Bar')))))
        self.assertEqual(
            [],
            builder.list_dir(
                os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz')))
        self.assertEqual(
            [], builder.list_dir(os.path.join(self._temp_dir, 'Sunday')))
        self.assertEqual(
            ['Beta.txt'],
            builder.list_dir(os.path.join(self._temp_dir, 'Monday')))

    def _check_walk(self, builder, dir_, top_down, expected):
        """Check the correctness of ``builder.walk(dir_, top_down)``.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            dir_ (str): The directory.
            top_down (bool): Whether to perform a top-down walk.
            expected (list<tuple<str, list<str>, list<str>>>): The
                expected results of the call to ``walk``. The ordering
                of each list is ignored; ``check_walk`` verifies the
                order of the tuples separately.
        """
        walk = builder.walk(dir_, top_down)
        self.assertIsInstance(walk, list)
        for item in walk:
            self.assertIsInstance(item, tuple)
            self.assertIsInstance(item[0], str)
            self.assertIsInstance(item[1], list)
            self.assertIsInstance(item[2], list)

        normalized_walk = self._normalize_walk(walk)
        normalized_expected = self._normalize_walk(expected)
        self.assertEqual(
            self._walk_map(normalized_expected),
            self._walk_map(normalized_walk))

        indices = {}
        for index, item in enumerate(normalized_walk):
            indices[item[0]] = index
        for dir_, subdirs, subfiles in normalized_expected:
            for subdir in subdirs:
                absolute_subdir = os.path.join(dir_, subdir)
                self.assertEqual(
                    top_down, indices[dir_] < indices[absolute_subdir])

    def _check_walks(self, builder):
        """Test ``FileBuilder.walk`` for ``test_operations``."""
        expected1 = [
            (self._temp_dir, ['Foo', 'Sunday', 'Monday'], []),
            (os.path.join(self._temp_dir, 'Foo'), ['Bar'], []),
            (
                os.path.join(self._temp_dir, 'Foo', 'Bar'),
                ['Baz'],
                ['Alpha.txt'],
            ),
            (os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz'), [], []),
            (os.path.join(self._temp_dir, 'Sunday'), [], []),
            (os.path.join(self._temp_dir, 'Monday'), [], ['Beta.txt']),
        ]
        self._check_walk(builder, os.fsencode(self._temp_dir), True, expected1)
        self._check_walk(builder, self._temp_dir, False, expected1)

        expected2 = [
            (os.path.join(self._temp_dir, 'Foo'), ['Bar'], []),
            (
                os.path.join(self._temp_dir, 'Foo', 'Bar'),
                ['Baz'],
                ['Alpha.txt'],
            ),
            (os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz'), [], []),
        ]
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'Foo'), True, expected2)
        self._check_walk(
            builder, Path(os.path.join(self._temp_dir, 'Foo')), False,
            expected2)

        expected3 = [
            (os.path.normcase(os.path.join(self._temp_dir, 'Sunday')), [], [])]
        self._check_walk(
            builder, os.path.normcase(os.path.join(self._temp_dir, 'Sunday')),
            True, expected3)
        self._check_walk(
            builder, os.path.normcase(os.path.join(self._temp_dir, 'Sunday')),
            False, expected3)

    def _check_file_type(self, builder, filename, is_file, is_dir):
        """Test the file type of ``filename``.

        Test ``FileBuilder``'s ``is_file``, ``is_dir``, and ``exists``
        methods on the specified file.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            filename (str): The filename.
            is_file (bool): Whether the filename is expected to refer to
                a regular file in the virtual state of the filesystem.
            is_dir (bool): Whether the file is expected to refer to a
                directory in the virtual state of the filesystem.
        """
        exists = is_file or is_dir
        self.assertEqual(is_file, builder.is_file(filename))
        self.assertEqual(is_dir, builder.is_dir(filename))
        self.assertEqual(exists, builder.exists(filename))
        self.assertEqual(is_file, builder.is_file(os.path.normcase(filename)))
        self.assertEqual(is_dir, builder.is_dir(os.path.normcase(filename)))
        self.assertEqual(exists, builder.exists(os.path.normcase(filename)))

        self.assertEqual(
            is_file,
            builder.is_file(os.fsencode(self._try_rel_path(filename))))
        self.assertEqual(
            is_dir, builder.is_dir(os.fsencode(self._try_rel_path(filename))))
        self.assertEqual(
            exists, builder.exists(os.fsencode(self._try_rel_path(filename))))
        self.assertEqual(
            is_file,
            builder.is_file(
                os.fsencode(os.path.normcase(self._try_rel_path(filename)))))
        self.assertEqual(
            is_dir,
            builder.is_dir(
                os.fsencode(os.path.normcase(self._try_rel_path(filename)))))
        self.assertEqual(
            exists,
            builder.exists(
                os.fsencode(os.path.normcase(self._try_rel_path(filename)))))

        self.assertEqual(is_file, builder.is_file(Path(filename)))
        self.assertEqual(is_dir, builder.is_dir(Path(filename)))
        self.assertEqual(exists, builder.exists(Path(filename)))
        self.assertEqual(
            is_file, builder.is_file(Path(os.path.normcase(filename))))
        self.assertEqual(
            is_dir, builder.is_dir(Path(os.path.normcase(filename))))
        self.assertEqual(
            exists, builder.exists(Path(os.path.normcase(filename))))

    def _check_file_types(self, builder):
        """Test file type operations for ``test_operations``.

        Test ``FileBuilder``'s ``is_file``, ``is_dir``, and ``exists``
        methods for ``test_operations``.
        """
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'Foo', 'Bar', 'Alpha.txt'),
            True, False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'Monday', 'Beta.txt'), True,
            False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'Foo'), False, True)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'DoesNotExist'), False,
            False)
        self._check_file_type(builder, self._cache_filename, False, False)

    def _check_get_size(self, builder):
        """Test ``FileBuilder.get_size`` for ``test_operations``."""
        filename1 = os.path.join(self._temp_dir, 'Foo', 'Bar', 'Alpha.txt')
        self.assertEqual(5, builder.get_size(filename1))
        self.assertEqual(5, builder.get_size(os.path.normcase(filename1)))
        self.assertEqual(
            5, builder.get_size(os.fsencode(os.path.normcase(filename1))))
        self.assertEqual(
            5,
            builder.get_size(
                Path(os.path.normcase(self._try_rel_path(filename1)))))

        filename2 = os.path.join(self._temp_dir, 'Monday', 'Beta.txt')
        self.assertEqual(0, builder.get_size(filename2))
        self.assertEqual(0, builder.get_size(os.path.normcase(filename2)))
        self.assertEqual(
            0, builder.get_size(os.fsencode(os.path.normcase(filename2))))
        self.assertEqual(
            0,
            builder.get_size(
                Path(os.path.normcase(self._try_rel_path(filename2)))))

    def _check_operations(self, builder):
        """Test ``FileBuilder`` methods for ``test_operations``."""
        self._check_read(builder)
        self._check_list_dir(builder)
        self._check_walks(builder)
        self._check_file_types(builder)
        self._check_get_size(builder)

    def _check_operations_build_file(self, builder, filename):
        """Build file function for ``test_operations``."""
        self._check_operations(builder)
        self._write(filename, 'text')

    def _check_operations_subbuild(self, builder):
        """Subbuild function for ``test_operations``."""
        self._check_operations(builder)
        filename = os.path.join(self._temp_dir, 'Output.txt')
        builder.build_file(
            filename, 'build_file', self._check_operations_build_file)

    def _check_operations_build(self, builder):
        """Build function for ``test_operations``."""
        self._check_operations(builder)
        builder.subbuild('subbuild', self._check_operations_subbuild)

    def test_operations(self):
        """Test the behavior of ``FileBuilder``'s simple operations."""
        os.makedirs(os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz'))
        os.mkdir(os.path.join(self._temp_dir, 'Sunday'))
        os.mkdir(os.path.join(self._temp_dir, 'Monday'))
        self._write(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Alpha.txt'), '12345')
        self._write(os.path.join(self._temp_dir, 'Monday', 'Beta.txt'), '')
        FileBuilder.build(
            self._cache_filename, 'simple_operations_test',
            self._check_operations_build)

    def _check_in_progress_read(self, builder):
        """Test ``FileBuilder.*read*`` for ``test_in_progress``."""
        filename1 = os.path.join(self._temp_dir, 'March', '8', 'F')
        with builder.read_text(filename1) as file_:
            self.assertEqual('abcde', file_.read())
        with builder.read_text(Path(os.path.normcase(filename1))) as file_:
            self.assertEqual('abcde', file_.read())
        with builder.read_binary(filename1) as file_:
            self.assertEqual(b'abcde', file_.read())

        filename2 = os.path.join(self._temp_dir, 'G')
        with builder.read_text(filename2) as file_:
            self.assertEqual('G', file_.read())
        with builder.read_text(Path(self._try_rel_path(filename2))) as file_:
            self.assertEqual('G', file_.read())
        with builder.read_binary(os.path.normcase(filename2)) as file_:
            self.assertEqual(b'G', file_.read())

        filename3 = os.path.join(self._temp_dir, 'I')
        with builder.read_text(self._try_rel_path(filename3)) as file_:
            self.assertEqual('text', file_.read())
        filename4 = os.path.join(self._temp_dir, 'August', '15', 'K')
        with builder.read_text(os.path.normcase(filename4)) as file_:
            self.assertEqual('text', file_.read())

        filename5 = os.path.join(self._temp_dir, 'January', '17', 'B')
        with self.assertRaises(FileNotFoundError):
            builder.read_text(os.path.normcase(filename5))
        with self.assertRaises(FileNotFoundError):
            builder.read_binary(os.fsencode(filename5))
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(Path(filename5))

        filename6 = os.path.join(self._temp_dir, 'August', '25', 'J')
        with self.assertRaises(FileNotFoundError):
            builder.read_text(Path(filename6))
        with self.assertRaises(FileNotFoundError):
            builder.read_binary(filename6)
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(os.fsencode(os.path.normcase(filename6)))

        filename7 = os.path.join(self._temp_dir, 'May')
        with self.assertRaises(IsADirectoryError):
            builder.read_text(filename7)

        filename8 = os.path.join(self._temp_dir, 'April')
        with self.assertRaises(IsADirectoryError):
            builder.read_text(filename8)
        with self.assertRaises(IsADirectoryError):
            builder.read_binary(filename8)
        with self.assertRaises(IsADirectoryError):
            builder.declare_read(filename8)

        filename9 = os.path.join(self._temp_dir, 'August', '15')
        with self.assertRaises(IsADirectoryError):
            builder.read_text(filename9)

        filename10 = os.path.join(self._temp_dir, 'August', '25')
        with self.assertRaises(IsADirectoryError):
            builder.read_binary(filename10)

    def _check_in_progress_list_dir(self, builder):
        """Test ``FileBuilder.list_dir`` for ``test_in_progress``."""
        self.assertEqual(
            set(['March', 'April', 'May', 'June', 'July', 'August', 'G', 'I']),
            set(builder.list_dir(self._temp_dir)))
        self.assertEqual(
            ['F'],
            builder.list_dir(os.path.join(self._temp_dir, 'March', '8')))
        self.assertEqual(
            [], builder.list_dir(os.path.join(self._temp_dir, 'April')))
        self.assertEqual(
            ['H'],
            builder.list_dir(os.path.join(self._temp_dir, 'July', '17')))
        self.assertEqual(
            set(['15', '25']),
            set(builder.list_dir(os.path.join(self._temp_dir, 'August'))))
        self.assertEqual(
            ['K'],
            builder.list_dir(os.path.join(self._temp_dir, 'August', '15')))
        self.assertEqual(
            [], builder.list_dir(os.path.join(self._temp_dir, 'August', '25')))

        with self.assertRaises(FileNotFoundError):
            builder.list_dir(os.path.join(self._temp_dir, 'January'))
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(os.path.join(self._temp_dir, 'E'))
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(os.path.join(self._temp_dir, 'April', '4'))

        with self.assertRaises(NotADirectoryError):
            builder.list_dir(os.path.join(self._temp_dir, 'March', '8', 'F'))
        with self.assertRaises(NotADirectoryError):
            builder.list_dir(os.path.join(self._temp_dir, 'G'))
        with self.assertRaises(NotADirectoryError):
            builder.list_dir(os.path.join(self._temp_dir, 'I'))
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(self._cache_filename)

    def _check_in_progress_walk(self, builder):
        """Test ``FileBuilder.walk`` for ``test_in_progress``."""
        expected1 = [
            (
                self._temp_dir,
                ['March', 'April', 'May', 'June', 'July', 'August'],
                ['G', 'I']
            ),
            (os.path.join(self._temp_dir, 'March'), ['8'], []),
            (os.path.join(self._temp_dir, 'March', '8'), [], ['F']),
            (os.path.join(self._temp_dir, 'April'), [], []),
            (os.path.join(self._temp_dir, 'May'), ['10'], []),
            (os.path.join(self._temp_dir, 'May', '10'), [], []),
            (os.path.join(self._temp_dir, 'June'), [], []),
            (os.path.join(self._temp_dir, 'July'), ['17'], []),
            (os.path.join(self._temp_dir, 'July', '17'), [], ['H']),
            (os.path.join(self._temp_dir, 'August'), ['15', '25'], []),
            (os.path.join(self._temp_dir, 'August', '15'), [], ['K']),
            (os.path.join(self._temp_dir, 'August', '25'), [], []),
        ]
        self._check_walk(builder, self._temp_dir, True, expected1)
        self._check_walk(
            builder, os.fsencode(self._temp_dir), False, expected1)

        expected2 = [
            (os.path.join(self._temp_dir, 'March'), ['8'], []),
            (os.path.join(self._temp_dir, 'March', '8'), [], ['F']),
        ]
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'March'), True, expected2)
        self._check_walk(
            builder,
            Path(self._try_rel_path(os.path.join(self._temp_dir, 'March'))),
            False, expected2)

        expected3 = [(os.path.join(self._temp_dir, 'April'), [], [])]
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'April'), True, expected3)
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'April'), False, expected3)

        expected4 = [(os.path.join(self._temp_dir, 'June'), [], [])]
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'June'), True, expected4)
        self._check_walk(
            builder, os.path.join(self._temp_dir, 'June'), False, expected4)

        expected5 = [(os.path.join(self._temp_dir, 'August', '25'), [], [])]
        self._check_walk(
            builder,
            os.path.join(self._temp_dir, 'August', '25'), True, expected5)
        self._check_walk(
            builder,
            os.path.join(self._temp_dir, 'August', '25'), False, expected5)

        self.assertEqual(
            [], builder.walk(os.path.join(self._temp_dir, 'January')))
        self.assertEqual(
            [], builder.walk(os.path.join(self._temp_dir, 'January'), False))
        self.assertEqual(
            [], builder.walk(os.path.join(self._temp_dir, 'March', '8', 'F')))
        self.assertEqual([], builder.walk(os.path.join(self._temp_dir, 'G')))
        self.assertEqual(
            [], builder.walk(os.path.join(self._temp_dir, 'I'), False))
        self.assertEqual([], builder.walk(self._cache_filename, False))

    def _check_in_progress_file_type(self, builder):
        """Test file type operations for ``test_in_progress``.

        Test ``FileBuilder``'s ``is_file``, ``is_dir``, and ``exists``
        methods for ``test_in_progress``.
        """
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'January'), False, False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'March', '8', 'F'), True,
            False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'G'), True, False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'April'), False, True)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'August'), False, True)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'August', '15'), False, True)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'August', '15', 'K'), True,
            False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'August', '25'), False, True)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'August', '25', 'J'), False,
            False)
        self._check_file_type(
            builder, os.path.join(self._temp_dir, 'I'), True, False)
        self._check_file_type(builder, self._cache_filename, False, False)

    def _check_in_progress_get_size(self, builder):
        """Test ``FileBuilder.get_size`` for ``test_in_progress``."""
        self.assertEqual(
            5,
            builder.get_size(os.path.join(self._temp_dir, 'March', '8', 'F')))
        self.assertEqual(
            1, builder.get_size(os.path.join(self._temp_dir, 'G')))
        self.assertEqual(
            4,
            builder.get_size(
                os.path.join(self._temp_dir, 'August', '15', 'K')))
        self.assertEqual(
            4, builder.get_size(os.path.join(self._temp_dir, 'I')))

        with self.assertRaises(FileNotFoundError):
            builder.get_size(
                os.path.join(self._temp_dir, 'January', '17', 'A'))
        with self.assertRaises(FileNotFoundError):
            builder.get_size(os.path.join(self._temp_dir, 'March', '8', 'C'))
        with self.assertRaises(FileNotFoundError):
            builder.get_size(os.path.join(self._temp_dir, 'August', '25', 'J'))
        with self.assertRaises(FileNotFoundError):
            builder.get_size(self._cache_filename)

    def _check_in_progress(self, builder):
        """Test ``FileBuilder`` methods for ``test_in_progress``."""
        self._check_in_progress_read(builder)
        self._check_in_progress_list_dir(builder)
        self._check_in_progress_walk(builder)
        self._check_in_progress_file_type(builder)
        self._check_in_progress_get_size(builder)

    def _write_to_file(self, builder, filename):
        """Write the word "text" to the specified file."""
        self._write(filename, 'text')

    def _set_up_in_progress(self, builder):
        """Initial build function for ``test_in_progress``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'January', '17', 'A'),
            'write_to_file', self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'January', '17', 'B'),
            'write_to_file', self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'March', '8', 'C'), 'write_to_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'April', '4', 'D'), 'write_to_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'E'), 'write_to_file',
            self._write_to_file)

    def _in_progress_subbuild(self, builder):
        """Subbuild function for ``test_in_progress``."""
        self._check_in_progress(builder)

    def _in_progress_build_file(self, builder, filename):
        """Build file function for ``test_in_progress``."""
        self._write(filename, 'text')
        builder.build_file(
            os.path.join(self._temp_dir, 'August', '15', 'K'), 'write_to_file',
            self._write_to_file)

        self._check_in_progress(builder)
        builder.subbuild('subbuild', self._in_progress_subbuild)

    def _in_progress_build(self, builder):
        """Main build function for ``test_in_progress``."""
        builder.build_file(
            os.path.join(self._temp_dir, 'I'), 'write_to_file',
            self._write_to_file)
        builder.build_file(
            os.path.join(self._temp_dir, 'August', '25', 'J'), 'build_file',
            self._in_progress_build_file)

    def test_in_progress(self):
        """Test ``FileBuilder``'s simple operations when build is in progress.

        In particular, this checks the results of simple operations on
        files and directories created during the previous build or
        during the current build.
        """
        os.mkdir(os.path.join(self._temp_dir, 'April'))
        FileBuilder.build(
            self._cache_filename, 'simple_operations_test',
            self._set_up_in_progress)
        os.makedirs(os.path.join(self._temp_dir, 'May', '10'))
        self._write(os.path.join(self._temp_dir, 'March', '8', 'F'), 'abcde')
        self._write(os.path.join(self._temp_dir, 'G'), 'G')
        os.mkdir(os.path.join(self._temp_dir, 'June'))
        os.makedirs(os.path.join(self._temp_dir, 'July', '17'))
        self._write(os.path.join(self._temp_dir, 'July', '17', 'H'), 'H')
        FileBuilder.build(
            self._cache_filename, 'simple_operations_test',
            self._in_progress_build)

    def _symlinks_build(self, builder):
        """Build function for ``test_symlinks``."""
        file_link = os.path.join(self._temp_dir, 'Foo', 'FileLink')
        dir_link1 = os.path.join(self._temp_dir, 'Foo', 'DirLink1')
        dir_link2 = os.path.join(self._temp_dir, 'Dir', 'DirLink2')
        broken_link = os.path.join(self._temp_dir, 'Foo', 'BrokenLink')

        with builder.read_text(file_link) as file_:
            self.assertEqual('text', file_.read())
        with self.assertRaises(IsADirectoryError):
            builder.read_text(dir_link1)
        with self.assertRaises(FileNotFoundError):
            builder.read_text(broken_link)

        with builder.read_binary(file_link) as file_:
            self.assertEqual(b'text', file_.read())
        with self.assertRaises(IsADirectoryError):
            builder.read_binary(dir_link2)
        with self.assertRaises(FileNotFoundError):
            builder.read_binary(broken_link)

        builder.declare_read(file_link)
        with self.assertRaises(IsADirectoryError):
            builder.declare_read(dir_link1)
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(broken_link)

        with self.assertRaises(NotADirectoryError):
            builder.list_dir(file_link)
        self.assertEqual(
            set(['File.txt', 'DirLink2']), set(builder.list_dir(dir_link1)))
        self.assertEqual(
            set(['File.txt', 'DirLink2']),
            set(builder.list_dir(os.path.join(self._temp_dir, 'Dir'))))
        self.assertEqual(
            set(['Bar', 'FileLink', 'DirLink1']),
            set(builder.list_dir(dir_link2)))
        self.assertEqual(
            set(['Bar', 'FileLink', 'DirLink1']),
            set(builder.list_dir(os.path.join(self._temp_dir, 'Foo'))))
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(broken_link)

        self.assertEqual([], builder.walk(file_link))
        self.assertEqual([], builder.walk(broken_link))
        self.assertEqual(
            [(dir_link1, ['DirLink2'], ['File.txt'])], builder.walk(dir_link1))

        expected_walk1 = [
            (os.path.join(dir_link2, 'Bar'), [], ['Baz.txt']),
            (dir_link2, ['Bar', 'DirLink1'], ['FileLink']),
        ]
        self.assertEqual(
            self._normalize_walk(expected_walk1),
            self._normalize_walk(builder.walk(dir_link2, False)))

        expected_walk2 = [
            (
                os.path.join(self._temp_dir, 'Foo'), ['Bar', 'DirLink1'],
                ['FileLink']),
            (os.path.join(self._temp_dir, 'Foo', 'Bar'), [], ['Baz.txt']),
        ]
        self.assertEqual(
            self._normalize_walk(expected_walk2),
            self._normalize_walk(
                builder.walk(os.path.join(self._temp_dir, 'Foo'))))

        self._check_file_type(builder, file_link, True, False)
        self._check_file_type(builder, dir_link1, False, True)
        self._check_file_type(builder, dir_link2, False, True)
        self._check_file_type(builder, broken_link, False, False)

        self.assertEqual(4, builder.get_size(file_link))
        with self.assertRaises(FileNotFoundError):
            builder.get_size(broken_link)

    def test_symlinks(self):
        """Test ``FileBuilder``'s simple operations on symbolic links."""
        os.makedirs(os.path.join(self._temp_dir, 'Foo', 'Bar'))
        os.mkdir(os.path.join(self._temp_dir, 'Dir'))
        self._write(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz.txt'), 'text')
        self._write(os.path.join(self._temp_dir, 'Dir', 'File.txt'), 'text')

        try:
            os.symlink(
                os.path.join(self._temp_dir, 'Dir'),
                os.path.join(self._temp_dir, 'Foo', 'DirLink1'))
            os.symlink(
                os.path.join(self._temp_dir, 'Foo'),
                os.path.join(self._temp_dir, 'Dir', 'DirLink2'))
            os.symlink(
                os.path.join(self._temp_dir, 'Dir', 'File.txt'),
                os.path.join(self._temp_dir, 'Foo', 'FileLink'))
            os.symlink(
                os.path.join(self._temp_dir, 'Foo', 'DoesNotExist'),
                os.path.join(self._temp_dir, 'Foo', 'BrokenLink'))
        except OSError:
            # Some Windows accounts are not allowed to create symlinks
            return

        FileBuilder.build(
            self._cache_filename, 'simple_operations_test',
            self._symlinks_build)
