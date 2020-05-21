import hashlib
import os

from .. import FileBuilder
from .file_builder_test import FileBuilderTest


class HashDirsTest(FileBuilderTest):
    """Tests a hash directory build operation.

    The build operation computes SHA-256 hashes for all of the files and
    directories in a given root directory. A directory's hash
    incorporates the hashes and names of the files and directories in
    the directory.

    This tests nested subbuilds, as each directory and file hash
    operation has its own subbuild.
    """

    def setUp(self):
        super().setUp()
        self._build_number = 0
        self._input_dir = os.path.join(self._temp_dir, 'Input')
        os.mkdir(self._input_dir)

    def _hash_file(self, builder, filename):
        """Build file function that computes a file's hash."""
        digest = hashlib.sha256()
        with builder.read_binary(filename) as file_:
            bytes_ = file_.read(1024)
            while len(bytes_) > 0:
                digest.update(bytes_)
                bytes_ = file_.read(1024)
        hash_ = digest.hexdigest()
        return {
            'build': self._build_number,
            'hash': hash_,
        }

    def _hash_dirs(self, builder, dir_):
        """Subbuild function that computes a directory's hash."""
        digest = hashlib.sha256()
        subfile_results = {}
        for subfile in sorted(builder.list_dir(dir_)):
            digest.update(subfile.encode())
            absolute_subfile = os.path.join(dir_, subfile)
            if builder.is_file(absolute_subfile):
                subfile_result = builder.subbuild(
                    'hash_file', self._hash_file, absolute_subfile)
            else:
                subfile_result = builder.subbuild(
                    'hash_dirs', self._hash_dirs, absolute_subfile)
            subfile_results[subfile] = subfile_result
            digest.update(subfile_result['hash'].encode())

        hash_ = digest.hexdigest()
        return {
            'build': self._build_number,
            'hash': hash_,
            'subfiles': subfile_results,
        }

    def _build(self):
        """Execute the "hash dirs" build operation."""
        self._build_number += 1
        return FileBuilder.build(
            self._cache_filename, 'hash_dirs_test', self._hash_dirs,
            self._input_dir)

    def _file_hash(self, hashes, *components):
        """Return the item in ``hashes`` for the specified file.

        Return the ``'build'`` and ``'hash'`` entries of the item in
        ``hashes`` for ``os.path.join(self._input_dir, *components)``,
        if any.

        Returns:
            dict<str, object>: The result.
        """
        subhashes = hashes
        for component in components:
            if ('subfiles' not in subhashes or
                    component not in subhashes['subfiles']):
                return None
            subhashes = subhashes['subfiles'][component]
        return {
            'build': subhashes['build'],
            'hash': subhashes['hash'],
        }

    def test_hash_dirs(self):
        """Test ``FileBuilder`` with the hash directory build operation."""
        os.makedirs(os.path.join(self._input_dir, 'Book', 'Bus', 'Apple'))
        os.mkdir(os.path.join(self._input_dir, 'Yarn'))
        os.mkdir(os.path.join(self._input_dir, 'Window'))
        self._write(
            os.path.join(self._input_dir, 'Book', 'Cartwheel.txt'), 'Circle')
        self._write(os.path.join(self._input_dir, 'Book', 'Igloo.txt'), 'Wide')
        self._write(
            os.path.join(self._input_dir, 'Book', 'Bus', 'Apple', 'Leaf.txt'),
            'Alphabet')
        self._write(
            os.path.join(self._input_dir, 'Window', 'Cabinet.txt'), 'Orange')
        hashes1 = self._build()

        root_hash1 = self._file_hash(hashes1)
        book_hash1 = self._file_hash(hashes1, 'Book')
        bus_hash1 = self._file_hash(hashes1, 'Book', 'Bus')
        apple_hash1 = self._file_hash(hashes1, 'Book', 'Bus', 'Apple')
        yarn_hash1 = self._file_hash(hashes1, 'Yarn')
        window_hash1 = self._file_hash(hashes1, 'Window')
        cartwheel_hash1 = self._file_hash(hashes1, 'Book', 'Cartwheel.txt')
        igloo_hash1 = self._file_hash(hashes1, 'Book', 'Igloo.txt')
        leaf_hash1 = self._file_hash(
            hashes1, 'Book', 'Bus', 'Apple', 'Leaf.txt')
        cabinet_hash1 = self._file_hash(hashes1, 'Window', 'Cabinet.txt')

        self.assertIsNotNone(root_hash1)
        self.assertIsNotNone(book_hash1)
        self.assertIsNotNone(bus_hash1)
        self.assertIsNotNone(apple_hash1)
        self.assertIsNotNone(yarn_hash1)
        self.assertIsNotNone(window_hash1)
        self.assertIsNotNone(cartwheel_hash1)
        self.assertIsNotNone(igloo_hash1)
        self.assertIsNotNone(leaf_hash1)
        self.assertIsNotNone(cabinet_hash1)

        self._write(
            os.path.join(self._input_dir, 'Window', 'Cabinet.txt'), 'Bicycle')
        hashes2 = self._build()

        root_hash2 = self._file_hash(hashes2)
        book_hash2 = self._file_hash(hashes2, 'Book')
        bus_hash2 = self._file_hash(hashes2, 'Book', 'Bus')
        apple_hash2 = self._file_hash(hashes2, 'Book', 'Bus', 'Apple')
        yarn_hash2 = self._file_hash(hashes2, 'Yarn')
        window_hash2 = self._file_hash(hashes2, 'Window')
        cartwheel_hash2 = self._file_hash(hashes2, 'Book', 'Cartwheel.txt')
        igloo_hash2 = self._file_hash(hashes2, 'Book', 'Igloo.txt')
        leaf_hash2 = self._file_hash(
            hashes2, 'Book', 'Bus', 'Apple', 'Leaf.txt')
        cabinet_hash2 = self._file_hash(hashes2, 'Window', 'Cabinet.txt')

        self.assertNotEqual(root_hash1['hash'], root_hash2['hash'])
        self.assertEqual(2, root_hash2['build'])
        self.assertNotEqual(window_hash1['hash'], window_hash2['hash'])
        self.assertEqual(2, window_hash2['build'])
        self.assertNotEqual(cabinet_hash1['hash'], cabinet_hash2['hash'])
        self.assertEqual(2, cabinet_hash2['build'])
        self.assertEqual(book_hash1, book_hash2)
        self.assertEqual(bus_hash1, bus_hash2)
        self.assertEqual(apple_hash1, apple_hash2)
        self.assertEqual(yarn_hash1, yarn_hash2)
        self.assertEqual(cartwheel_hash1, cartwheel_hash2)
        self.assertEqual(igloo_hash1, igloo_hash2)
        self.assertEqual(leaf_hash1, leaf_hash2)

        self._write(
            os.path.join(self._input_dir, 'Book', 'Bus', 'Clock.txt'),
            'Flower')
        self._write(os.path.join(self._input_dir, 'Yarn', 'Road.txt'), 'Sky')
        os.mkdir(os.path.join(self._input_dir, 'Fruit'))
        os.remove(os.path.join(self._input_dir, 'Window', 'Cabinet.txt'))
        hashes3 = self._build()

        root_hash3 = self._file_hash(hashes3)
        book_hash3 = self._file_hash(hashes3, 'Book')
        bus_hash3 = self._file_hash(hashes3, 'Book', 'Bus')
        apple_hash3 = self._file_hash(hashes3, 'Book', 'Bus', 'Apple')
        yarn_hash3 = self._file_hash(hashes3, 'Yarn')
        window_hash3 = self._file_hash(hashes3, 'Window')
        fruit_hash3 = self._file_hash(hashes3, 'Fruit')
        cartwheel_hash3 = self._file_hash(hashes3, 'Book', 'Cartwheel.txt')
        igloo_hash3 = self._file_hash(hashes3, 'Book', 'Igloo.txt')
        leaf_hash3 = self._file_hash(
            hashes3, 'Book', 'Bus', 'Apple', 'Leaf.txt')
        cabinet_hash3 = self._file_hash(hashes3, 'Window', 'Cabinet.txt')
        clock_hash3 = self._file_hash(hashes3, 'Book', 'Bus', 'Clock.txt')
        road_hash3 = self._file_hash(hashes3, 'Yarn', 'Road.txt')

        self.assertNotEqual(root_hash2['hash'], root_hash3['hash'])
        self.assertEqual(3, root_hash3['build'])
        self.assertNotEqual(book_hash2['hash'], book_hash3['hash'])
        self.assertEqual(3, book_hash3['build'])
        self.assertNotEqual(bus_hash2['hash'], bus_hash3['hash'])
        self.assertEqual(3, bus_hash3['build'])
        self.assertNotEqual(yarn_hash2['hash'], yarn_hash3['hash'])
        self.assertEqual(3, yarn_hash3['build'])
        self.assertNotEqual(window_hash2['hash'], window_hash3['hash'])
        self.assertEqual(3, window_hash3['build'])
        self.assertIsNone(cabinet_hash3)
        self.assertEqual(apple_hash2, apple_hash3)
        self.assertEqual(cartwheel_hash2, cartwheel_hash3)
        self.assertEqual(igloo_hash2, igloo_hash3)
        self.assertEqual(leaf_hash2, leaf_hash3)
        self.assertEqual(3, fruit_hash3['build'])
        self.assertEqual(3, clock_hash3['build'])
        self.assertEqual(3, road_hash3['build'])

        hashes4 = self._build()

        root_hash4 = self._file_hash(hashes4)
        book_hash4 = self._file_hash(hashes4, 'Book')
        bus_hash4 = self._file_hash(hashes4, 'Book', 'Bus')
        apple_hash4 = self._file_hash(hashes4, 'Book', 'Bus', 'Apple')
        yarn_hash4 = self._file_hash(hashes4, 'Yarn')
        window_hash4 = self._file_hash(hashes4, 'Window')
        fruit_hash4 = self._file_hash(hashes4, 'Fruit')
        cartwheel_hash4 = self._file_hash(hashes4, 'Book', 'Cartwheel.txt')
        igloo_hash4 = self._file_hash(hashes4, 'Book', 'Igloo.txt')
        leaf_hash4 = self._file_hash(
            hashes4, 'Book', 'Bus', 'Apple', 'Leaf.txt')
        clock_hash4 = self._file_hash(hashes4, 'Book', 'Bus', 'Clock.txt')
        road_hash4 = self._file_hash(hashes4, 'Yarn', 'Road.txt')

        self.assertNotEqual(root_hash3, root_hash4)
        self.assertEqual(book_hash3, book_hash4)
        self.assertEqual(bus_hash3, bus_hash4)
        self.assertEqual(apple_hash3, apple_hash4)
        self.assertEqual(yarn_hash3, yarn_hash4)
        self.assertEqual(window_hash3, window_hash4)
        self.assertEqual(fruit_hash3, fruit_hash4)
        self.assertEqual(cartwheel_hash3, cartwheel_hash4)
        self.assertEqual(igloo_hash3, igloo_hash4)
        self.assertEqual(leaf_hash3, leaf_hash4)
        self.assertEqual(clock_hash3, clock_hash4)
        self.assertEqual(road_hash3, road_hash4)

        hashes5 = self._build()
        self.assertEqual(5, hashes5['build'])
        self.assertEqual(3, hashes5['subfiles']['Book']['build'])

        hashes6 = self._build()
        self.assertEqual(6, hashes6['build'])
        self.assertEqual(3, hashes6['subfiles']['Book']['build'])
