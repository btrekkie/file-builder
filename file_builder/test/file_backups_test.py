import os
import shutil
import tempfile
import unittest

from ..file_backups import FileBackups


class FileBackupsTest(unittest.TestCase):
    """Tests the ``FileBackups`` class."""

    def setUp(self):
        self._temp_dir = tempfile.mkdtemp(None, 'file_backups_test_')

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

    def test_restore(self):
        """Test ``FileBackups`` when we restore files."""
        self._write(os.path.join(self._temp_dir, 'File1.txt'), 'contents1')
        os.mkdir(os.path.join(self._temp_dir, 'Dir'))
        self._write(
            os.path.join(self._temp_dir, 'Dir', 'File2.txt'), 'contents2')
        self._write(os.path.join(self._temp_dir, 'File3.txt'), 'contents3')

        with FileBackups() as backups:
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'File1.txt')))
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'Dir', 'File2.txt')))
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'File3.txt')))

            self.assertFalse(
                os.path.exists(os.path.join(self._temp_dir, 'File1.txt')))
            self.assertFalse(
                os.path.exists(
                    os.path.join(self._temp_dir, 'Dir', 'File2.txt')))
            self.assertFalse(
                os.path.exists(os.path.join(self._temp_dir, 'File3.txt')))
            self.assertTrue(os.path.isdir(os.path.join(self._temp_dir, 'Dir')))

            backups.restore_all()

            self._check_contents(
                os.path.join(self._temp_dir, 'File1.txt'), 'contents1')
            self._check_contents(
                os.path.join(self._temp_dir, 'Dir', 'File2.txt'), 'contents2')
            self._check_contents(
                os.path.join(self._temp_dir, 'File3.txt'), 'contents3')

        self._check_contents(
            os.path.join(self._temp_dir, 'File1.txt'), 'contents1')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir', 'File2.txt'), 'contents2')
        self._check_contents(
            os.path.join(self._temp_dir, 'File3.txt'), 'contents3')

    def test_dont_restore(self):
        """Test ``FileBackups`` when we don't restore the files."""
        self._write(os.path.join(self._temp_dir, 'File1.txt'), 'contents1')
        os.mkdir(os.path.join(self._temp_dir, 'Dir'))
        self._write(
            os.path.join(self._temp_dir, 'Dir', 'File2.txt'), 'contents2')
        self._write(os.path.join(self._temp_dir, 'File3.txt'), 'contents3')

        with FileBackups() as backups:
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'File1.txt')))
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'Dir', 'File2.txt')))
            self.assertTrue(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'File3.txt')))

            self.assertFalse(
                os.path.exists(os.path.join(self._temp_dir, 'File1.txt')))
            self.assertFalse(
                os.path.exists(
                    os.path.join(self._temp_dir, 'Dir', 'File2.txt')))
            self.assertFalse(
                os.path.exists(os.path.join(self._temp_dir, 'File3.txt')))
            self.assertTrue(os.path.isdir(os.path.join(self._temp_dir, 'Dir')))

        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'File1.txt')))
        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'Dir', 'File2.txt')))
        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'File3.txt')))
        self.assertTrue(os.path.isdir(os.path.join(self._temp_dir, 'Dir')))

    def test_restore_exception(self):
        """Test ``FileBackups`` when we restore files and catch an exception.

        Test ``FileBackups`` when we restore files, raise an exception
        from the context manager, and catch it.
        """
        self._write(os.path.join(self._temp_dir, 'File.txt'), 'contents')

        with self.assertRaises(RuntimeError):
            with FileBackups() as backups:
                self.assertTrue(
                    backups.back_up_and_remove(
                        os.path.join(self._temp_dir, 'File.txt')))
                backups.restore_all()
                raise RuntimeError()

        self._check_contents(
            os.path.join(self._temp_dir, 'File.txt'), 'contents')

    def test_dont_restore_exception(self):
        """Test ``FileBackups`` when we don't restore the files and catch.

        Test ``FileBackups`` when we raise an exception from the context
        manager and catch it, without restoring files.
        """
        self._write(os.path.join(self._temp_dir, 'File.txt'), 'contents')

        with self.assertRaises(RuntimeError):
            with FileBackups() as backups:
                self.assertTrue(
                    backups.back_up_and_remove(
                        os.path.join(self._temp_dir, 'File.txt')))
                raise RuntimeError()

        self.assertFalse(
            os.path.exists(os.path.join(self._temp_dir, 'File.txt')))

    def test_back_up_non_file(self):
        """Test passing a non-file to ``FileBackups.back_up_and_remove``.

        Test passing a filename that does not refer to a regular file to
        ``FileBackups.back_up_and_remove``.
        """
        os.mkdir(os.path.join(self._temp_dir, 'Dir'))

        with FileBackups() as backups:
            self.assertFalse(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'DoesNotExist.txt')))
            self.assertFalse(
                backups.back_up_and_remove(
                    os.path.join(self._temp_dir, 'Dir')))

            dir_existed = os.path.exists(os.path.join(self._temp_dir, 'Dir'))
            backups.restore_all()
            self.assertEqual(
                dir_existed,
                os.path.exists(os.path.join(self._temp_dir, 'Dir')))
            self.assertFalse(
                os.path.exists(
                    os.path.join(self._temp_dir, 'DoesNotExist.txt')))

    def test_change_files(self):
        """Test ``restore_all()`` when the backup files have changed.

        Test backing up some files, making some file system changes
        pertaining to those files, and then calling ``restore_all()``.
        """
        for i in range(1, 7):
            dir_ = os.path.join(self._temp_dir, 'Dir{:d}'.format(i))
            os.makedirs(os.path.join(dir_, 'Subdir'))
            self._write(
                os.path.join(dir_, 'Subdir', 'File.txt'),
                'contents{:d}'.format(i))

        with FileBackups() as backups:
            for i in range(1, 7):
                dir_ = os.path.join(self._temp_dir, 'Dir{:d}'.format(i))
                self.assertTrue(
                    backups.back_up_and_remove(
                        os.path.join(dir_, 'Subdir', 'File.txt')))
                self.assertFalse(
                    os.path.exists(os.path.join(dir_, 'File.txt')))

            self._write(
                os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'File.txt'),
                'changed')
            os.makedirs(
                os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'File.txt'))
            os.rmdir(os.path.join(self._temp_dir, 'Dir4', 'Subdir'))
            os.rmdir(os.path.join(self._temp_dir, 'Dir4'))
            self._write(os.path.join(self._temp_dir, 'Dir4'), 'contents')
            os.rmdir(os.path.join(self._temp_dir, 'Dir5', 'Subdir'))
            os.rmdir(os.path.join(self._temp_dir, 'Dir5'))
            backups.restore_all()

        self._check_contents(
            os.path.join(self._temp_dir, 'Dir1', 'Subdir', 'File.txt'),
            'contents1')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir2', 'Subdir', 'File.txt'),
            'contents2')
        self.assertTrue(
            os.path.isdir(
                os.path.join(self._temp_dir, 'Dir3', 'Subdir', 'File.txt')))
        self.assertFalse(
            os.path.exists(
                os.path.join(self._temp_dir, 'Dir4', 'Subdir', 'File.txt')))
        self._check_contents(os.path.join(self._temp_dir, 'Dir4'), 'contents')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir5', 'Subdir', 'File.txt'),
            'contents5')
        self._check_contents(
            os.path.join(self._temp_dir, 'Dir6', 'Subdir', 'File.txt'),
            'contents6')
