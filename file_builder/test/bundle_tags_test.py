import os
import re

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class BundleTagsTest(FileBuilderTest):
    """Tests a "bundle tags" build operation.

    The build operation takes files from an input directory, processes
    certain components appearing in angle brackets, and stores the
    results in an intermediate directory. Then it concatenates all of
    the files with a given "tag" (specified in the file's contents) into
    a file in the output directory.

    This tests a two-phase build process, where the second phase reads
    files produced in the first phase.
    """

    def setUp(self):
        super().setUp()
        self._build_number = 0
        self._input_dir = os.path.join(self._temp_dir, 'Input')
        os.mkdir(self._input_dir)
        self._output_dir = os.path.join(self._temp_dir, 'Output')
        os.mkdir(self._output_dir)
        self._processed_dir = os.path.join(self._output_dir, 'Processed')
        self._bundles_dir = os.path.join(self._output_dir, 'Bundles')

    def _process_file(self, builder, output_filename, input_filename):
        """Process a file's angle bracket components.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            output_filename (str): The file to store the results in.
            input_filename (str): The file to process.
        """
        with builder.read_text(input_filename) as file_:
            contents_with_tags = file_.read()
        contents = contents_with_tags.split("\n", 1)[1]
        if '<error>' in contents:
            raise RuntimeError('Processing error')

        output = []
        prev_end = 0
        for match in re.finditer(r'<(\d+)\+(\d+)>', contents):
            output.append(contents[prev_end:match.start()])
            output.append(str(int(match.group(1)) + int(match.group(2))))
            prev_end = match.end()
        output.append(contents[prev_end:])

        with open(output_filename, 'w') as file_:
            file_.write("# Build {:d}\n".format(self._build_number))
            for component in output:
                file_.write(component)

    def _process_files(self, builder, input_dir, output_dir):
        """Process the angle bracket components in a given directory.

        Create a directory structure matching ``input_dir`` which
        contained processed copies of the files in that directory.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            input_dir (str): The directory containing the input files.
            output_dir (str): The directory in which to store the
                results.
        """
        processed_dir = os.path.join(output_dir, 'Processed')
        for dir_, subdirs, subfiles in builder.walk(input_dir):
            for subfile in subfiles:
                input_filename = os.path.join(dir_, subfile)
                output_filename = os.path.join(
                    processed_dir,
                    self._try_rel_path(input_filename, input_dir))
                builder.build_file(
                    output_filename, 'process_file', self._process_file,
                    input_filename)

    def _tags(self, builder, filename):
        """Return the tags that the specified file is tagged with.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            filename (str): The file.

        Returns:
            list<str>: The tags.
        """
        with builder.read_text(filename) as file_:
            return file_.readline()[len('# Tags: '):-1].split(',')

    def _create_bundle(self, builder, output_filename, input_filenames):
        """Bundle the specified processed files.

        This concatenates the specified processed input files (as in
        ``_process_file``) into a single output file.

        Arguments:
            builder (FileBuilder): The ``FileBuilder``.
            output_filename (str): The file to store the bundle in.
            input_filenames (list<str>): The input files.
        """
        with open(output_filename, 'w') as output_file:
            output_file.write("# Build {:d}\n".format(self._build_number))
            for input_filename in input_filenames:
                with builder.read_text(input_filename) as input_file:
                    contents = input_file.read()
                contents_without_build_number = contents.split("\n", 1)[1]
                output_file.write(contents_without_build_number)

    def _bundle_files(self, builder, input_dir, output_dir):
        """Bundle the processed files in the specified directory.

        This creates bundles (as in ``_create_bundle``) from all of the
        processed files (as in ``_process_file``) in
        ``os.path.join(output_dir, 'Processed')`` and stores them in
        ``os.path.join(output_dir, 'Bundles')``.
        """
        # Compute a map of the input files in each bundle
        processed_dir = os.path.join(output_dir, 'Processed')
        tag_to_processed_filenames = {}
        for dir_, subdirs, subfiles in builder.walk(input_dir):
            for subfile in subfiles:
                input_filename = os.path.join(dir_, subfile)
                output_filename = os.path.join(
                    processed_dir,
                    self._try_rel_path(input_filename, input_dir))
                tags = builder.subbuild('tags', self._tags, input_filename)
                for tag in tags:
                    tag_to_processed_filenames.setdefault(tag, []).append(
                        output_filename)

        # Build the bundles
        bundles_dir = os.path.join(output_dir, 'Bundles')
        for tag, filenames in tag_to_processed_filenames.items():
            output_filename = os.path.join(bundles_dir, '{:s}.txt'.format(tag))
            builder.build_file(
                output_filename, 'create_bundle', self._create_bundle,
                sorted(filenames))

    def _bundle_tags(self, builder, input_dir, output_dir):
        """Build function for ``BundleTagsTest``."""
        self._process_files(builder, input_dir, output_dir)
        self._bundle_files(builder, input_dir, output_dir)

    def _build(self):
        """Execute the build operation for ``BundleTagsTest``."""
        self._build_number += 1
        FileBuilder.build(
            self._cache_filename, 'bundle_tags_test', self._bundle_tags,
            self._input_dir, self._output_dir)

    def test_bundle_tags(self):
        """Test ``FileBuilder`` using the "bundle tags" build operation."""
        os.mkdir(os.path.join(self._input_dir, 'April'))
        self._write(
            os.path.join(self._input_dir, 'April', 'Piano.txt'),
            "# Tags: music\n"
            "There are <42+46> keys on a standard piano.\n")
        self._write(
            os.path.join(self._input_dir, 'April', 'Beatles.txt'),
            "# Tags: music,entertainment\n"
            'The Beatles recorded <10+3> albums over their <2+5> years '
            "together.\n")
        os.mkdir(os.path.join(self._input_dir, 'May'))
        self._write(
            os.path.join(self._input_dir, 'May', 'Wizard of Oz.txt'),
            "# Tags: entertainment,film\n"
            'In "The Wizard of Oz", Dorothy travels with <0+3> companions: '
            "the Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        os.mkdir(os.path.join(self._input_dir, 'June'))
        self._write(
            os.path.join(self._input_dir, 'June', 'Beethoven.txt'),
            "# Tags: music\n"
            "Beethoven wrote <8+1> symphonies and <3+6> concertos.\n")
        os.mkdir(os.path.join(self._input_dir, 'August'))
        self._write(
            os.path.join(self._input_dir, 'August', 'Planets.txt'),
            "# Tags: astrology\n"
            'There are <6+2> planets in our solar system. It used to be said '
            'that there were <6+3>, but Pluto is no longer regarded as a '
            "planet.\n")
        self._build()

        self.assertEqual(
            set(['Processed', 'Bundles']), set(os.listdir(self._output_dir)))
        self.assertEqual(
            set(['April', 'May', 'June', 'August']),
            set(os.listdir(self._processed_dir)))
        self.assertEqual(
            set([
                'astrology.txt', 'entertainment.txt', 'film.txt',
                'music.txt']),
            set(os.listdir(self._bundles_dir)))

        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Piano.txt'),
            "# Build 1\n"
            "There are 88 keys on a standard piano.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Beatles.txt'),
            "# Build 1\n"
            "The Beatles recorded 13 albums over their 7 years together.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'May', 'Wizard of Oz.txt'),
            "# Build 1\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'June', 'Beethoven.txt'),
            "# Build 1\n"
            "Beethoven wrote 9 symphonies and 9 concertos.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'August', 'Planets.txt'),
            "# Build 1\n"
            'There are 8 planets in our solar system. It used to be said that '
            "there were 9, but Pluto is no longer regarded as a planet.\n")

        self._check_contents(
            os.path.join(self._bundles_dir, 'astrology.txt'),
            "# Build 1\n"
            'There are 8 planets in our solar system. It used to be said that '
            "there were 9, but Pluto is no longer regarded as a planet.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'entertainment.txt'),
            "# Build 1\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'film.txt'),
            "# Build 1\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'music.txt'),
            "# Build 1\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            "There are 88 keys on a standard piano.\n"
            "Beethoven wrote 9 symphonies and 9 concertos.\n")

        self._write(
            os.path.join(self._input_dir, 'August', 'Guitar.txt'),
            "# Tags: music\n"
            "A guitar has <2+4> strings.\n")
        os.remove(os.path.join(self._input_dir, 'April', 'Beatles.txt'))
        os.remove(os.path.join(self._processed_dir, 'August', 'Planets.txt'))
        self._write(
            os.path.join(self._input_dir, 'May', 'Wizard of Oz.txt'),
            "# Tags: entertainment,film,fiction\n"
            'In "The Wizard of Oz", Dorothy travels with <0+3> companions: '
            "the Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are <2+2> companions, because Toto also '
            "accompanies Dorothy.\n")
        self._build()

        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Piano.txt'),
            "# Build 1\n"
            "There are 88 keys on a standard piano.\n")
        self.assertFalse(
            os.path.exists(
                os.path.join(self._processed_dir, 'April', 'Beatles.txt')))
        self._check_contents(
            os.path.join(self._processed_dir, 'May', 'Wizard of Oz.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are 4 companions, because Toto also '
            "accompanies Dorothy.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'June', 'Beethoven.txt'),
            "# Build 1\n"
            "Beethoven wrote 9 symphonies and 9 concertos.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'August', 'Planets.txt'),
            "# Build 2\n"
            'There are 8 planets in our solar system. It used to be said that '
            "there were 9, but Pluto is no longer regarded as a planet.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'August', 'Guitar.txt'),
            "# Build 2\n"
            "A guitar has 6 strings.\n")

        # Depending on whether Planets.txt was generated with the same
        # modification time as before, we may or may not have regenerated
        # astrology.txt
        with open(os.path.join(self._bundles_dir, 'astrology.txt'), 'r') as (
                file_):
            astrology_contents = file_.read()
        self.assertIn(
            astrology_contents,
            [
                "# Build 1\n"
                'There are 8 planets in our solar system. It used to be said '
                'that there were 9, but Pluto is no longer regarded as a '
                "planet.\n",
                "# Build 2\n"
                'There are 8 planets in our solar system. It used to be said '
                'that there were 9, but Pluto is no longer regarded as a '
                "planet.\n"])

        self._check_contents(
            os.path.join(self._bundles_dir, 'entertainment.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are 4 companions, because Toto also '
            "accompanies Dorothy.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'fiction.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are 4 companions, because Toto also '
            "accompanies Dorothy.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'film.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are 4 companions, because Toto also '
            "accompanies Dorothy.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'music.txt'),
            "# Build 2\n"
            "There are 88 keys on a standard piano.\n"
            "A guitar has 6 strings.\n"
            "Beethoven wrote 9 symphonies and 9 concertos.\n")

        os.remove(os.path.join(self._input_dir, 'June', 'Beethoven.txt'))
        self._write(os.path.join(self._bundles_dir, 'astrology.txt'), 'BROKEN')
        self._build()

        self.assertFalse(
            os.path.exists(os.path.join(self._processed_dir, 'June')))
        self._check_contents(
            os.path.join(self._bundles_dir, 'astrology.txt'),
            "# Build 3\n"
            'There are 8 planets in our solar system. It used to be said that '
            "there were 9, but Pluto is no longer regarded as a planet.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'music.txt'),
            "# Build 3\n"
            "There are 88 keys on a standard piano.\n"
            "A guitar has 6 strings.\n")

        FileBuilder.clean(self._cache_filename, 'bundle_tags_test')
        self.assertTrue(os.path.isdir(self._output_dir))
        self.assertEqual([], os.listdir(self._output_dir))
        self.assertFalse(os.path.exists(self._cache_filename))

    def test_rollback(self):
        """Test the rollback feature of ``FileBuilder`` using bundle tags.

        Test the rollback feature of ``FileBuilder`` using the "bundle
        tags" build operation.
        """
        os.mkdir(os.path.join(self._input_dir, 'April'))
        self._write(
            os.path.join(self._input_dir, 'April', 'Piano.txt'),
            "# Tags: music\n"
            "There are <42+46> keys on a standard piano.\n")
        self._write(
            os.path.join(self._input_dir, 'April', 'Beatles.txt'),
            "# Tags: music,entertainment\n"
            'The Beatles recorded <10+3> albums over their <2+5> years '
            "together.\n")
        os.mkdir(os.path.join(self._input_dir, 'May'))
        self._write(
            os.path.join(self._input_dir, 'May', 'Wizard of Oz.txt'),
            "# Tags: entertainment,film\n"
            'In "The Wizard of Oz", <error> Dorothy travels with <0+3> '
            "companions: the Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        with self.assertRaises(RuntimeError):
            self._build()

        self.assertEqual([], os.listdir(self._output_dir))

        self._write(
            os.path.join(self._input_dir, 'May', 'Wizard of Oz.txt'),
            "# Tags: entertainment,film\n"
            'In "The Wizard of Oz", Dorothy travels with <0+3> companions: '
            "the Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._build()

        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Piano.txt'),
            "# Build 2\n"
            "There are 88 keys on a standard piano.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Beatles.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'May', 'Wizard of Oz.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")

        self._check_contents(
            os.path.join(self._bundles_dir, 'entertainment.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'film.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'music.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            "There are 88 keys on a standard piano.\n")

        self._write(
            os.path.join(self._input_dir, 'April', 'Piano.txt'),
            "# Tags: music\n"
            "There are <42+46> keys <error> on a standard piano.\n")
        self._write(
            os.path.join(self._input_dir, 'April', 'Beatles.txt'),
            "# Tags: music,entertainment\n"
            'The Beatles were a rock band that recorded <10+3> albums over '
            "their <2+5> years together.\n")
        self._write(
            os.path.join(self._input_dir, 'May', 'Wizard of Oz.txt'),
            "# Tags: entertainment,film,fiction\n"
            'In "The Wizard of Oz", Dorothy travels with <0+3> companions: '
            "the Scarecrow, the Tin Man, and the Cowardly Lion.\n"
            'Correction: There are <2+2> companions, because Toto also '
            "accompanies Dorothy.\n")
        with self.assertRaises(RuntimeError):
            self._build()

        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Piano.txt'),
            "# Build 2\n"
            "There are 88 keys on a standard piano.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'April', 'Beatles.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n")
        self._check_contents(
            os.path.join(self._processed_dir, 'May', 'Wizard of Oz.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")

        self._check_contents(
            os.path.join(self._bundles_dir, 'entertainment.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'film.txt'),
            "# Build 2\n"
            'In "The Wizard of Oz", Dorothy travels with 3 companions: the '
            "Scarecrow, the Tin Man, and the Cowardly Lion.\n")
        self._check_contents(
            os.path.join(self._bundles_dir, 'music.txt'),
            "# Build 2\n"
            "The Beatles recorded 13 albums over their 7 years together.\n"
            "There are 88 keys on a standard piano.\n")
