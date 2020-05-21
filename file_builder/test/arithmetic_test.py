import re
import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class ArithmeticTest(FileBuilderTest):
    """Tests a build process that executes arithmetic operations.

    The build process reads an Operations.txt file containing a list of
    operation names. Then, starting from some integer, it performs the
    operations in turn, writing each intermediate result to a file. Each
    operation is a reference to a file containing a sequence of integer
    additions, subtractions, multiplications, and divisions. We execute
    them from to left to right, without respecting order of operations.

    This is intended to test heavily sequential builds. In particular,
    it tests cases where we repeatedly read a file that we just wrote.
    """

    def setUp(self):
        super().setUp()
        self._input_dir = os.path.join(self._temp_dir, 'Input')
        os.mkdir(self._input_dir)
        self._output_dir = os.path.join(self._temp_dir, 'Output')
        os.mkdir(self._output_dir)

    def _build_file(
            self, builder, output_filename, start_value, input_filename):
        """The build file function."""
        with builder.read_text(input_filename) as file_:
            contents = file_.read()

        offsets = []
        for match in re.finditer(r'[+*/-]', contents):
            if match.start() > 0:
                offsets.append(match.start())
        offsets.append(len(contents))

        value = start_value
        prev_offset = 0
        for offset in offsets:
            operation = contents[prev_offset]
            operand = int(contents[prev_offset + 1:offset])
            if operation == '+':
                value += operand
            elif operation == '-':
                value -= operand
            elif operation == '*':
                value *= operand
            elif operation == '/':
                value //= operand
            else:
                raise RuntimeError('Unhandled operation')
            prev_offset = offset

        self._write(
            output_filename,
            "# Build {:d}\n"
            '{:d}'.format(self._build_number, value))
        return value

    def _build_file_and_get_result(
            self, builder, start_value, operation, read_result):
        """Build a file for the specified math operation and return the result.

        See ``_build``.
        """
        output_filename = os.path.join(self._output_dir, operation)
        result = builder.build_file(
            output_filename, 'build_file', self._build_file, start_value,
            os.path.join(self._input_dir, operation))
        if read_result:
            with builder.read_text(output_filename) as file_:
                return int(file_.read().split("\n")[1])
        else:
            return result

    def _read_operations(self, builder):
        """Return a list of the math operations stored in the operations file.
        """
        operations_filename = os.path.join(self._input_dir, 'Operations.txt')
        with builder.read_text(operations_filename) as file_:
            return file_.read().split("\n")

    def _non_nested_build_or_subbuild(self, builder, start_value, read_result):
        """A build and subbuild function for a build that isn't deeply nested.

        See ``_build``.
        """
        value = start_value
        for operation in self._read_operations(builder):
            value = self._build_file_and_get_result(
                builder, value, operation, read_result)

    def _non_nested_build(self, builder, start_value, read_result):
        """A build function for a build that isn't deeply nested.

        See ``_build``.
        """
        builder.subbuild(
            'subbuild', self._non_nested_build_or_subbuild, start_value,
            read_result)

    def _nested_subbuild(self, builder, start_value, operations, read_result):
        """A subbuild function for a build that is deeply nested.

        See ``_build``.
        """
        if operations:
            value = self._build_file_and_get_result(
                builder, start_value, operations[0], read_result)
            builder.subbuild(
                'subbuild', self._nested_subbuild, value, operations[1:],
                read_result)

    def _nested_build(self, builder, start_value, read_result):
        """A build function for a build that is deeply nested.

        See ``_build``.
        """
        operations = self._read_operations(builder)
        self._nested_subbuild(builder, start_value, operations, read_result)

    def _build(self, start_value, nest, subbuild, read_result):
        """Execute a build operation.

        There are three variations on the build operation, depending on
        the arguments:

        * ``nest = subbuild = False``: There are no subbuilds.
        * ``nest = False, subbuild = True``: Wraps the previous type of
          build operation in a single subbuild.
        * ``nest = subbuild = True``: For every operation, we perform
          the operation, and then we recursively perform the subsequent
          operations in a separate subbuild.

        If ``read_result`` is ``True``, then we obtain the result of a
        math operation by reading the relevant output file. Otherwise,
        we use the return value of the build file function.
        """
        self._build_number += 1
        if nest:
            build_func = self._nested_build
        elif subbuild:
            build_func = self._non_nested_build
        else:
            build_func = self._non_nested_build_or_subbuild
        FileBuilder.build(
            self._cache_filename, 'arithmetic_test', build_func, start_value,
            read_result)

    def _check_arithmetic(self, nest, subbuild, read_result):
        """Test an arithmetic build.

        See ``_build``.
        """
        self._build_number = 0
        self._write(os.path.join(self._input_dir, 'Pi'), '*3+1-4+1/5')
        self._write(os.path.join(self._input_dir, 'E'), '+2+7+1/8*2')
        self._write(os.path.join(self._input_dir, 'Identity'), '+2*5-10/5-0')
        self._write(os.path.join(self._input_dir, 'Increase'), '+2*2+3')
        self._write(os.path.join(self._input_dir, 'Subtract'), '-15-2')
        self._write(
            os.path.join(self._input_dir, 'Operations.txt'),
            "Pi\n"
            "E\n"
            "Identity\n"
            "Increase\n"
            "Subtract")
        self._build(3, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 1\n"
            '1')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 1\n"
            '2')
        self._check_contents(
            os.path.join(self._output_dir, 'Identity'),
            "# Build 1\n"
            '2')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 1\n"
            '11')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 1\n"
            '-6')

        self._write(
            os.path.join(self._input_dir, 'Operations.txt'),
            "Pi\n"
            "E\n"
            "Increase\n"
            "Subtract")
        self._build(3, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 1\n"
            '1')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 1\n"
            '2')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 1\n"
            '11')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 1\n"
            '-6')

        self._write(os.path.join(self._input_dir, 'Increase'), '+9+2')
        self._write(
            os.path.join(self._input_dir, 'Operations.txt'),
            "Pi\n"
            "E\n"
            "Increase\n"
            "Subtract")
        self._build(3, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 1\n"
            '1')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 1\n"
            '2')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 3\n"
            '13')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 3\n"
            '-4')

        self._build(18, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 4\n"
            '10')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 4\n"
            '4')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 4\n"
            '15')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 4\n"
            '-2')

        self._write(os.path.join(self._input_dir, 'E'), '+2+7+1/8*2+8')
        self._write(os.path.join(self._input_dir, 'Sqrt2'), '*1-4+1*4-2')
        self._write(os.path.join(self._input_dir, 'Mult'), '*2')
        self._write(
            os.path.join(self._input_dir, 'Operations.txt'),
            "Pi\n"
            "E\n"
            "Sqrt2\n"
            "Increase\n"
            "Mult\n"
            "Subtract")
        self._build(18, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 4\n"
            '10')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 5\n"
            '12')
        self._check_contents(
            os.path.join(self._output_dir, 'Sqrt2'),
            "# Build 5\n"
            '34')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 5\n"
            '45')
        self._check_contents(
            os.path.join(self._output_dir, 'Mult'),
            "# Build 5\n"
            '90')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 5\n"
            '73')

        self._build(18, nest, subbuild, read_result)

        self._check_contents(
            os.path.join(self._output_dir, 'Pi'),
            "# Build 4\n"
            '10')
        self._check_contents(
            os.path.join(self._output_dir, 'E'),
            "# Build 5\n"
            '12')
        self._check_contents(
            os.path.join(self._output_dir, 'Sqrt2'),
            "# Build 5\n"
            '34')
        self._check_contents(
            os.path.join(self._output_dir, 'Increase'),
            "# Build 5\n"
            '45')
        self._check_contents(
            os.path.join(self._output_dir, 'Mult'),
            "# Build 5\n"
            '90')
        self._check_contents(
            os.path.join(self._output_dir, 'Subtract'),
            "# Build 5\n"
            '73')

    def test_arithmetic(self):
        """Test arithmetic builds."""
        self._check_arithmetic(False, False, False)
        self._check_arithmetic(False, True, False)
        self._check_arithmetic(True, True, False)
        self._check_arithmetic(False, False, True)
        self._check_arithmetic(False, True, True)
        self._check_arithmetic(True, True, True)
