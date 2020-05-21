import logging
import os
import shutil
import tempfile
import threading

logger = logging.getLogger(__name__)


class FileBackups:
    """Provides the ability to back up files.

    ``FileBackups`` is a context manager that returns itself when
    entered. We may only call methods on a ``FileBackups`` instance if
    we have entered it. When we exit a ``FileBackups`` instance, we
    delete all of the backups. ``FileBackups`` is thread-safe.
    """

    # Private attributes:
    #
    # list<tuple<str, str>> _backups - The backup files. Each pair consists of
    #     the filename of the file we backed up and the filename where we're
    #     storing its backup.
    # Lock _lock - The lock guarding access to _backups and _next_backup_index.
    # int _next_backup_index - An integer identifying the next backup we will
    #     attempt. We use this to select a filename to store the backup. This
    #     starts at 0 and increases by one every time we attempt to back up a
    #     file.
    # str _temp_dir - The temporary directory where we are storing the backups.

    def __init__(self):
        self._backups = []
        self._next_backup_index = 0
        self._temp_dir = None
        self._lock = threading.Lock()

    def __enter__(self):
        self._temp_dir = tempfile.mkdtemp(None, 'file_builder_')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(
            self._temp_dir, False, self._handle_remove_temp_dir_error)
        self._backups.clear()
        self._next_backup_index = 0
        self._temp_dir = None

    def back_up_and_remove(self, filename):
        """Back up the specified file and remove it from its current location.

        If the file does not exist, this has no effect. (This may happen
        during builds that use multithreading.) If the specified
        filename refers to a directory, this may remove the directory.
        This is not normally desirable, but it might be an acceptable
        cost as a way to deal with external modifications to the file
        system.

        Returns:
            bool: Whether the file existed and was a regular file.

        Raises:
            OSError: If an OS error occurred.
        """
        with self._lock:
            value = self._next_backup_index
            self._next_backup_index += 1

        # Store the backup files in subdirectories so that each directory has
        # at most 128 files and 128 directories. This prevents us from having
        # one directory with a ton of files, which may reduce performance.
        components = []
        while value >= 128:
            components.append('{:02x}'.format(value % 128))
            value //= 128
        backup_dir = os.path.join(self._temp_dir, *components)
        backup_filename = os.path.join(backup_dir, 'file_{:02x}'.format(value))

        os.makedirs(backup_dir, exist_ok=True)
        try:
            os.rename(filename, backup_filename)
        except FileNotFoundError:
            return False

        if os.path.isdir(backup_filename):
            # "filename" was a directory when we backed it up
            return False

        with self._lock:
            self._backups.append((filename, backup_filename))
        return True

    def restore_all(self):
        """Restore all files backed up since the last ``restore_all()`` call.

        Each file is restored to its original location/filename,
        overwriting any existing regular files. Whenever we are unable
        to restore a file (e.g. due to an ``OSError``), we skip the file
        and move on to the next one.
        """
        with self._lock:
            backups = self._backups
            self._backups = []

        for filename, backup_filename in backups:
            if os.path.isdir(filename):
                logger.error(
                    'Unable to restore old contents of {:s}, because it is an '
                    'existing directory'.format(filename))
                continue

            try:
                os.makedirs(os.path.dirname(filename), exist_ok=True)
            except OSError:
                logger.error(
                    'Unable to restore old contents of {:s}, because we '
                    'failed to create the parent directories'.format(filename),
                    exc_info=True)
                continue

            try:
                os.replace(backup_filename, filename)
            except OSError:
                logger.error(
                    'Failed to restore old contents of {:s}'.format(filename),
                    exc_info=True)
                continue

            logger.info('Restored old contents of {:s}'.format(filename))

    def _handle_remove_temp_dir_error(self, function, filename, exc_info):
        """Error handler for calling ``shutil.rmtree(self._temp_dir, ...)``."""
        logger.error(
            'Error removing temporary file {:s}'.format(filename),
            exc_info=exc_info)
