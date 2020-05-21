import os

from .. import FileBuilder
from .. import FileComparison
from .file_builder_test import FileBuilderTest


class ErrorHandlingTest(FileBuilderTest):
    """Tests the behavior of ``FileBuilder`` when exceptions are caught.

    The build operation for most of ``ErrorHandlingTest`` copies one
    directory to another. That is, it creates an output directory
    structure matching the input directory which contains copies of the
    files in the input directory. However, there are some quirks:

    * There is a separate subbuild for each subdirectory.
    * If an input file contains the string ``'error'``, then we raise a
      ``RuntimeError` instead of copying it.
    * If a directory is named ``catch``, then its parent directory's
      subbuild catches any ``RuntimeErrors`` that occur in its subbuild.
      When we catch an exception, we create a file named ``Caught.txt``
      in the ``catch`` directory, which contains the word "Caught".
    * Within each directory, we visit subfiles and subdirectories in
      sorted order.
    * We prepend a comment indicating the build number to the beginning
      of each output file.
    """

    def setUp(self):
        super().setUp()
        self._build_number = 0
        self._input_dir = os.path.join(self._temp_dir, 'Input')
        os.mkdir(self._input_dir)
        self._output_dir = os.path.join(self._temp_dir, 'Output')
        os.mkdir(self._output_dir)

    def _copy_file(self, builder, output_filename, input_filename):
        """Copy ``input_filename`` to ``output_filename``.

        Copy ``input_filename`` to ``output_filename``, after prepending
        the build number. If it contains the substring ``'error'``, then
        raise a ``RuntimeError`` instead.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            output_filename (str): The output filename.
            input_filename (str): The input filename.
        """
        builder.declare_read(input_filename, FileComparison.HASH)
        with open(input_filename, 'r') as file_:
            contents = file_.read()
        if 'error' in contents:
            raise RuntimeError()
        self._write(
            output_filename,
            "# Build {:d}\n"
            '{:s}'.format(self._build_number, contents))

    def _write_caught_file(self, builder, filename):
        """Build file function for writing a ``Caught.txt`` file."""
        self._write(
            filename,
            "# Build {:d}\n"
            'Caught'.format(self._build_number))

    def _copy_dir(self, builder, input_dir, output_dir):
        """Subbuild function for copying a directory.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            input_dir (str): The directory containing the input files.
            output_dir (str): The directory in which to store the
                copies.
        """
        for subfile in sorted(builder.list_dir(input_dir)):
            input_filename = os.path.join(input_dir, subfile)
            output_filename = os.path.join(output_dir, subfile)
            if builder.is_file(input_filename):
                builder.build_file(
                    output_filename, 'copy_file', self._copy_file,
                    input_filename)
            else:
                try:
                    builder.subbuild(
                        'copy_dir', self._copy_dir, input_filename,
                        output_filename)
                except RuntimeError:
                    if subfile != 'catch':
                        raise
                    caught_filename = os.path.join(
                        output_filename, 'Caught.txt')
                    builder.build_file(
                        caught_filename, 'write_caught_file',
                        self._write_caught_file)

    def _build(self):
        """Execute the build operation used in most of ``ErrorHandlingTest``.
        """
        self._build_number += 1
        FileBuilder.build(
            self._cache_filename, 'error_handling_test', self._copy_dir,
            self._input_dir, self._output_dir)

    def test_rollback(self):
        """Test ``FileBuilder``'s rollback feature."""
        os.makedirs(os.path.join(self._input_dir, 'History', 'War'))
        os.makedirs(
            os.path.join(
                self._input_dir, 'Science', 'Physics', 'Electromagnetism'))
        self._write(
            os.path.join(
                self._input_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            'Napoleonic Wars')
        self._write(
            os.path.join(self._input_dir, 'History', 'War', 'Trojan War.txt'),
            'Trojan War')
        self._write(
            os.path.join(self._input_dir, 'History', 'ENIAC.txt'),
            '1945, the first computer')
        self._write(
            os.path.join(
                self._input_dir, 'Science', 'Physics', 'Electromagnetism',
                'Maxwell equations.txt'),
            'Maxwell equations')
        self._write(
            os.path.join(
                self._input_dir, 'Science', 'Physics', 'Electromagnetism',
                'Light.txt'),
            'Light: particle or wave?')
        self._write(
            os.path.join(self._input_dir, 'Science', 'Physics', 'Gravity.txt'),
            'Gravity')
        self._write(os.path.join(self._input_dir, 'Manifest.txt'), 'Manifest')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'War', 'Trojan War.txt'),
            "# Build 1\n"
            'Trojan War')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'ENIAC.txt'),
            "# Build 1\n"
            '1945, the first computer')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Electromagnetism',
                'Maxwell equations.txt'),
            "# Build 1\n"
            'Maxwell equations')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Electromagnetism',
                'Light.txt'),
            "# Build 1\n"
            'Light: particle or wave?')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Gravity.txt'),
            "# Build 1\n"
            'Gravity')
        self._check_contents(
            os.path.join(self._output_dir, 'Manifest.txt'),
            "# Build 1\n"
            'Manifest')

        self._write(
            os.path.join(
                self._input_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            'Napoleonic Wars error')
        self._write(
            os.path.join(self._input_dir, 'History', 'ENIAC.txt'),
            '1945, the first digital computer')
        self._write(
            os.path.join(
                self._input_dir, 'Science', 'Physics', 'Electromagnetism',
                'Light.txt'),
            'Light: particle or wave? Travels 300,000,000 m/s in a vacuum.')
        with self.assertRaises(RuntimeError):
            self._build()
        with self.assertRaises(RuntimeError):
            self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'War', 'Trojan War.txt'),
            "# Build 1\n"
            'Trojan War')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'ENIAC.txt'),
            "# Build 1\n"
            '1945, the first computer')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Electromagnetism',
                'Light.txt'),
            "# Build 1\n"
            'Light: particle or wave?')
        self._check_contents(
            os.path.join(self._output_dir, 'Manifest.txt'),
            "# Build 1\n"
            'Manifest')

        self._write(
            os.path.join(
                self._input_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            'Napoleonic Wars')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'History', 'War', 'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'War', 'Trojan War.txt'),
            "# Build 1\n"
            'Trojan War')
        self._check_contents(
            os.path.join(self._output_dir, 'History', 'ENIAC.txt'),
            "# Build 4\n"
            '1945, the first digital computer')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Electromagnetism',
                'Maxwell equations.txt'),
            "# Build 1\n"
            'Maxwell equations')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Electromagnetism',
                'Light.txt'),
            "# Build 4\n"
            'Light: particle or wave? Travels 300,000,000 m/s in a vacuum.')
        self._check_contents(
            os.path.join(
                self._output_dir, 'Science', 'Physics', 'Gravity.txt'),
            "# Build 1\n"
            'Gravity')
        self._check_contents(
            os.path.join(self._output_dir, 'Manifest.txt'),
            "# Build 1\n"
            'Manifest')

    def test_error_catching(self):
        """Test ``FileBuilder``'s behavior when we catch exceptions."""
        os.makedirs(os.path.join(self._input_dir, 'catch', 'History', 'War'))
        os.makedirs(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism'))
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            'Napoleonic Wars')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'History', 'War', 'Trojan War.txt'),
            'Trojan War')
        self._write(
            os.path.join(self._input_dir, 'catch', 'History', 'ENIAC.txt'),
            '1945, the first computer')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Maxwell equations.txt'),
            'Maxwell equations')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Light.txt'),
            'Light: particle or wave?')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Electromagnetic spectrum.txt'),
            'Electromagnetic spectrum')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'Gravity.txt'),
            'Gravity')
        os.mkdir(os.path.join(self._input_dir, 'catch', 'Theater'))
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Theater', 'Shakespeare.txt'),
            'The Bard')
        self._write(
            os.path.join(self._input_dir, 'catch', 'Manifest.txt'), 'Manifest')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War', 'Trojan War.txt'),
            "# Build 1\n"
            'Trojan War')
        self._check_contents(
            os.path.join(self._output_dir, 'catch', 'History', 'ENIAC.txt'),
            "# Build 1\n"
            '1945, the first computer')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Maxwell equations.txt'),
            "# Build 1\n"
            'Maxwell equations')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Light.txt'),
            "# Build 1\n"
            'Light: particle or wave?')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Electromagnetic spectrum.txt'),
            "# Build 1\n"
            'Electromagnetic spectrum')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics',
                'Gravity.txt'),
            "# Build 1\n"
            'Gravity')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Theater', 'Shakespeare.txt'),
            "# Build 1\n"
            'The Bard')
        self._check_contents(
            os.path.join(self._output_dir, 'catch', 'Manifest.txt'),
            "# Build 1\n"
            'Manifest')

        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Light.txt'),
            'Light: particle or wave? error')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Electromagnetic spectrum.txt'),
            "# Build 1\n"
            'Electromagnetic spectrum')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Caught.txt'),
            "# Build 2\n"
            'Caught')
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Light.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Maxwell equations.txt')))
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Theater', 'Shakespeare.txt'),
            "# Build 1\n"
            'The Bard')

        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            "# Build 1\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Electromagnetic spectrum.txt'),
            "# Build 1\n"
            'Electromagnetic spectrum')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Caught.txt'),
            "# Build 2\n"
            'Caught')
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Light.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Maxwell equations.txt')))
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Theater', 'Shakespeare.txt'),
            "# Build 1\n"
            'The Bard')

        self._write(
            os.path.join(
                self._input_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            'error')
        self._write(
            os.path.join(
                self._input_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Light.txt'),
            'Light: particle or wave?')
        self._build()

        self._check_contents(
            os.path.join(self._output_dir, 'catch', 'History', 'ENIAC.txt'),
            "# Build 1\n"
            '1945, the first computer')
        self._check_contents(
            os.path.join(self._output_dir, 'catch', 'Caught.txt'),
            "# Build 4\n"
            'Caught')
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'History', 'War',
                    'Napoleonic Wars.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'History', 'War',
                    'Trojan War.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Maxwell equations.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Light.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Electromagnetism', 'Electromagnetic spectrum.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics',
                    'Gravity.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Theater', 'Shakespeare.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'catch', 'Manifest.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Caught.txt')))

        self._write(
            os.path.join(
                self._input_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            'Napoleonic Wars')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War',
                'Napoleonic Wars.txt'),
            "# Build 5\n"
            'Napoleonic Wars')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'History', 'War', 'Trojan War.txt'),
            "# Build 5\n"
            'Trojan War')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                'Electromagnetism', 'Light.txt'),
            "# Build 5\n"
            'Light: particle or wave?')
        self._check_contents(
            os.path.join(
                self._output_dir, 'catch', 'Theater', 'Shakespeare.txt'),
            "# Build 5\n"
            'The Bard')
        self._check_contents(
            os.path.join(self._output_dir, 'catch', 'Manifest.txt'),
            "# Build 5\n"
            'Manifest')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'catch', 'Caught.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    self._output_dir, 'catch', 'Science', 'Physics', 'catch',
                    'Caught.txt')))

    def test_build_file_exception(self):
        """Test ``FileBuilder``'s behavior when we catch exceptions.

        Test ``FileBuilder``'s behavior when we catch exceptions and
        there is a single output file.
        """
        os.makedirs(
            os.path.join(self._input_dir, 'foo', 'catch', 'bar', 'baz'))
        self._write(
            os.path.join(
                self._input_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'),
            'error')
        self._build()

        self.assertEqual(
            ['Caught.txt'],
            os.listdir(os.path.join(self._output_dir, 'foo', 'catch')))
        self._check_contents(
            os.path.join(self._output_dir, 'foo', 'catch', 'Caught.txt'),
            "# Build 1\n"
            'Caught')

        self._write(
            os.path.join(
                self._input_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'),
            'text')
        self._build()

        self._check_contents(
            os.path.join(
                self._output_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'),
            "# Build 2\n"
            'text')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'foo', 'catch', 'Caught.txt')))

        self._write(
            os.path.join(
                self._input_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'),
            'error')
        self._build()

        self.assertEqual(
            ['Caught.txt'],
            os.listdir(os.path.join(self._output_dir, 'foo', 'catch')))
        self._check_contents(
            os.path.join(self._output_dir, 'foo', 'catch', 'Caught.txt'),
            "# Build 3\n"
            'Caught')

        self._write(
            os.path.join(
                self._input_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'),
            'text')
        self._build()
        os.remove(
            os.path.join(
                self._input_dir, 'foo', 'catch', 'bar', 'baz', 'file.txt'))
        self._build()

        self.assertEqual([], os.listdir(self._output_dir))

    def _caching_operations(self, builder):
        """Perform several file operations with a bunch of error catching.

        This is based on the files created in ``test_caching``.
        """
        filename = os.path.join(self._temp_dir, 'File1.txt')
        dir_ = os.path.join(self._temp_dir, 'Dir', 'Subdir1')
        builder.is_file(filename)
        builder.exists(dir_)

        with self.assertRaises(IsADirectoryError):
            builder.read_text(dir_)
        with self.assertRaises(IsADirectoryError):
            builder.read_binary(dir_)
        with self.assertRaises(IsADirectoryError):
            builder.declare_read(dir_)
        with self.assertRaises(FileNotFoundError):
            builder.read_text(
                os.path.join(
                    self._temp_dir, 'Dir', 'Subdir2', 'Subdir3', 'Output.txt'))
        with self.assertRaises(FileNotFoundError):
            builder.declare_read(
                os.path.join(self._temp_dir, 'DoesNotExist.txt'))

        with self.assertRaises(NotADirectoryError):
            builder.list_dir(filename)
        with self.assertRaises(FileNotFoundError):
            builder.list_dir(os.path.join(self._temp_dir, 'DoesNotExist'))

        builder.is_dir(
            os.path.join(self._temp_dir, 'Dir', 'Subdir2', 'Subdir3'))
        builder.is_file(
            os.path.join(
                self._temp_dir, 'Dir', 'Subdir4', 'Subdir5', 'Output.txt'))
        builder.is_file(os.path.join(self._temp_dir, 'File2.txt'))

    def _caching_build_file(self, builder, filename):
        """Build file function for ``test_caching`` that doesn't raise."""
        self._caching_operations(builder)
        self._write(filename, 'text')
        self._caching_operations(builder)

    def _caching_build_file_error(self, builder, filename):
        """Build file function for ``test_caching`` that raises an exception.
        """
        self._caching_operations(builder)
        raise RuntimeError()

    def _caching_subbuild(self, builder):
        """Subbuild function for ``test_caching``."""
        self._caching_operations(builder)
        with self.assertRaises(RuntimeError):
            builder.build_file(
                os.path.join(
                    self._temp_dir, 'Dir', 'Subdir2', 'Subdir3', 'Output.txt'),
                'build_file_error', self._caching_build_file_error)
        builder.build_file(
            os.path.join(
                self._temp_dir, 'Dir', 'Subdir4', 'Subdir5', 'Output.txt'),
            'build_file', self._caching_build_file)
        self._caching_operations(builder)
        return self._build_number

    def _caching_build(self, builder):
        """Build function for ``test_caching``."""
        self._caching_operations(builder)
        build_number = builder.subbuild('subbuild', self._caching_subbuild)
        self._caching_operations(builder)
        return build_number

    def test_caching(self):
        """Test catching exceptions from file system operations.

        Test the ability to cache builds that contain several file
        system operations, especially operations that result in caught
        exceptions.
        """
        self._build_number = 1
        self._write(os.path.join(self._temp_dir, 'File1.txt'), 'text')
        os.makedirs(os.path.join(self._temp_dir, 'Dir', 'Subdir1'))
        build_number1 = FileBuilder.build(
            self._cache_filename, 'error_handling_test', self._caching_build)
        self.assertEqual(1, build_number1)

        self._build_number = 2
        build_number2 = FileBuilder.build(
            self._cache_filename, 'error_handling_test', self._caching_build)
        self.assertEqual(1, build_number2)

        self._build_number = 3
        self._write(os.path.join(self._temp_dir, 'File2.txt'), 'text')
        build_number3 = FileBuilder.build(
            self._cache_filename, 'error_handling_test', self._caching_build)
        self.assertEqual(3, build_number3)

    def _repeated_operation_caching_build_file(self, builder, filename):
        """Build file function for ``test_repeated_operation_caching``."""
        self._write(filename, 'text')
        return self._build_number

    def _repeated_operation_caching_subbuild1(self, builder):
        """The first subbuild function for ``test_repeated_operation_caching``.
        """
        return self._build_number

    def _repeated_operation_caching_subbuild2(self, builder):
        """Second subbuild function for ``test_repeated_operation_caching``.
        """
        result = builder.build_file(
            os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
            self._repeated_operation_caching_build_file)
        with self.assertRaises(Exception):
            builder.build_file(
                os.path.join(self._temp_dir, 'Output.txt'), 'build_file',
                self._repeated_operation_caching_build_file)
        return result

    def _repeated_operation_caching_subbuild3(self, builder):
        """The third subbuild function for ``test_repeated_operation_caching``.
        """
        result = builder.subbuild(
            'subbuild1', self._repeated_operation_caching_subbuild1)
        with self.assertRaises(Exception):
            builder.subbuild(
                'subbuild1', self._repeated_operation_caching_subbuild1)
        return result

    def _repeated_operation_caching_build(self, builder):
        """Build function for ``test_repeated_operation_caching``."""
        result1 = builder.subbuild(
            'subbuild2', self._repeated_operation_caching_subbuild2)
        result2 = builder.subbuild(
            'subbuild3', self._repeated_operation_caching_subbuild3)
        with self.assertRaises(Exception):
            builder.subbuild(
                'subbuild', self._repeated_operation_caching_subbuild)
        return [result1, result2]

    def test_repeated_operation_caching(self):
        """Test caching when a build file or subbuild operation is repeated.

        Test ``FileBuilder``'s caching when we perform a build file or
        subbuild operation twice in the same build. In particular,
        ``FileBuilder`` should not attempt to reuse the cache entries
        for when we repeated the operations; it should reuse the cache
        entries for when the operations succeeded.
        """
        self._build_number = 1
        result1 = FileBuilder.build(
            self._cache_filename, 'error_handling_test',
            self._repeated_operation_caching_build)

        self.assertEqual([1, 1], result1)

        self._build_number = 2
        result2 = FileBuilder.build(
            self._cache_filename, 'error_handling_test',
            self._repeated_operation_caching_build)

        self.assertEqual([1, 1], result2)
