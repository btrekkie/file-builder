import functools
import os
from pathlib import Path

from .. import FileBuilder
from .. import FileComparison
from .file_builder_test import FileBuilderTest


class MyDict(dict):
    pass


class MyList(list):
    pass


class MyTuple(tuple):
    pass


class MyStr(str):
    pass


class MyInt(int):
    pass


class MyFloat(float):
    pass


class ArgsTest(FileBuilderTest):
    """Tests handling of arguments to subbuild and build file functions.

    Tests that ``FileBuilder`` correctly handles arguments to subbuild
    and build file functions.
    """

    def _non_sanitized_value(self, part):
        """Return a non-sanitized JSON value.

        Return a non-sanitized JSON value containing ``part`` as a
        component.
        """
        my_dict = MyDict()
        my_dict['bar'] = 7
        my_list = MyList()
        my_list.append(True)
        my_list.append(False)
        return {
            42: [
                part, my_dict, my_list, MyStr('abc'), MyInt(23), MyFloat(8.7),
                None, -4.8, float('inf'), -float('inf'), (1,), MyTuple()],
            8: 3,
            '8': 3,
            float('inf'): None,
            None: 17,
            False: False,
        }

    def _assert_sanitized(self, value):
        """Assert that the specified value is a sanitized JSON value."""
        self.assertIn(
            value.__class__, (dict, list, str, int, float, bool, type(None)))
        if isinstance(value, dict):
            for key, subvalue in value.items():
                self.assertIs(str, key.__class__)
                self._assert_sanitized(subvalue)
        elif isinstance(value, list):
            for element in value:
                self._assert_sanitized(element)

    def _check_sanitized_value(self, value, expected_part):
        """Check whether a value is sanitized from ``_non_sanitized_value``.

        Assert that ``value`` is a sanitized form of
        ``_non_sanitized_value(expected_part)``.
        """
        expected = {
            '8': 3,
            '42': [
                expected_part, {'bar': 7}, [True, False], 'abc', 23, 8.7, None,
                -4.8, float('inf'), -float('inf'), [1], []],
            'false': False,
            'Infinity': None,
            'null': 17,
        }
        self.assertEqual(expected, value)
        self._assert_sanitized(value)
        self.assertIs(True, value['42'][2][0])
        self.assertIs(False, value['42'][2][1])
        self.assertIs(int, value['42'][10][0].__class__)
        self.assertIs(False, value['false'])

    def _sanitized_build_file(
            self, builder, filename, cache_buster, value1, value2, keyword1,
            keyword2):
        """Build file function for ``test_sanitized``."""
        self._check_sanitized_value(value1, 21)
        self._check_sanitized_value(value2, 22)
        self._check_sanitized_value(keyword1, 23)
        self._check_sanitized_value(keyword2, 24)
        self._write(
            filename,
            "# Build {:d}\n"
            'text'.format(self._build_number))
        return self._non_sanitized_value(25)

    def _sanitized_subbuild(
            self, builder, cache_busters, value1, value2, keyword1, keyword2):
        """Subbuild function for ``test_sanitized``."""
        self._check_sanitized_value(value1, 11)
        self._check_sanitized_value(value2, 12)
        self._check_sanitized_value(keyword1, 13)
        self._check_sanitized_value(keyword2, 14)
        result = builder.build_file(
            os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
            self._sanitized_build_file, cache_busters[1],
            self._non_sanitized_value(21), self._non_sanitized_value(22),
            keyword2=self._non_sanitized_value(24),
            keyword1=self._non_sanitized_value(23))
        self._check_sanitized_value(result, 25)
        return self._non_sanitized_value(15)

    def _sanitized_build(
            self, builder, cache_busters, value1, value2, keyword1, keyword2):
        """Build function for ``test_sanitized``."""
        self.assertEqual(set([7, MyStr()]), value1)
        values = set(value1)
        values.remove(7)
        self.assertEqual(MyStr, list(values)[0].__class__)
        self.assertEqual(self, value2)
        self.assertEqual(set(), keyword1)
        self.assertEqual('foo', keyword2)
        result = builder.subbuild(
            'subbuild', self._sanitized_subbuild, cache_busters,
            self._non_sanitized_value(11), self._non_sanitized_value(12),
            keyword2=self._non_sanitized_value(14),
            keyword1=self._non_sanitized_value(13))
        self._check_sanitized_value(result, 15)
        return [set()]

    def test_sanitized(self):
        """Test that ``FileBuilder`` sanitizes arguments.

        Test that ``FileBuilder`` sanitizes the arguments to build file
        and subbuild functions.
        """
        self._build_number = 1
        result1 = FileBuilder.build(
            self._cache_filename, 'args_test', self._sanitized_build, [1, 1],
            set([7, MyStr()]), self, keyword2='foo', keyword1=set())

        self.assertEqual([set()], result1)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

        self._build_number = 2
        result2 = FileBuilder.build(
            self._cache_filename, 'args_test', self._sanitized_build, [1, 1],
            set([7, MyStr()]), self, keyword2='foo', keyword1=set())

        self.assertEqual([set()], result2)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

        self._build_number = 3
        result3 = FileBuilder.build(
            self._cache_filename, 'args_test', self._sanitized_build,
            [1, True], set([7, MyStr()]), self, keyword2='foo',
            keyword1=set())

        self.assertEqual([set()], result3)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 3\n"
            'text')

        self._build_number = 4
        result4 = FileBuilder.build(
            self._cache_filename, 'args_test', self._sanitized_build, [2, 3],
            set([7, MyStr()]), self, keyword2='foo', keyword1=set())

        self.assertEqual([set()], result4)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 4\n"
            'text')

    def _copy_build_file(self, builder, filename, value):
        """Build file function for ``test_copy``."""
        value.append(5)
        self._write(
            filename,
            "# Build {:d}\n"
            'text'.format(self._build_number))
        return value

    def _copy_subbuild(self, builder, value):
        """Subbuild function for ``test_copy``."""
        value.append(3)
        build_file_value = []
        result = builder.build_file(
            os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
            self._copy_build_file, build_file_value)
        self.assertEqual([], build_file_value)
        build_file_value.append(4)
        self.assertEqual([5], result)
        self.assertIsNot(build_file_value, result)
        return value

    def _copy_build(self, builder, value):
        """Build function for ``test_copy``."""
        value.append(1)
        subbuild_value = []
        result = builder.subbuild(
            'subbuild', self._copy_subbuild, subbuild_value)
        self.assertEqual([], subbuild_value)
        subbuild_value.append(2)
        self.assertEqual([3], result)
        self.assertIsNot(subbuild_value, result)
        return value

    def test_copy(self):
        """Test that ``FileBuilder`` copies arguments.

        Test that ``FileBuilder`` copies the arguments to build file and
        subbuild functions.
        """
        self._build_number = 1
        value1 = []
        result1 = FileBuilder.build(
            self._cache_filename, 'args_test', self._copy_build, value1)

        self.assertEqual([1], value1)
        value1.append(0)
        self.assertEqual([1, 0], result1)
        self.assertIs(value1, result1)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

        self._build_number = 2
        value2 = []
        result2 = FileBuilder.build(
            self._cache_filename, 'args_test', self._copy_build, value2)

        self.assertEqual([1], value2)
        value2.append(0)
        self.assertEqual([1, 0], result2)
        self.assertIs(value2, result2)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

    def _sanitize_filename_build_file(
            self, filename_type, builder, output_filename):
        """Build file function for ``test_sanitize_filename``."""
        self.assertEqual(
            os.path.join(self._temp_dir, 'Output.txt'), output_filename)
        self._write(
            output_filename,
            "# Build {:d}\n"
            'text'.format(self._build_number))

        filename = os.path.join(self._temp_dir, 'Foo.txt')
        dir_ = os.path.join(self._temp_dir, 'Bar')
        if filename_type == 2:
            filename = os.fsencode(self._try_rel_path(filename))
            dir_ = os.fsencode(self._try_rel_path(dir_))
        elif filename_type == 3:
            filename = Path(self._try_rel_path(filename))
            dir_ = Path(self._try_rel_path(dir_))
        elif filename_type != 1:
            raise ValueError('Unhandled filename type')

        # Add some junk to the cache entry for this function
        with builder.read_text(filename):
            pass
        with builder.read_binary(filename):
            pass
        self.assertTrue(builder.is_file(filename))
        self.assertTrue(builder.is_dir(dir_))
        self.assertTrue(builder.exists(filename))
        self.assertEqual(4, builder.get_size(filename))
        self.assertEqual([], builder.list_dir(dir_))
        self.assertEqual(
            [(os.path.join(self._temp_dir, 'Bar'), [], [])],
            builder.walk(dir_))
        self.assertEqual(
            [(os.path.join(self._temp_dir, 'Bar'), [], [])],
            builder.walk(dir_, False))

    def _sanitize_filename_build(
            self, filename_type, with_comparison, builder):
        """Build function for ``test_sanitize_filename``."""
        if filename_type == 1:
            filename = os.path.join(self._temp_dir, 'Output.txt')
        elif filename_type == 2:
            filename = os.fsencode(
                self._try_rel_path(os.path.join(self._temp_dir, 'Output.txt')))
        elif filename_type == 3:
            filename = Path(
                self._try_rel_path(os.path.join(self._temp_dir, 'Output.txt')))
        else:
            raise ValueError('Unhandled filename type')

        if with_comparison:
            builder.build_file_with_comparison(
                filename, FileComparison.METADATA, 'build_file',
                functools.partial(
                    self._sanitize_filename_build_file, filename_type))
        else:
            builder.build_file(
                filename, 'build_file',
                functools.partial(
                    self._sanitize_filename_build_file, filename_type))

    def test_sanitize_filename(self):
        """Test that ``FileBuilder`` sanitizes filenames."""
        self._build_number = 1
        self._write(os.path.join(self._temp_dir, 'Foo.txt'), 'text')
        os.mkdir(os.path.join(self._temp_dir, 'Bar'))
        FileBuilder.build(
            self._cache_filename, 'args_test',
            functools.partial(self._sanitize_filename_build, 1, False))

        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

        self._build_number = 2
        FileBuilder.build(
            self._cache_filename, 'args_test',
            functools.partial(self._sanitize_filename_build, 2, True))
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

        self._build_number = 3
        FileBuilder.build(
            self._cache_filename, 'args_test',
            functools.partial(self._sanitize_filename_build, 3, False))
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'),
            "# Build 1\n"
            'text')

    def _custom_str_build_file(self, builder, filename):
        """Build file function for ``test_custom_str``."""
        self.assertEqual(str, filename.__class__)
        self._write(filename, 'text')
        return self._build_number

    def _custom_str_subbuild(self, builder):
        """Subbuild function for ``test_custom_str``."""
        result = builder.build_file(
            MyStr(os.path.join(self._temp_dir, 'Output.txt')),
            MyStr('build_file'), self._custom_str_build_file)
        return [self._build_number, result]

    def _custom_str_build(self, builder):
        """Build function for ``test_custom_str``."""
        result = builder.subbuild(MyStr('subbuild'), self._custom_str_subbuild)
        return [self._build_number] + result

    def test_custom_str(self):
        """Test ``FileBuilder``'s behavior when passed subtypes of ``str``."""
        self._build_number = 1
        result1 = FileBuilder.build(
            MyStr(self._cache_filename), MyStr('args_test'),
            self._custom_str_build)

        self.assertEqual([1, 1, 1], result1)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 2
        result2 = FileBuilder.build(
            MyStr(self._cache_filename), MyStr('args_test'),
            self._custom_str_build)

        self.assertEqual([2, 1, 1], result2)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 3
        os.remove(os.path.join(self._temp_dir, 'Output.txt'))
        result3 = FileBuilder.build(
            MyStr(self._cache_filename), MyStr('args_test'),
            self._custom_str_build)

        self.assertEqual([3, 3, 3], result3)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 4
        result4 = FileBuilder.build_versioned(
            MyStr(self._cache_filename), MyStr('args_test'),
            {MyStr('subbuild'): MyStr('version2')}, self._custom_str_build)

        self.assertEqual([4, 4, 3], result4)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 5
        result5 = FileBuilder.build_versioned(
            MyStr(self._cache_filename), MyStr('args_test'),
            {MyStr('subbuild'): MyStr('version2')}, self._custom_str_build)

        self.assertEqual([5, 4, 3], result5)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 6
        result6 = FileBuilder.build_versioned(
            MyStr(self._cache_filename), MyStr('args_test'), {
                MyStr('subbuild'): MyStr('version2'),
                MyStr('build_file'): MyStr('version2')
            }, self._custom_str_build)

        self.assertEqual([6, 6, 6], result6)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        self._build_number = 7
        result7 = FileBuilder.build_versioned(
            MyStr(self._cache_filename), MyStr('args_test'), {
                MyStr('subbuild'): MyStr('version2'),
                MyStr('build_file'): MyStr('version2')
            }, self._custom_str_build)

        self.assertEqual([7, 6, 6], result7)
        self._check_contents(
            os.path.join(self._temp_dir, 'Output.txt'), 'text')

        FileBuilder.clean(MyStr(self._cache_filename), MyStr('args_test'))

        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'Output.txt')))

        FileBuilder.clean(MyStr(self._cache_filename), MyStr('args_test'))

        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'Output.txt')))
