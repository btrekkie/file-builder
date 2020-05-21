from enum import Enum
import functools
import os

from .. import FileBuilder
from .. import FileComparison
from .file_builder_test import FileBuilderTest


class FakeFileComparison(Enum):
    """A fake copy of ``FileComparison``."""

    METADATA = 1
    HASH = 2


class ErrorTest(FileBuilderTest):
    """Tests that ``FileBuilder`` methods raise when they're supposed to.

    This has less to do with ensuring that exceptions occurring in
    functions passed to ``FileBuilder`` methods are propagated, and more
    to do with ensuring that ``FileBuilder`` methods check argument
    types, file system methods raise ``OSErrors`` when appropriate, etc.

    One pattern that ``ErrorTest``'s test methods use is to wrap a bunch
    of method calls with one invalid argument in ``assertRaises``
    blocks, and then to call the method with valid arguments. The valid
    call is supposed to confirm that it was the invalid arguments that
    caused the exceptions.
    """

    def _do_nothing(self, *args, **kwargs):
        pass

    def _return_non_json(self, builder, *args, **kwargs):
        """Return a value that isn't a JSON value."""
        return [object()]

    def test_build_types(self):
        """Test that ``FileBuilder.build`` checks the argument types."""
        with self.assertRaises(TypeError):
            FileBuilder.build(None, 'error_test', self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build(self._cache_filename, None, self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build(self._cache_filename, 'error_test', 'function')
        FileBuilder.build(
            self._cache_filename, 'error_test', self._return_non_json,
            object(), x=object())

    def test_build_versioned_types(self):
        """Test that ``FileBuilder.build_versioned`` checks the argument types.
        """
        with self.assertRaises(TypeError):
            FileBuilder.build_versioned(
                None, 'error_test', {}, self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build_versioned(
                self._cache_filename, None, {}, self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build_versioned(
                self._cache_filename, 'error_test', {'func': object()},
                self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build_versioned(
                self._cache_filename, 'error_test', 42, self._do_nothing)
        with self.assertRaises(TypeError):
            FileBuilder.build_versioned(
                self._cache_filename, 'error_test', {}, 'function')
        FileBuilder.build_versioned(
            self._cache_filename, 'error_test', {}, self._return_non_json,
            object(), x=object())

    def test_clean_types(self):
        """Test that ``FileBuilder.clean`` checks the argument types."""
        with self.assertRaises(TypeError):
            FileBuilder.clean(None, 'error_test')
        with self.assertRaises(TypeError):
            FileBuilder.clean(self._cache_filename, 42)
        FileBuilder.clean(self._cache_filename, 'error_test')

    def _build_file_types_build_file(self, builder, filename):
        """Build file function for ``test_build_file[_with_comparison]_types``.
        """
        self._write(filename, 'text')
        return [object()]

    def _build_file_types_build(self, builder):
        """Build function for ``test_build_file_types``."""
        output_filename1 = os.path.join(self._temp_dir, 'output1.txt')
        with self.assertRaises(TypeError):
            builder.build_file(None, 'build_file', self._write_to_file)
        with self.assertRaises(TypeError):
            builder.build_file(output_filename1, None, self._write_to_file)
        with self.assertRaises(TypeError):
            builder.build_file(output_filename1, 'build_file', 'function')
        with self.assertRaises(TypeError):
            builder.build_file(
                output_filename1, 'build_file', self._write_to_file,
                [object()])
        with self.assertRaises(TypeError):
            builder.build_file(
                output_filename1, 'build_file', self._write_to_file,
                x=[object()])
        with self.assertRaises(TypeError):
            builder.build_file(
                output_filename1, 'build_file',
                self._build_file_types_build_file)
        output_filename2 = os.path.join(self._temp_dir, 'output2.txt')
        builder.build_file(
            output_filename2, 'build_file2', self._write_to_file)

    def test_build_file_types(self):
        """Test that ``FileBuilder.build_file`` checks the argument types."""
        FileBuilder.build(
            self._cache_filename, 'error_test', self._build_file_types_build)

    def _build_file_with_comparison_types_build(self, builder):
        """Build function for ``test_build_file_with_comparison``."""
        output_filename1 = os.path.join(self._temp_dir, 'output1.txt')
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                None, FileComparison.METADATA, 'build_file',
                self._write_to_file)
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FakeFileComparison.METADATA, 'build_file',
                self._write_to_file)
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FileComparison.METADATA, None,
                self._write_to_file)
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FileComparison.METADATA, 'build_file',
                'function')
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FileComparison.METADATA, 'build_file',
                self._write_to_file, [object()])
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FileComparison.METADATA, 'build_file',
                self._write_to_file, x=[object()])
        with self.assertRaises(TypeError):
            builder.build_file_with_comparison(
                output_filename1, FileComparison.METADATA, 'build_file',
                self._build_file_types_build_file)
        output_filename2 = os.path.join(self._temp_dir, 'output2.txt')
        builder.build_file_with_comparison(
            output_filename2, FileComparison.METADATA, 'build_file2',
            self._write_to_file)

    def test_build_file_with_comparison_types(self):
        """Test that ``build_file_with_comparison`` checks the argument types.
        """
        FileBuilder.build(
            self._cache_filename, 'error_test',
            self._build_file_with_comparison_types_build)

    def _subbuild_types_build(self, builder):
        """Build function for ``test_subbuild_types``."""
        with self.assertRaises(TypeError):
            builder.subbuild(None, self._do_nothing)
        with self.assertRaises(TypeError):
            builder.subbuild('subbuild', 'function')
        with self.assertRaises(TypeError):
            builder.subbuild('subbuild', self._do_nothing, [object()])
        with self.assertRaises(TypeError):
            builder.subbuild('subbuild', self._do_nothing, x=[object()])
        with self.assertRaises(TypeError):
            builder.subbuild('subbuild', self._return_non_json, 1)
        builder.subbuild('subbuild2', self._do_nothing, 2)

    def test_subbuild_types(self):
        """Test that ``FileBuilder.subbuild`` checks the argument types."""
        FileBuilder.build(
            self._cache_filename, 'error_test', self._subbuild_types_build)

    def _simple_operation_types_build(self, builder):
        """Build method for ``test_simple_operation_types``."""
        with self.assertRaises(TypeError):
            builder.read_text(None)
        with self.assertRaises(TypeError):
            builder.read_binary(None)
        with self.assertRaises(TypeError):
            builder.declare_read(None)
        with self.assertRaises(TypeError):
            builder.list_dir(None)
        with self.assertRaises(TypeError):
            builder.walk(None)
        with self.assertRaises(TypeError):
            builder.walk(self._temp_dir, 1)
        with self.assertRaises(TypeError):
            builder.is_file(None)
        with self.assertRaises(TypeError):
            builder.is_dir(None)
        with self.assertRaises(TypeError):
            builder.exists(None)
        with self.assertRaises(TypeError):
            builder.get_size(None)

    def test_simple_operation_types(self):
        """Test that simple operations check the argument types."""
        FileBuilder.build(
            self._cache_filename, 'error_test',
            self._simple_operation_types_build)

    def test_build_errors(self):
        """Test that ``FileBuilder.build`` raises the appropriate errors."""
        FileBuilder.build(self._cache_filename, 'error_test', self._do_nothing)
        with self.assertRaises(Exception):
            FileBuilder.build(
                self._cache_filename, 'not_error_test', self._do_nothing)

    def test_clean_errors(self):
        """Test that ``FileBuilder.clean`` raises the appropriate errors."""
        FileBuilder.build(self._cache_filename, 'error_test', self._do_nothing)
        with self.assertRaises(Exception):
            FileBuilder.clean(self._cache_filename, 'not_error_test')

    def test_cache_file_errors(self):
        """Test ``FileBuilder``'s behavior when dealing with bad cache files.
        """
        self._write(self._cache_filename, 'not a cache file')
        with self.assertRaises(Exception):
            FileBuilder.build(
                self._cache_filename, 'error_test', self._do_nothing)
        with self.assertRaises(Exception):
            FileBuilder.build_versioned(
                self._cache_filename, 'error_test', {}, self._do_nothing)
        with self.assertRaises(Exception):
            FileBuilder.clean(self._cache_filename, 'error_test')

        os.remove(self._cache_filename)
        os.mkdir(self._cache_filename)
        with self.assertRaises(IsADirectoryError):
            FileBuilder.build(
                self._cache_filename, 'error_test', self._do_nothing)
        with self.assertRaises(IsADirectoryError):
            FileBuilder.build_versioned(
                self._cache_filename, 'error_test', {}, self._do_nothing)

    def _write_to_file(self, builder, filename, *args, **kwargs):
        """Build file function that outputs some text."""
        self._write(filename, 'text')

    def _build_file(
            self, builder, use_file_comparison, filename, func_name, func,
            *args):
        """Call ``build_file`` or ``build_file_with_comparison``.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            use_file_comparison (bool): Whether to call
                ``build_file_with_comparison``.
            filename (str): The output file.
            func_name (str): A string identifying the function ``func``.
            func (callable): The function, as in the ``func`` argument
                to ``build_file``.
            *args: The positional arguments to the function, apart from
                the ``FileBuilder`` and filename.

        Returns:
            The return value of ``build_file*``.
        """
        if use_file_comparison:
            return builder.build_file_with_comparison(
                filename, FileComparison.METADATA, func_name, func, *args)
        else:
            return builder.build_file(filename, func_name, func, *args)

    def _build_file_errors_build_file(self, builder, filename):
        """Build file function for ``test_build_file_errors``."""
        pass

    def _build_file_errors_build(self, builder, dir_, use_file_comparison):
        """Build function for ``test_build_file_errors``."""
        with self.assertRaises(Exception):
            self._build_file(
                builder, use_file_comparison, self._cache_filename,
                'build_file', self._do_nothing)

        output_filename = os.path.join(self._temp_dir, 'Output.txt')
        self._build_file(
            builder, use_file_comparison, output_filename, 'build_file',
            self._write_to_file)
        norm_cased_output_filename = os.path.normcase(output_filename)
        with self.assertRaises(Exception):
            self._build_file(
                builder, use_file_comparison, norm_cased_output_filename,
                'build_file2', self._do_nothing)
        with self.assertRaises(NotADirectoryError):
            self._build_file(
                builder, use_file_comparison,
                os.path.join(norm_cased_output_filename, 'foo', 'bar.txt'),
                'build_file2', self._do_nothing)
        with self.assertRaises(NotADirectoryError):
            self._build_file(
                builder, use_file_comparison,
                os.path.join(self._cache_filename, 'foo', 'bar.txt'),
                'build_file2', self._do_nothing)
        with self.assertRaises(IsADirectoryError):
            self._build_file(
                builder, use_file_comparison, dir_, 'build_file',
                self._write_to_file)

        self._build_file(
            builder, use_file_comparison,
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz.txt'),
            'build_file', self._write_to_file)
        with self.assertRaises(IsADirectoryError):
            self._build_file(
                builder, use_file_comparison,
                os.path.normcase(os.path.join(self._temp_dir, 'Foo', 'Bar')),
                'build_file', self._write_to_file)

        with self.assertRaises(Exception):
            if use_file_comparison:
                builder.build_file(
                    os.path.join(self._temp_dir, 'Output2.txt'),
                    'build_file_dont_create',
                    self._build_file_errors_build_file)
            else:
                builder.build_file_with_comparison(
                    os.path.join(self._temp_dir, 'Output2.txt'),
                    FileComparison.METADATA, 'build_file_dont_create',
                    self._build_file_errors_build_file)

    def test_build_file_errors(self):
        """Test that various conditions when building files result in errors.
        """
        dir_ = os.path.join(self._temp_dir, 'Dir')
        os.mkdir(dir_)
        FileBuilder.build(
            self._cache_filename, 'error_test', self._build_file_errors_build,
            dir_, False)

        self._clean_temp_dir()
        os.mkdir(dir_)
        FileBuilder.build(
            self._cache_filename, 'error_test', self._build_file_errors_build,
            dir_, True)

    def _repeated_build_file_error_build_file(self, builder, filename):
        """Build file function for ``test_repeated_build_file_error``."""
        raise RuntimeError()

    def _repeated_build_file_error_build(self, builder, use_file_comparison):
        """Build function for ``test_repeated_build_file_error``."""
        output_filename1 = os.path.join(self._temp_dir, 'Output.txt')
        self._build_file(
            builder, use_file_comparison, output_filename1, 'build_file',
            self._write_to_file)
        with self.assertRaises(Exception):
            self._build_file(
                builder, use_file_comparison,
                os.path.normcase(output_filename1), 'build_file2',
                self._do_nothing, 'arg')

        output_filename2 = os.path.join(self._temp_dir, 'Output2.txt')
        with self.assertRaises(RuntimeError):
            self._build_file(
                builder, use_file_comparison, output_filename2, 'build_file',
                self._repeated_build_file_error_build_file)
        with self.assertRaises(Exception):
            self._build_file(
                builder, use_file_comparison, output_filename2, 'build_file',
                self._do_nothing)

        output_filename3 = os.path.join(self._temp_dir, 'Output3.txt')
        with self.assertRaises(TypeError):
            self._build_file(
                builder, use_file_comparison, output_filename3, 'build_file',
                self._return_non_json)
        with self.assertRaises(Exception):
            self._build_file(
                builder, use_file_comparison, output_filename3, 'build_file',
                self._do_nothing)

    def test_repeated_build_file_error(self):
        """Ensure that ``FileBuilder`` raises when we build a file twice."""
        FileBuilder.build(
            self._cache_filename, 'error_test',
            self._repeated_build_file_error_build, False)
        self._clean_temp_dir()
        FileBuilder.build(
            self._cache_filename, 'error_test',
            self._repeated_build_file_error_build, True)

    def _immovable_file_build(self, builder, use_file_comparison, filename):
        """Build function for ``test_immovable_file``."""
        self._build_file(
            builder, use_file_comparison, filename, 'build_file',
            self._write_to_file)

    def _check_immovable_file(self, use_file_comparison):
        """Ensure that ``FileBuilder`` raises when we build an immovable file.

        See the comments for ``test_immovable_file``.
        """
        # Test the good path: it's normally possible to create a file that was
        # a directory in the previous build
        output_filename1 = os.path.join(
            self._temp_dir, 'Foo', 'Bar', 'Baz.txt')
        FileBuilder.build(
            self._cache_filename, 'error_test', self._immovable_file_build,
            use_file_comparison, output_filename1)

        output_filename2 = os.path.join(self._temp_dir, 'Foo')
        FileBuilder.build(
            self._cache_filename, 'error_test', self._immovable_file_build,
            use_file_comparison, output_filename2)

        self.assertTrue(os.path.isfile(output_filename2))

        self._clean_temp_dir()

        # Test the bad path: it's impossible to create a file that was a
        # directory in the previous build, if it contains a file that wasn't
        # created in the previous build
        FileBuilder.build(
            self._cache_filename, 'error_test', self._immovable_file_build,
            use_file_comparison, output_filename1)

        self._write(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'File.txt'), 'content')
        with self.assertRaises(IsADirectoryError):
            FileBuilder.build(
                self._cache_filename, 'error_test', self._immovable_file_build,
                use_file_comparison, output_filename2)

        self.assertEqual(
            set(['Baz.txt', 'File.txt']),
            set(os.listdir(os.path.join(self._temp_dir, 'Foo', 'Bar'))))
        self._check_contents(
            os.path.join(self._temp_dir, 'Foo', 'Bar', 'File.txt'), 'content')
        self.assertTrue(os.path.isfile(output_filename1))

        os.remove(os.path.join(self._temp_dir, 'Foo', 'Bar', 'File.txt'))
        os.mkdir(os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz'))
        with self.assertRaises(IsADirectoryError):
            FileBuilder.build(
                self._cache_filename, 'error_test', self._immovable_file_build,
                use_file_comparison, output_filename2)

        self.assertEqual(
            set(['Baz.txt', 'Baz']),
            set(os.listdir(os.path.join(self._temp_dir, 'Foo', 'Bar'))))
        self.assertTrue(
            os.path.isdir(os.path.join(self._temp_dir, 'Foo', 'Bar', 'Baz')))
        self.assertTrue(os.path.isfile(output_filename1))

    def test_immovable_file(self):
        """Ensure that ``FileBuilder`` raises when we build an immovable file.

        Ensure that ``FileBuilder`` raises an ``IsADirectoryError`` when
        we attempt to build a file that is a directory in the virtual
        state of the file system. This tests the case where the file is
        a directory that was created in the previous build, but we're
        not allowed to remove it because we added a file to it between
        builds.
        """
        self._check_immovable_file(False)
        self._clean_temp_dir()
        self._check_immovable_file(True)

    def _subbuild_errors_subbuild(self, builder, arg):
        """Subbuild function for ``test_subbuild_errors``."""
        with self.assertRaises(Exception):
            builder.subbuild('subbuild', self._do_nothing)
        with self.assertRaises(Exception):
            builder.subbuild('subbuild', self._do_nothing, arg)

    def _subbuild_errors_build(self, builder):
        """Build function for ``test_subbuild_errors``."""
        builder.subbuild('subbuild', self._do_nothing)
        builder.subbuild('subbuild', self._do_nothing, {'foo': [True]})
        builder.subbuild('subbuild', self._do_nothing, {'foo': [1]})
        builder.subbuild('subbuild2', self._do_nothing)
        with self.assertRaises(Exception):
            builder.subbuild('subbuild', self._do_nothing)
        with self.assertRaises(Exception):
            builder.subbuild('subbuild', self._do_nothing, {'foo': [True]})
        with self.assertRaises(Exception):
            builder.subbuild('subbuild', self._do_nothing, {'foo': [1]})
        with self.assertRaises(TypeError):
            builder.subbuild('subbuild3', self._return_non_json)
        with self.assertRaises(Exception):
            builder.subbuild('subbuild3', self._do_nothing)
        builder.subbuild('subbuild', self._subbuild_errors_subbuild, 42)

    def test_subbuild_errors(self):
        """Test that repeating a subbuild results in an error."""
        FileBuilder.build(
            self._cache_filename, 'error_test', self._subbuild_errors_build)

    def _simple_operation_errors_build(self, builder, filename, dir_):
        """Build function for ``test_simple_operation_errors``."""
        does_not_exist_filename = os.path.join(
            self._temp_dir, 'does_not_exist.txt')
        with self.assertRaises(FileNotFoundError):
            builder.read_text(does_not_exist_filename)
        with self.assertRaises(IsADirectoryError):
            builder.read_text(dir_)
        with self.assertRaises(FileNotFoundError):
            builder.read_text(self._cache_filename)

        with self.assertRaises(FileNotFoundError):
            builder.read_binary(does_not_exist_filename)
        with self.assertRaises(IsADirectoryError):
            builder.read_binary(dir_)
        with self.assertRaises(FileNotFoundError):
            builder.read_binary(self._cache_filename)

        with self.assertRaises(FileNotFoundError):
            builder.declare_read(does_not_exist_filename)
        with self.assertRaises(IsADirectoryError):
            builder.declare_read(dir_)
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(self._cache_filename)

        with self.assertRaises(FileNotFoundError):
            builder.list_dir(does_not_exist_filename)
        with self.assertRaises(NotADirectoryError):
            builder.list_dir(filename)
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(self._cache_filename)

        with self.assertRaises(FileNotFoundError):
            builder.get_size(does_not_exist_filename)
        with self.assertRaises(FileNotFoundError):
            builder.get_size(self._cache_filename)

    def test_simple_operation_errors(self):
        """Test that simple operations raise the appropriate exceptions."""
        filename = os.path.join(self._temp_dir, 'filename.txt')
        self._write(filename, 'text')
        dir_ = os.path.join(self._temp_dir, 'dir')
        os.mkdir(dir_)
        FileBuilder.build(
            self._cache_filename, 'error_test',
            self._simple_operation_errors_build, filename, dir_)

    def _check_finished_builder(self, builder, filename, dir_):
        """Assert that a finished builder raises for different operations.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            filename (str): The filename of an existing regular file to
                use in the assertions.
            filename (str): The filename of an existing directory to use
                in the assertions.
        """
        output_filename = os.path.join(self._temp_dir, 'Output2.txt')
        with self.assertRaises(Exception):
            builder.build_file(output_filename, 'build_file', self._do_nothing)
        with self.assertRaises(Exception):
            builder.build_file_with_comparison(
                output_filename, FileComparison.METADATA, 'build_file',
                self._do_nothing)
        with self.assertRaises(Exception):
            builder.subbuild('subbuild2', self._do_nothing)
        with self.assertRaises(Exception):
            builder.read_text(filename)
        with self.assertRaises(Exception):
            builder.read_binary(filename)
        with self.assertRaises(Exception):
            builder.declare_read(filename)
        with self.assertRaises(Exception):
            builder.list_dir(dir_)
        with self.assertRaises(Exception):
            builder.walk(dir_)
        with self.assertRaises(Exception):
            builder.is_file(filename)
        with self.assertRaises(Exception):
            builder.is_dir(dir_)
        with self.assertRaises(Exception):
            builder.exists(filename)
        with self.assertRaises(Exception):
            builder.get_size(filename)

    def _finished_build_file(self, builder_list, builder, filename):
        """Build file function for ``test_finished``."""
        self._write(filename, 'text')
        builder_list.append(builder)

    def _finished_subbuild(self, builder_list, builder):
        """Subbuild function for ``test_finished``."""
        builder_list.append(builder)

    def _finished_build(self, builder, filename, dir_):
        """Build function for ``test_finished``."""
        builder_list1 = []
        builder.subbuild(
            'subbuild',
            functools.partial(self._finished_subbuild, builder_list1))
        finished_builder1 = builder_list1[0]
        self._check_finished_builder(finished_builder1, filename, dir_)

        builder_list2 = []
        builder.build_file(
            os.path.join(self._temp_dir, 'Output1.txt'), 'build_file',
            functools.partial(self._finished_build_file, builder_list2))
        finished_builder2 = builder_list2[0]
        self._check_finished_builder(finished_builder2, filename, dir_)
        return builder

    def test_finished(self):
        """Test that finished ``FileBuilders`` raise for different operations.

        A finished ``FileBuilder`` is one whose corresponding build,
        build file, or subbuild function has returned.
        """
        filename = os.path.join(self._temp_dir, 'filename.txt')
        self._write(filename, 'text')
        dir_ = os.path.join(self._temp_dir, 'dir')
        os.mkdir(dir_)
        builder = FileBuilder.build(
            self._cache_filename, 'error_test', self._finished_build, filename,
            dir_)
        self._check_finished_builder(builder, filename, dir_)
