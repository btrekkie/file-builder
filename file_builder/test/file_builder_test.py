import os
import shutil
import tempfile
import unittest


class FileBuilderTest(unittest.TestCase):
    """Base class for ``FileBuilder`` test cases.

    The base class's ``setUp()`` method creates a temporary directory
    ``_temp_dir`` we can use for building, and it designates a cache
    filename ``_cache_filename``. The cache file is in ``_temp_dir``.

    ``FileBuilder`` test cases typically use filenames that contain
    uppercase letters. This is a better test on Windows, which has
    case-insensitive filenames.
    """

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp(None, 'file_builder_test_')
        self._cache_filename = os.path.join(self._temp_dir, 'Cache.gz')

    def tearDown(self):
        shutil.rmtree(self._temp_dir)

    def _write(self, filename, contents):
        """Convenience method to write ``contents`` to the file ``filename``.

        Arguments:
            filename (str): The file.
            contents (str): The contents.
        """
        with open(filename, 'w') as file_:
            file_.write(contents)

    def _check_contents(self, filename, expected_contents):
        """Assert that ``filename`` consists of ``expected_contents``.

        Assert that the contents of the specified file are equal to the
        specified string.
        """
        with open(filename, 'r') as file_:
            self.assertEqual(expected_contents, file_.read())

    def _clean_temp_dir(self):
        """Remove all of the files in ``_temp_dir``."""
        for subfile in os.listdir(self._temp_dir):
            absolute_subfile = os.path.join(self._temp_dir, subfile)
            if os.path.isfile(absolute_subfile):
                os.remove(absolute_subfile)
            else:
                shutil.rmtree(absolute_subfile)

    def _normalize_walk(self, walk):
        """Normalize the items in the specified walk.

        Specifically, this returns a list that is the same as ``walk``,
        but whose subdirs and subfiles elements are sorted.

        Arguments:
            walk (list<tuple<str, list<str>, list<str>>>): The walk, as
                in the return value of ``FileBuilder.walk``.
        """
        normalized_walk = []
        for dir_, subdirs, subfiles in walk:
            normalized_walk.append((dir_, sorted(subdirs), sorted(subfiles)))
        return normalized_walk

    def _walk_map(self, walk):
        """Return a map representation of the specified walk.

        This returns a map that for each tuple ``(dir_, subdirs,
        subfiles)`` in ``walk`` contains a mapping from ``dir_`` to
        ``(subdirs, subfiles)``.

        Arguments:
            walk (list<tuple<str, list<str>, list<str>>>): The walk, as
                in the return value of ``FileBuilder.walk``.
        """
        walk_map = {}
        for dir_, subdirs, subfiles in walk:
            walk_map[dir_] = (subdirs, subfiles)
        return walk_map

    def _try_rel_path(self, filename, start_filename=None):
        r"""Return a relative filename.

        Return a relative filename for ``filename`` relative to
        ``start_filename``. If this is not possible, this returns
        ``filename`` instead. For example, on Windows, there is no
        relative filename for ``C:\Foo`` relative to ``D:\Bar``.
        ``start_filename`` defaults to ``os.getcwd()``. ``filename`` and
        ``start_filename`` must be absolute filenames.
        """
        if start_filename is None:
            start_filename = os.getcwd()
        try:
            return os.path.relpath(filename, start_filename)
        except ValueError:
            return filename
