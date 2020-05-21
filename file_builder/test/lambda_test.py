import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class LambdaTest(FileBuilderTest):
    """Tests that ``FileBuilder`` methods accept lambda arguments.

    Tests that ``FileBuilder`` methods accept lambdas for arguments that
    must be callables.
    """

    def _build_file(self, builder, filename):
        """Build file function for ``LambdaTest``."""
        self._write(filename, 'text')

    def _subbuild(self, builder, dir_):
        """Subbuild function for ``LambdaTest``."""
        builder.build_file(
            os.path.join(dir_, 'Output1.txt'), 'build_file', self._build_file)
        builder.build_file(
            os.path.join(dir_, 'Output2.txt'), 'build_file',
            lambda builder, filename: self._write(filename, 'text'))

    def _build(self, builder):
        """Build function for ``LambdaTest``."""
        builder.subbuild(
            'subbuild', self._subbuild, os.path.join(self._temp_dir, 'Dir1'))
        builder.subbuild(
            'subbuild',
            lambda builder, dir_: self._subbuild(builder, dir_),
            os.path.join(self._temp_dir, 'Dir2'))

    def test_lambda(self):
        """Test that ``FileBuilder`` methods accept lambda arguments.

        Test that ``FileBuilder`` methods accept lambdas for arguments
        that must be callable.
        """
        FileBuilder.build(self._cache_filename, 'lambda_test', self._build)

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output2.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output2.txt'), 'text')

        FileBuilder.clean(self._cache_filename, 'lambda_test')

        self.assertEqual([], os.listdir(self._temp_dir))

        FileBuilder.build(
            self._cache_filename, 'lambda_test',
            lambda builder: self._build(builder))

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Output2.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output1.txt'), 'text')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Output2.txt'), 'text')
