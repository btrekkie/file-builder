import os
import threading


class BuildDirs:
    """Keeps track of the directories for a particular ``FileBuilder`` build.

    Specifically, this keeps track of which directories were created or
    removed in the virtual state of the file system. We must keep
    ``BuildDirs`` updated by calling ``started_building_file``,
    ``error_building_file``, and ``handle_norm_cased_dir_exists`` as
    appropriate. ``BuildDirs`` is thread-safe. See the comments for
    ``FileBuilder`` and ``FileBuilder.build_file_with_comparison``.
    """

    # Private attributes:
    #
    # dict<str, int> _build_dir_counts - A map from the norm-cased filename of
    #     each directory reserved for at least one descendant build file in the
    #     current build to the number of different directories or files that
    #     are direct children that are reserved for this purpose. For example,
    #     say we are currently building '/foo/bar/a.txt', we finished building
    #     '/foo/b.txt' and '/foo/bar/c.txt', and there was an error building
    #     '/foo/d.txt'. Then _build_dir_counts would have a mapping from '/foo'
    #     to 2. There are two reservations for that folder: one for '/foo/bar'
    #     (even though it contains two build files) and one for '/foo/b.txt'.
    #     There is no reservation for '/foo/d.txt', because an exception was
    #     raised while building it.
    # dict<str, str> _created_dirs_map - A map from the norm-cased filename of
    #     each directory that the current build virtually created and didn't
    #     subsequently virtually remove to the corresponding non-norm-cased
    #     filename.
    # set<str> _error_created_dirs - The norm-cased filenames of the
    #     directories that the current build virtually created, subsequently
    #     virtually removed due to an exception while building a file, and
    #     didn't subsequently virtually recreate.
    # set<str> _exists_dirs - The norm-cased filenames of directories we know
    #     to exist in the virtual state of the file system, assuming no
    #     external changes to the file system, due to calls to
    #     _handle_dir_exists. This is structured so that if X is in
    #     _exists_dirs, then so is os.path.dirname(X). No file in _exists_dirs
    #     is also present in _removed_tree. This field is used to optimize the
    #     implementation of _handle_dir_exists, so that it doesn't have to walk
    #     all the way up to the root directory every time.
    # Lock _lock - The lock guarding access to all of the other attributes.
    # set<str> _maybe_removed_dirs - The norm-cased filenames of directories
    #     that might be removed in the virtual state of the file system. To be
    #     sure, we need to check whether the directory is a key in
    #     _build_dir_counts, and we need to check all of its contents to see if
    #     it contains any files or directories not in _maybe_removed_dirs,
    #     _removed_dirs, or _removed_files. Such files or directories would
    #     have been created between builds or during the current build by an
    #     external program. For performance reasons, we defer the directory
    #     scan check until it becomes necessary. It is crucial that we leave a
    #     maybe-removed directory in this set as long as it is a key in
    #     _build_dir_counts, in case future exceptions while building a file
    #     result in removing the directory from _build_dir_counts.
    # set<str> _removed_dirs - The norm-cased filenames of directories that are
    #     removed in the virtual state of the file system, provided they are
    #     not keys in _build_dir_counts. An item in _maybe_removed_dirs
    #     graduates to _removed_dirs if we confirm it has been removed. It is
    #     crucial that we leave a removed directory in this set as long as it
    #     is a key in _build_dir_counts, in case future exceptions while
    #     building a file result in removing the directory from
    #     _build_dir_counts.
    # set<str> _removed_files - The norm-cased filenames of the files from the
    #     previous build that are removed in the virtual state of the file
    #     system, but might still be present.

    def __init__(self, old_cache_dirs, old_cache_files):
        """Initialize a new ``BuildDirs`` object.

        Arguments:
            old_cache_dirs (list<str>): The directories created during
                the previous build.
            old_cache_files (list<str>): The files created during the
                previous build, including the cache file.
        """
        self._build_dir_counts = {}
        self._created_dirs_map = {}
        self._error_created_dirs = set()
        self._removed_dirs = set()
        self._exists_dirs = set()
        self._lock = threading.Lock()

        self._maybe_removed_dirs = set(
            [os.path.normcase(dir_) for dir_ in old_cache_dirs])
        self._removed_files = set(
            [os.path.normcase(filename) for filename in old_cache_files])

    def is_removed_norm_case(self, norm_cased_dir):
        """Return whether the specified directory was removed.

        Return whether the specified norm-cased filename refers to a
        directory that was created during the previous build or the
        current build and is not present in the virtual state of the
        file system.
        """
        with self._lock:
            if norm_cased_dir in self._build_dir_counts:
                return False
            elif norm_cased_dir in self._removed_dirs:
                return True
            elif norm_cased_dir not in self._maybe_removed_dirs:
                return False
            else:
                return self._check_maybe_removed_dir(norm_cased_dir)

    def handle_norm_cased_dir_exists(self, norm_cased_dir):
        """Respond to the existence of the specified norm-cased directory.

        Respond to the existence of the specified norm-cased directory
        in the virtual state of the file system, excluding files created
        in the relevant instance of ``CreatedFiles``.
        ``SimpleOperationExecutor`` should call this whenever it becomes
        aware of such a directory.
        """
        with self._lock:
            self._handle_dir_exists(norm_cased_dir)

    def started_building_file(self, filename, created_dirs):
        """Handle starting to build a file.

        This includes the case where we simply reuse a cached result.

        Arguments:
            filename (str): The non-norm-cased filename.
            created_dirs (list<str>): The non-norm-cased parent
                directories of ``filename`` that we virtually created.

        Returns:
            list<str>: The elements of ``created_dirs`` that we
                virtually created in this thread. Multiple threads might
                all think they created a given directory X, in which
                case ``BuildDirs`` will arbitrate and select one thread
                as the one that we say really created X.
        """
        created_dirs_set = set(created_dirs)
        locked_created_dirs = []
        prev_parent = filename
        parent = os.path.dirname(prev_parent)
        with self._lock:
            self._removed_files.discard(os.path.normcase(filename))
            while parent != prev_parent:
                norm_cased_parent = os.path.normcase(parent)
                count = self._build_dir_counts.get(norm_cased_parent, 0)
                self._build_dir_counts[norm_cased_parent] = count + 1
                if count > 0:
                    break
                if parent in created_dirs_set:
                    self._created_dirs_map[norm_cased_parent] = parent
                    self._error_created_dirs.discard(norm_cased_parent)
                    self._removed_files.discard(norm_cased_parent)
                    locked_created_dirs.append(parent)

                prev_parent = parent
                parent = os.path.dirname(parent)
        return locked_created_dirs

    def error_building_file(self, filename):
        """Handle an exception building the specified file."""
        prev_parent = os.path.normcase(filename)
        parent = os.path.dirname(prev_parent)
        with self._lock:
            while parent != prev_parent:
                count = self._build_dir_counts[parent] - 1
                if count > 0:
                    self._build_dir_counts[parent] = count
                    break
                self._build_dir_counts.pop(parent)
                if self._created_dirs_map.pop(parent, None) is not None:
                    self._error_created_dirs.add(parent)
                    self._maybe_removed_dirs.add(parent)

                    # We can't simply remove "parent" from _exists_dirs,
                    # because that could break the invariant that if X is in
                    # _exists_dirs, then so is os.path.dirname(X)
                    self._exists_dirs.clear()

                prev_parent = parent
                parent = os.path.dirname(parent)

    def created_dirs(self):
        """Return the directories virtually created during the current build.

        Return a list of the non-norm-cased filenames of the directories
        that were virtually created during the current build.
        """
        with self._lock:
            return list(self._created_dirs_map.values())

    def norm_cased_error_created_dirs(self):
        """Return the norm-cased filenames of the error directories.

        Return a list of the norm-cased filenames of the directories
        that the current build virtually created, subsequently virtually
        removed due to an exception while building a file, and didn't
        subsequently virtually recreate.
        """
        with self._lock:
            return list(self._error_created_dirs)

    def _handle_dir_exists(self, norm_cased_dir):
        """Implementation of ``handle_norm_cased_dir_exists``.

        The only difference is that ``handle_norm_cased_dir_exists``
        acquires ``_lock`` first.
        """
        parent = norm_cased_dir
        while (parent not in self._exists_dirs and
                parent not in self._build_dir_counts):
            self._removed_dirs.discard(parent)
            self._maybe_removed_dirs.discard(parent)
            self._removed_files.discard(parent)
            self._exists_dirs.add(parent)
            parent = os.path.dirname(parent)

        while parent not in self._exists_dirs:
            self._exists_dirs.add(parent)
            parent = os.path.dirname(parent)

    def _check_maybe_removed_dir(self, norm_cased_dir):
        """Check whether the specified directory is really removed.

        Scan the files and directories in the specified norm-cased
        directory that is in ``_maybe_removed_dirs`` to determine
        whether it is present in the virtual file system. Return
        ``True`` if it is not present and ``False`` if it is present.
        Assume it is not a key in ``_build_dir_counts``. See the
        comments for the ``_maybe_removed_dirs`` field.
        """
        self._maybe_removed_dirs.remove(norm_cased_dir)

        try:
            subfiles = os.listdir(norm_cased_dir)
        except FileNotFoundError:
            # The directory doesn't exist in the real file system, so it
            # doesn't exist in the virtual file system either
            self._removed_dirs.add(norm_cased_dir)
            return True
        except NotADirectoryError:
            # The directory was externally removed and a file created in its
            # place
            self._handle_dir_exists(os.path.dirname(norm_cased_dir))
            return False

        for subfile in subfiles:
            absolute_subfile = os.path.join(
                norm_cased_dir, os.path.normcase(subfile))
            if absolute_subfile in self._removed_dirs:
                if os.path.isfile(absolute_subfile):
                    # The directory was externally removed and a file
                    # created in its place
                    self._handle_dir_exists(norm_cased_dir)
                    return False
            elif absolute_subfile in self._removed_files:
                if os.path.isdir(absolute_subfile):
                    # The file was externally removed and a directory
                    # created in its place
                    self._handle_dir_exists(absolute_subfile)
                    return False
            elif absolute_subfile in self._maybe_removed_dirs:
                if not self._check_maybe_removed_dir(absolute_subfile):
                    return False
            else:
                if os.path.isdir(absolute_subfile):
                    self._handle_dir_exists(absolute_subfile)
                else:
                    self._handle_dir_exists(norm_cased_dir)
                return False

        self._removed_dirs.add(norm_cased_dir)
        return True
