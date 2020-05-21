import os

from .. import FileBuilder
from .. import FileComparison
from .file_builder_test import FileBuilderTest


class FileComparisonTest(FileBuilderTest):
    """Tests ``FileBuilder`` with different ``FileComparisons``.

    Tests the behavior of ``FileBuilder`` methods when we pass in
    different ``FileComparisons``.
    """

    # The number of nanoseconds in 365 days
    _NS_PER_YEAR = 365 * 86400 * 1000000000

    def setUp(self):
        super().setUp()
        self._build_number = 0

    def _read_build_file(
            self, builder, output_filename, input_filename, method,
            file_comparison_name):
        """Build file function for ``test_read_*``."""
        file_comparison = FileComparison[file_comparison_name]
        if method == 1:
            with builder.read_text(input_filename, file_comparison) as (
                    input_file):
                self._write(
                    output_filename,
                    "# Build {:d}\n"
                    '{:s}'.format(self._build_number, input_file.read()))
        elif method == 2:
            with builder.read_binary(input_filename, file_comparison) as (
                    input_file):
                with open(output_filename, 'wb') as output_file:
                    output_file.write(
                        "# Build {:d}\n".format(self._build_number).encode())
                    output_file.write(input_file.read())
        elif method == 3:
            builder.declare_read(input_filename, file_comparison)
            with open(input_filename, 'r') as input_file:
                self._write(
                    output_filename,
                    "# Build {:d}\n"
                    '{:s}'.format(self._build_number, input_file.read()))
        else:
            raise ValueError('Unhandled method')

    def _read_build_func(self, builder, file_comparison):
        """Build function for ``test_read_*``."""
        for i in range(1, 4):
            builder.build_file(
                os.path.join(self._temp_dir, 'Output{:d}.txt'.format(i)),
                'build_file', self._read_build_file,
                os.path.join(self._temp_dir, 'Input{:d}.txt'.format(i)), i,
                file_comparison.name)

    def _read_build(self, file_comparison):
        """Execute the build operation for ``test_read_*``."""
        self._build_number += 1
        FileBuilder.build(
            self._cache_filename, 'file_comparison_test',
            self._read_build_func, file_comparison)

    def test_read_metadata(self):
        """Test ``FileBuilder`` read methods with ``FileComparison.METADATA``.
        """
        input_filenames = [
            os.path.join(self._temp_dir, 'Input1.txt'),
            os.path.join(self._temp_dir, 'Input2.txt'),
            os.path.join(self._temp_dir, 'Input3.txt')]
        output_filenames = [
            os.path.join(self._temp_dir, 'Output1.txt'),
            os.path.join(self._temp_dir, 'Output2.txt'),
            os.path.join(self._temp_dir, 'Output3.txt')]
        times1_ns = []
        for filename in input_filenames:
            self._write(filename, 'first')
            os.utime(filename, ns=(0, 0))
            times1_ns.append(os.stat(filename).st_mtime_ns)
        self._read_build(FileComparison.METADATA)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 1\n"
                'first')

        times2_ns = []
        for filename, time1_ns in zip(input_filenames, times1_ns):
            os.utime(filename, ns=(0, FileComparisonTest._NS_PER_YEAR))
            time2_ns = os.stat(filename).st_mtime_ns
            self.assertNotEqual(time1_ns, time2_ns)
            times2_ns.append(time2_ns)
        self._read_build(FileComparison.METADATA)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 2\n"
                'first')

        for filename, time2_ns in zip(input_filenames, times2_ns):
            self._write(filename, 'second')
            os.utime(filename, ns=(0, time2_ns))
            self.assertEqual(time2_ns, os.stat(filename).st_mtime_ns)
        self._read_build(FileComparison.METADATA)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 3\n"
                'second')

        for filename, time2_ns in zip(input_filenames, times2_ns):
            self._write(filename, 's3c0nd')
            os.utime(filename, ns=(0, time2_ns))
            self.assertEqual(time2_ns, os.stat(filename).st_mtime_ns)
        self._read_build(FileComparison.METADATA)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 3\n"
                'second')

    def test_read_hash(self):
        """Test ``FileBuilder``'s read methods with ``FileComparison.HASH``."""
        input_filenames = [
            os.path.join(self._temp_dir, 'Input1.txt'),
            os.path.join(self._temp_dir, 'Input2.txt'),
            os.path.join(self._temp_dir, 'Input3.txt')]
        output_filenames = [
            os.path.join(self._temp_dir, 'Output1.txt'),
            os.path.join(self._temp_dir, 'Output2.txt'),
            os.path.join(self._temp_dir, 'Output3.txt')]
        atimes1_ns = []
        mtimes1_ns = []
        for filename in input_filenames:
            self._write(filename, 'first')
            os.utime(filename, ns=(0, 0))
            atimes1_ns.append(os.stat(filename).st_atime_ns)
            mtimes1_ns.append(os.stat(filename).st_mtime_ns)
        self._read_build(FileComparison.HASH)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 1\n"
                'first')

        atimes2_ns = []
        mtimes2_ns = []
        for filename, atime1_ns, mtime1_ns in zip(
                input_filenames, atimes1_ns, mtimes1_ns):
            os.utime(
                filename,
                ns=(
                    FileComparisonTest._NS_PER_YEAR,
                    FileComparisonTest._NS_PER_YEAR))
            atime2_ns = os.stat(filename).st_atime_ns
            mtime2_ns = os.stat(filename).st_mtime_ns
            self.assertNotEqual(atime1_ns, atime2_ns)
            self.assertNotEqual(mtime1_ns, mtime2_ns)
            atimes2_ns.append(atime2_ns)
            mtimes2_ns.append(mtime2_ns)
        self._read_build(FileComparison.HASH)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 1\n"
                'first')

        for filename, atime2_ns, mtime2_ns in zip(
                input_filenames, atimes2_ns, mtimes2_ns):
            self._write(filename, 'f1r57')
            os.utime(filename, ns=(atime2_ns, mtime2_ns))
            self.assertEqual(atime2_ns, os.stat(filename).st_atime_ns)
            self.assertEqual(mtime2_ns, os.stat(filename).st_mtime_ns)
        self._read_build(FileComparison.HASH)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 3\n"
                'f1r57')

        self._read_build(FileComparison.HASH)

        for filename in output_filenames:
            self._check_contents(
                filename,
                "# Build 3\n"
                'f1r57')

    def _write_build_file(self, builder, filename):
        """Build file function for ``test_write_*``."""
        self._write(
            filename,
            "# Build {:d}\n"
            'original'.format(self._build_number))

    def _write_build_func(self, builder, file_comparison_name):
        """Build function for ``test_write_*``."""
        builder.build_file_with_comparison(
            os.path.join(self._temp_dir, 'Output.txt'),
            FileComparison[file_comparison_name], 'build_file',
            self._write_build_file)

    def _write_build(self, file_comparison):
        """Execute the build operation for ``test_write_*``."""
        self._build_number += 1
        FileBuilder.build(
            self._cache_filename, 'file_comparison_test',
            self._write_build_func, file_comparison.name)

    def test_write_metadata(self):
        """Test building files using ``FileComparison.METADATA`` comparisons.
        """
        filename = os.path.join(self._temp_dir, 'Output.txt')
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 1\n"
            'original')

        time1_ns = os.stat(filename).st_mtime_ns
        self._write(filename, 'changed')
        os.utime(filename, ns=(0, time1_ns))
        time2_ns = os.stat(filename).st_mtime_ns
        self.assertEqual(time1_ns, time2_ns)
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 2\n"
            'original')

        time3_ns = os.stat(filename).st_mtime_ns
        os.utime(filename, ns=(0, time3_ns + FileComparisonTest._NS_PER_YEAR))
        time4_ns = os.stat(filename).st_mtime_ns
        self.assertNotEqual(time3_ns, time4_ns)
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')

        time5_ns = os.stat(filename).st_mtime_ns
        self._write(
            filename,
            "# Build ?\n"
            '0r1g1n47')
        os.utime(filename, ns=(0, time5_ns))
        time6_ns = os.stat(filename).st_mtime_ns
        self.assertEqual(time5_ns, time6_ns)
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build ?\n"
            '0r1g1n47')

        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build ?\n"
            '0r1g1n47')

    def test_write_hash(self):
        """Test building files using ``FileComparison.HASH`` comparisons."""
        filename = os.path.join(self._temp_dir, 'Output.txt')
        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build 1\n"
            'original')

        time1_ns = os.stat(filename).st_mtime_ns
        os.utime(filename, ns=(0, time1_ns + FileComparisonTest._NS_PER_YEAR))
        time2_ns = os.stat(filename).st_mtime_ns
        self.assertNotEqual(time1_ns, time2_ns)
        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build 1\n"
            'original')

        self._write(
            filename,
            "# Build ?\n"
            '0r1g1n47')
        os.utime(filename, ns=(0, time2_ns))
        time3_ns = os.stat(filename).st_mtime_ns
        self.assertEqual(time2_ns, time3_ns)
        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')

        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')

    def test_write_change_comparison(self):
        """Test building a file with multiple comparison types.

        Test building a file and changing the comparison type used for
        that file from one build to the next.
        """
        filename = os.path.join(self._temp_dir, 'Output.txt')
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 1\n"
            'original')

        time1_ns = os.stat(filename).st_mtime_ns
        self._write(
            filename,
            "# Build ?\n"
            '0riginal')
        os.utime(filename, ns=(0, time1_ns))
        time2_ns = os.stat(filename).st_mtime_ns
        self.assertEqual(time1_ns, time2_ns)
        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build ?\n"
            '0riginal')

        self._write(
            filename,
            "# Build !\n"
            '0r1g1n47')
        os.utime(filename, ns=(0, time1_ns))
        time3_ns = os.stat(filename).st_mtime_ns
        self.assertEqual(time1_ns, time3_ns)
        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')

        self._write_build(FileComparison.HASH)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')

        self._write_build(FileComparison.METADATA)

        self._check_contents(
            filename,
            "# Build 3\n"
            'original')
