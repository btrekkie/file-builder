import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class VersionsTest(FileBuilderTest):
    """Tests function versions in ``FileBuilder``.

    Tests function versions in ``FileBuilder``, as in the ``versions``
    argument to ``build_versioned``. The build function copies a subset
    of the input files to the output directory, after applying a certain
    modification to some of the files' contents and then prepending the
    build number. Which subset of files are copied, what modification to
    apply, and which files to apply it to are based on the versions.
    """

    def setUp(self):
        super().setUp()
        self._build_number = 0
        self._input_dir = os.path.join(self._temp_dir, 'Input')
        os.mkdir(self._input_dir)
        self._output_dir = os.path.join(self._temp_dir, 'Output')
        os.mkdir(self._output_dir)
        self._versions = {}

    def _should_modify(self, builder, relative_filename):
        """Subbuild function for ``test_versions``."""
        input_filename = os.path.join(self._input_dir, relative_filename)
        with builder.read_text(input_filename) as file_:
            contents = file_.read()
        version = self._versions.get('should_modify')
        if version is None:
            return len(contents) >= 30
        elif version == 1:
            return contents.count("\n") > 1
        elif version == 2:
            return 'u' in contents
        else:
            raise RuntimeError('Unknown version')

    def _build_file(self, builder, filename, relative_filename, should_modify):
        """Build file function for ``test_versions``."""
        input_filename = os.path.join(self._input_dir, relative_filename)
        with builder.read_text(input_filename) as file_:
            contents = file_.read()

        if should_modify is None:
            should_modify = builder.subbuild(
                'should_modify', self._should_modify, relative_filename)
        if should_modify:
            version = self._versions.get('build_file')
            if version is None:
                contents = contents.upper()
            elif version == 1:
                contents = contents.lower()
            elif version == 2:
                contents = "Hello, username!\n{:s}".format(contents)
            else:
                raise RuntimeError('Unhandled version')

        self._write(
            filename,
            "# Build {:d}\n"
            '{:s}'.format(self._build_number, contents))

    def _build_func(self, builder):
        """Build function for ``test_versions``."""
        version = self._versions.get('build')
        if version is None:
            version = {
                'limit': 'M',
                'nest': True,
            }

        for subfile in builder.list_dir(self._input_dir):
            if subfile[0] <= version['limit']:
                output_filename = os.path.join(self._output_dir, subfile)
                if version['nest']:
                    should_modify = None
                else:
                    should_modify = builder.subbuild(
                        'should_modify', self._should_modify, subfile)
                builder.build_file(
                    output_filename, 'build_file', self._build_file, subfile,
                    should_modify)

    def _build(self, versions):
        """Execute the build operation for ``test_versions``."""
        self._build_number += 1
        self._versions = versions
        FileBuilder.build_versioned(
            self._cache_filename, 'versions_test', versions, self._build_func)

    def test_versions(self):
        """Test function versions in ``FileBuilder``."""
        self._write(
            os.path.join(self._input_dir, 'Alphabet.txt'),
            "Alpha\n"
            "Bravo\n"
            "Charlie\n"
            "Delta\n"
            "Echo\n")
        self._write(
            os.path.join(self._input_dir, 'High scores.txt'),
            "1. Alice\n"
            "2. Bob\n"
            "3. Charlie\n")
        self._write(os.path.join(self._input_dir, 'Mozart.txt'), 'Mozart')
        self._write(
            os.path.join(self._input_dir, 'Nintendo consoles.txt'),
            'NES, SNES, Nintendo 64, GameCube, Wii, Wii U, Switch, Game Boy, '
            'Game Boy Advance, Nintendo DS, Nintendo 3DS')
        self._write(
            os.path.join(self._input_dir, 'Quantum mechanics.txt'),
            'Quantum mechanics')

        self._build({})
        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 1\n"
            "ALPHA\n"
            "BRAVO\n"
            "CHARLIE\n"
            "DELTA\n"
            "ECHO\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 1\n"
            "1. Alice\n"
            "2. Bob\n"
            "3. Charlie\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 1\n"
            'Mozart')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Nintendo consoles.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Quantum mechanics.txt')))

        self._build({'should_modify': 1})
        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 2\n"
            "ALPHA\n"
            "BRAVO\n"
            "CHARLIE\n"
            "DELTA\n"
            "ECHO\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 2\n"
            "1. ALICE\n"
            "2. BOB\n"
            "3. CHARLIE\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 2\n"
            'Mozart')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Nintendo consoles.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Quantum mechanics.txt')))

        self._build({
            'build': {
                'limit': 'N',
                'nest': False,
            },
            'should_modify': 1,
        })

        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 3\n"
            "ALPHA\n"
            "BRAVO\n"
            "CHARLIE\n"
            "DELTA\n"
            "ECHO\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 3\n"
            "1. ALICE\n"
            "2. BOB\n"
            "3. CHARLIE\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 3\n"
            'Mozart')
        self._check_contents(
            os.path.join(self._output_dir, 'Nintendo consoles.txt'),
            "# Build 3\n"
            'NES, SNES, Nintendo 64, GameCube, Wii, Wii U, Switch, Game Boy, '
            'Game Boy Advance, Nintendo DS, Nintendo 3DS')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Quantum mechanics.txt')))

        self._build({
            'build': {
                'limit': 'N',
                'nest': False,
            },
            'build_file': None,
            'should_modify': None,
        })

        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 3\n"
            "ALPHA\n"
            "BRAVO\n"
            "CHARLIE\n"
            "DELTA\n"
            "ECHO\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 4\n"
            "1. Alice\n"
            "2. Bob\n"
            "3. Charlie\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 3\n"
            'Mozart')
        self._check_contents(
            os.path.join(self._output_dir, 'Nintendo consoles.txt'),
            "# Build 4\n"
            'NES, SNES, NINTENDO 64, GAMECUBE, WII, WII U, SWITCH, GAME BOY, '
            'GAME BOY ADVANCE, NINTENDO DS, NINTENDO 3DS')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Quantum mechanics.txt')))

        self._build({
            'build': {
                'limit': 'N',
                'nest': False,
            },
            'build_file': 1
        })

        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 5\n"
            "alpha\n"
            "bravo\n"
            "charlie\n"
            "delta\n"
            "echo\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 5\n"
            "1. Alice\n"
            "2. Bob\n"
            "3. Charlie\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 5\n"
            'Mozart')
        self._check_contents(
            os.path.join(self._output_dir, 'Nintendo consoles.txt'),
            "# Build 5\n"
            'nes, snes, nintendo 64, gamecube, wii, wii u, switch, game boy, '
            'game boy advance, nintendo ds, nintendo 3ds')
        self.assertFalse(
            os.path.exists(
                os.path.join(self._output_dir, 'Quantum mechanics.txt')))

        self._build({
            'build': {
                'limit': 'Z',
                'nest': False,
            },
            'build_file': 2,
            'should_modify': 2,
        })

        self._check_contents(
            os.path.join(self._output_dir, 'Alphabet.txt'),
            "# Build 6\n"
            "Alpha\n"
            "Bravo\n"
            "Charlie\n"
            "Delta\n"
            "Echo\n")
        self._check_contents(
            os.path.join(self._output_dir, 'High scores.txt'),
            "# Build 6\n"
            "1. Alice\n"
            "2. Bob\n"
            "3. Charlie\n")
        self._check_contents(
            os.path.join(self._output_dir, 'Mozart.txt'),
            "# Build 6\n"
            'Mozart')
        self._check_contents(
            os.path.join(self._output_dir, 'Nintendo consoles.txt'),
            "# Build 6\n"
            "Hello, username!\n"
            'NES, SNES, Nintendo 64, GameCube, Wii, Wii U, Switch, Game Boy, '
            'Game Boy Advance, Nintendo DS, Nintendo 3DS')
        self._check_contents(
            os.path.join(self._output_dir, 'Quantum mechanics.txt'),
            "# Build 6\n"
            "Hello, username!\n"
            'Quantum mechanics')
