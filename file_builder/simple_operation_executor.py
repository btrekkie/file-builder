import hashlib
import os
import stat
import threading


class SimpleOperationExecutor:
    """Executes simple operations.

    All simple operations are performed according to the virtual state
    of the file system. The return values of ``SimpleOperationExecutor``
    are deterministic in the sense of ``JsonUtil.is_equal``. For
    example, the order of the files returned by ``list_dir`` is
    consistent. ``SimpleOperationExecutor`` is thread-safe. See the
    comments for ``FileBuilder`` and ``Operation``.
    """

    # Private attributes:
    #
    # BuildDirs _build_dirs - The BuildDirs instance for the current build.
    # dict<str, tuple<str, bool>> _hash_cache - A cache mapping from norm-cased
    #     filenames to their hashes. Each value is a pair consisting of the
    #     SHA-256 hex string and a boolean indicating whether we have started
    #     (or finished) building the file.
    # Lock _hash_cache_lock - The lock guarding access to _hash_cache.
    # Cache _new_cache - The Cache object storing the cached results for the
    #     current build. Note that we don't add created directories to
    #     _new_cache until we've finished calling the function passed to
    #     FileBuilder.build_versioned.
    # str _norm_cased_cache_filename - The norm-cased cache file.
    # Cache _old_cache - The Cache object storing the cached results from the
    #     previous build.

    # The names of all available simple operations. They each correspond to a
    # SimpleOperationExecutor method of the same name.
    OPERATIONS = set([
        'exists', 'get_size', 'is_dir', 'is_file', 'list_dir', 'read', 'walk'
    ])

    def __init__(self, cache_filename, old_cache, new_cache, build_dirs):
        self._norm_cased_cache_filename = os.path.normcase(cache_filename)
        self._old_cache = old_cache
        self._new_cache = new_cache
        self._build_dirs = build_dirs
        self._hash_cache = {}
        self._hash_cache_lock = threading.Lock()

    def exec(self, name, args, created_files):
        """Execute the specified simple operation.

        Arguments:
            name (str): The operation's name, as in
                ``SimpleOperation.name``
            args (list): The positional arguments to the operation,
                apart from ``created_files``.
            created_files (CreatedFiles): The ``created_files`` argument
                to the operation: the files to regard as created, if
                any.

        Returns:
            The return value of the corresponding
            ``SimpleOperationExecutor`` method.

        Raises:
            Exception: If the corresponding ``SimpleOperationExecutor``
                method raised an exception.
        """
        if name not in SimpleOperationExecutor.OPERATIONS:
            raise ValueError('Invalid operation')
        return getattr(self, name)(*(args + [created_files]))

    def file_comparison_result(self, filename, file_comparison_name):
        """Return the result of the specified file comparison.

        Return a non-``None`` JSON object describing the result of
        performing the specified comparison on the specified file. If
        the same call produces an equal return value later on (as in
        ``JsonUtil.is_equal``), then we conclude that the file hasn't
        changed. Unlike most other ``SimpleOperationExecutor`` methods,
        this method's behavior is based on the real file system, not the
        virtual state of the file system.

        Arguments:
            filename (str): The file.
            file_comparison_name (str): The comparison to perform, as in
                ``FileComparison.name``.

        Raises:
            FileNotFoundError: If the file doesn't exist in the real
                file system.
            IsADirectoryError: If the filename refers to a directory in
                the real file system.
            OSError: If some other type of OS error occurred.
        """
        if file_comparison_name == 'METADATA':
            return self._file_metadata(filename)
        elif file_comparison_name == 'HASH':
            return self._file_hash(filename)
        else:
            raise ValueError('Not a file comparison name')

    def is_cache_file(self, filename):
        """Return whether the specified file is the cache file."""
        return os.path.normcase(filename) == self._norm_cased_cache_filename

    def read(self, filename, file_comparison_name, created_files=None):
        """Return the result of the specified read operation.

        This is for ``FileBuilder``'s ``read_text``, ``read_binary``,
        and ``declare_read`` methods. This method really just returns a
        file comparison result for the file, as in
        ``file_comparison_result``, because this is how we determine
        whether the read operation is cached.

        Arguments:
            filename (str): The file.
            file_comparison_name (str): The comparison to perform, as in
                ``FileComparison.name``.
            created_files (CreatedFiles): The files to regard as
                created, if any.

        Raises:
            FileNotFoundError: If the file doesn't exist in the virtual
                state of the file system.
            IsADirectoryError: If the filename refers to a directory in
                the virtual state of the file system.
            OSError: If some other type of OS error occurred.
        """
        norm_cased_filename = os.path.normcase(filename)
        is_file_no_read = self._is_file_no_read(
            norm_cased_filename, created_files)
        if is_file_no_read is False:
            if self.is_dir(filename, created_files):
                raise IsADirectoryError(
                    'Cannot read a directory: {:s}'.format(filename))
            else:
                raise FileNotFoundError(
                    'The requested file does not exist: {:s}'.format(filename))

        try:
            result = self.file_comparison_result(
                filename, file_comparison_name)
        except FileNotFoundError:
            raise FileNotFoundError(
                'The requested file does not exist: {:s}'.format(filename))
        except IsADirectoryError:
            raise IsADirectoryError(
                'Cannot read a directory: {:s}'.format(filename))

        # The file must exist, since we didn't raise a FileNotFoundError or an
        # IsADirectoryError
        if (created_files is None or
                not created_files.has_norm_cased_file(norm_cased_filename)):
            self._build_dirs.handle_norm_cased_dir_exists(
                os.path.dirname(norm_cased_filename))

        return result

    def list_dir(self, dir_, created_files=None):
        """Return the subfiles of the specified directory.

        This has the same semantics as ``FileBuilder.list_dir``.

        Arguments:
            dir_ (str): The directory.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        self._assert_is_dir(dir_, created_files)
        subfiles = []
        for subfile in self._list_dir_superset(dir_, created_files):
            absolute_subfile = os.path.join(dir_, subfile)
            if self.exists(absolute_subfile, created_files):
                subfiles.append(subfile)
        return subfiles

    def walk(self, dir_, top_down, created_files=None):
        """Return the files in the specified directory, recursively.

        This has the same semantics as ``FileBuilder.walk``.

        Arguments:
            dir_ (str): The directory.
            top_down (bool): Whether to return the contents of each
                directory before those of its children.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        results = []
        if self.is_dir(dir_, created_files):
            self._append_walk(dir_, top_down, created_files, results)
        return results

    def is_file(self, filename, created_files=None):
        """Return whether the specified filename refers to a regular file.

        This has the same semantics as ``FileBuilder.is_file``.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        norm_cased_filename = os.path.normcase(filename)
        is_file_no_read = self._is_file_no_read(
            norm_cased_filename, created_files)
        if is_file_no_read is not None:
            return is_file_no_read
        elif os.path.isfile(norm_cased_filename):
            self._build_dirs.handle_norm_cased_dir_exists(
                os.path.dirname(norm_cased_filename))
            return True
        else:
            return False

    def is_dir(self, filename, created_files=None):
        """Return whether the specified filename refers to a directory.

        This has the same semantics as ``FileBuilder.is_dir``.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        norm_cased_dir = os.path.normcase(filename)
        if created_files is not None:
            if created_files.has_norm_cased_dir(norm_cased_dir):
                return True
            elif created_files.has_norm_cased_file(norm_cased_dir):
                return False

        if self._build_dirs.is_removed_norm_case(norm_cased_dir):
            return False
        elif os.path.isdir(norm_cased_dir):
            self._build_dirs.handle_norm_cased_dir_exists(norm_cased_dir)
            return True
        else:
            return False

    def exists(self, filename, created_files=None):
        """Return whether the specified file exists.

        This has the same semantics as ``FileBuilder.exists``.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        return (
            self.is_file(filename, created_files) or
            self.is_dir(filename, created_files))

    def get_size(self, filename, created_files=None):
        """Return the size of the specified file in bytes.

        This has the same semantics as ``FileBuilder.get_size``.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        self._assert_exists(filename, created_files)
        return os.path.getsize(filename)

    def _file_metadata(self, filename):
        """Implementation of ``file_comparison_result`` for ``'METADATA'``."""
        stats = os.stat(filename)
        if stat.S_ISDIR(stats.st_mode):
            raise IsADirectoryError()
        return {
            'size': stats.st_size,
            'timeNs': stats.st_mtime_ns,
        }

    def _file_hash(self, filename):
        """Implementation of ``file_comparison_result`` for ``'HASH'``."""
        norm_cased_filename = os.path.normcase(filename)
        is_built = self._new_cache.has_norm_cased_file(norm_cased_filename)

        # Check _hash_cache
        with self._hash_cache_lock:
            cache_entry = self._hash_cache.get(norm_cased_filename)
        if cache_entry is not None and cache_entry[1] == is_built:
            # Manually check whether the file exists, since we won't be calling
            # "open"
            if not os.path.isfile(norm_cased_filename):
                if os.path.isdir(norm_cased_filename):
                    raise IsADirectoryError()
                else:
                    raise FileNotFoundError()
            return cache_entry[0]

        digest = hashlib.sha256()
        with open(norm_cased_filename, 'rb') as file_:
            bytes_ = file_.read(1024)
            while len(bytes_) > 0:
                digest.update(bytes_)
                bytes_ = file_.read(1024)
        hash_ = digest.hexdigest()

        with self._hash_cache_lock:
            self._hash_cache[norm_cased_filename] = (hash_, is_built)
        return hash_

    def _is_file_no_read(self, norm_cased_filename, created_files):
        """Implementation of ``is_file``, but without reading.

        The implementation of ``is_file``, before we check the real file
        system. This returns ``True`` if we can determine that this is a
        regular file without checking the file system, ``False`` if we
        can determine that it is not a regular file, and ``None`` if we
        cannot determine. If this returns ``None``, then the file is a
        regular file in the virtual state of the file system if and only
        if ``os.path.isfile(norm_cased_filename)`` is ``True``.

        Arguments:
            norm_cased_filename (str): The norm-cased filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.
        """
        if created_files is not None:
            if created_files.has_norm_cased_file(norm_cased_filename):
                return True
            elif created_files.has_norm_cased_dir(norm_cased_filename):
                return False

        if norm_cased_filename == self._norm_cased_cache_filename:
            return False
        elif self._new_cache.has_norm_cased_file(norm_cased_filename):
            if (self._new_cache.get_norm_cased_file(norm_cased_filename) is
                    None):
                # We are currently building the file
                return False
        elif self._old_cache.created_norm_cased_file(norm_cased_filename):
            return False

        return None

    def _assert_is_dir(self, filename, created_files):
        """Raise an exception if the specified file is not a directory.

        Raise an exception if the specified filename does not refer to a
        directory in the virtual state of the file system.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            NotADirectoryError: If the filename refers to a regular
                file.
            OSError: If some other type of OS error occurred.
        """
        if not self.is_dir(filename, created_files):
            if self.is_file(filename, created_files):
                raise NotADirectoryError(
                    '{:s} is not a directory'.format(filename))
            else:
                raise FileNotFoundError(
                    'Directory does not exist: {:s}'.format(filename))

    def _assert_exists(self, filename, created_files):
        """Raise a ``FileNotFoundError`` if the specified file does not exist.

        Raise a ``FileNotFoundError`` if the specified file does not
        exist in the virtual state of the file system.

        Arguments:
            filename (str): The filename.
            created_files (CreatedFiles): The files to regard as
                created, if any.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            OSError: If some other type of OS error occurred.
        """
        if not self.exists(filename, created_files):
            raise FileNotFoundError(
                'File does not exist: {:s}'.format(filename))

    def _list_dir_superset(self, dir_, created_files):
        """Return a superset of ``list_dir(dir_, created_files)``.

        In order to determine the result of ``list_dir(dir_,
        created_files)``, we must check whether each file in the
        superset exists in the virtual state of the file system. This
        returns the files in a consistent order.

        Returns:
            list<str>: A superset of the subfiles.

        Raises:
            OSError: If an OS error occurred.
        """
        subfiles = os.listdir(dir_)
        if created_files is not None:
            norm_cased_subfiles = set(
                [os.path.normcase(subfile) for subfile in subfiles])
            for subfile in created_files.list_dir(dir_):
                if os.path.normcase(subfile) not in norm_cased_subfiles:
                    subfiles.append(subfile)
        return sorted(subfiles)

    def _append_walk(self, dir_, top_down, created_files, results):
        """Append the result of walking ``dir_`` to the list ``results``.

        This is equivalent to ``results.extend(walk(dir_, top_down,
        created_files))``. This assumes that ``dir_`` is a directory.
        """
        try:
            list_dir_superset = self._list_dir_superset(dir_, created_files)
        except OSError:
            list_dir_superset = []

        # Compute the subfiles and subdirectories
        subdirs = []
        subfiles = []
        for subfile in list_dir_superset:
            absolute_subfile = os.path.join(dir_, subfile)
            if self.is_file(absolute_subfile, created_files):
                subfiles.append(subfile)
            elif self.is_dir(absolute_subfile, created_files):
                subdirs.append(subfile)

        # Append the tuple and recurse
        if top_down:
            results.append((dir_, subdirs, subfiles))
        for subdir in subdirs:
            absolute_subdir = os.path.join(dir_, subdir)
            if not os.path.islink(absolute_subdir):
                self._append_walk(
                    absolute_subdir, top_down, created_files, results)
        if not top_down:
            results.append((dir_, subdirs, subfiles))
