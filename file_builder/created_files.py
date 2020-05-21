import os


class CreatedFiles:
    """Represents the files created during a portion of a build process.

    Represents the files created during a portion of a build process,
    along with all of their parent directories. See the comments for
    ``FileBuilder`` and ``FileBuilder.build_file_with_comparison``.

    We use this when checking whether we can reuse a cached result.
    ``SimpleOperationExecutor`` methods act as though the files
    indicated by the ``CreatedFiles`` objects passed in as arguments
    exist in the virtual state of the file system. So we use
    ``CreatedFiles`` to indicate what files were created from the
    beginning of the cache entry we are checking to the current point in
    that entry.

    ``CreatedFiles`` is not thread-safe. There's no need, because we
    only ever use a given ``CreatedFiles`` instance in a single thread.
    """

    # Private attributes:
    #
    # dict<str, int> _norm_cased_dir_to_started_count - A map from the
    #     immediate parent directory of each file we have started building and
    #     have not finished with an exception to the number of such regular
    #     files that are immediate children of those directories. This does not
    #     include mappings to 0.
    # dict<str, dict<str, str>> _norm_cased_dir_to_subfiles - A map of the
    #     "created" subfiles of each directory. For each non-norm-cased
    #     filename X for an element in _norm_cased_files or _norm_cased_dirs,
    #     apart from root directories,
    #     _norm_cased_dir_to_subfiles[os.path.normcase(os.path.dirname(X))]
    #     contains a mapping from os.path.normcase(os.path.basename(X)) to
    #     os.path.basename(X). This does not include empty dictionaries.
    # set<str> _norm_cased_dirs - The norm-cased filenames of the "created"
    #     directories. This contains all of the parents of all of the files we
    #     started creating which haven't resulted in an error.
    # set<str> _norm_cased_files - A set of the norm-cased filenames of the
    #     regular files we have created.

    def __init__(self):
        """Initialize a new empty ``CreatedFiles`` object."""
        self._norm_cased_files = set()
        self._norm_cased_dirs = set()
        self._norm_cased_dir_to_subfiles = {}
        self._norm_cased_dir_to_started_count = {}

    def started_building_file(self, filename):
        """Update this for starting a build file operation.

        Arguments:
            filename (str): The non-norm-cased filename of the output
                file.
        """
        parent = os.path.dirname(filename)
        norm_cased_parent = os.path.normcase(parent)
        self._norm_cased_dir_to_started_count[norm_cased_parent] = (
            self._norm_cased_dir_to_started_count.get(norm_cased_parent, 0) +
            1)
        while norm_cased_parent not in self._norm_cased_dirs:
            self._norm_cased_dirs.add(norm_cased_parent)
            self._add_to_subfiles(parent)
            parent = os.path.dirname(parent)
            norm_cased_parent = os.path.normcase(parent)

    def finished_building_file(self, filename):
        """Update this for successfully finishing a build file operation.

        This does not include cases where there was an exception when
        building the file.

        Arguments:
            filename (str): The filename of the output file.
        """
        self._norm_cased_files.add(os.path.normcase(filename))
        self._add_to_subfiles(filename)

    def error_building_file(self, filename):
        """Update this for an exception raised from a build file operation.

        Arguments:
            filename (str): The filename of the output file.
        """
        parent = os.path.normcase(os.path.dirname(filename))
        count = self._norm_cased_dir_to_started_count[parent] - 1
        if count > 0:
            self._norm_cased_dir_to_started_count[parent] = count
            return

        self._norm_cased_dir_to_started_count.pop(parent)
        self._norm_cased_dirs.remove(parent)
        while self._remove_from_subfiles(parent):
            parent = os.path.dirname(parent)
            self._norm_cased_dirs.remove(parent)

    def has_norm_cased_file(self, norm_cased_filename):
        """Return whether we created a regular file with the given filename.

        Arguments:
            norm_cased_filename (str): The norm-cased filename.
        """
        return norm_cased_filename in self._norm_cased_files

    def has_norm_cased_dir(self, norm_cased_dir):
        """Return whether we created a directory with the specified filename.

        We say that when we build a file, we create all of the parent
        directories, even if they already existed in the real or virtual
        file system.

        Arguments:
            norm_cased_dir (str): The norm-cased filename.
        """
        return norm_cased_dir in self._norm_cased_dirs

    def list_dir(self, dir_):
        """Return the subfiles of the specified directory that we have created.

        Return a list of the non-norm-cased names of the immediate
        children of the the specified directory that we have created. We
        say that when we build a file, we create all of the parent
        directories, even if they already existed in the real or virtual
        file system.

        If we have not created ``dir_`` or we created it as a regular
        file, this returns ``[]``. The names only contain the final
        components of each path, e.g. ``'bar'`` and not ``'/foo/bar'``.
        The return value does not include special entries like ``'.'``
        and ``'..'``.
        """
        subfiles = self._norm_cased_dir_to_subfiles.get(os.path.normcase(dir_))
        if subfiles is not None:
            return list(subfiles.values())
        else:
            return []

    def _add_to_subfiles(self, filename):
        """Add the specified file to ``_norm_cased_dir_to_subfiles``.

        That is, this adds an entry for ``os.path.basename(filename)``
        to the ``_norm_cased_dir_to_subfiles`` entry for
        ``os.path.normcase(os.path.dirname(filename))``. This has no
        effect if the file is already present or it is a root directory.

        Arguments:
            filename (str): The non-norm-cased filename.
        """
        dir_name, base_name = os.path.split(filename)
        if dir_name != filename:
            subfiles = self._norm_cased_dir_to_subfiles.setdefault(
                os.path.normcase(dir_name), {})
            norm_cased_base_name = os.path.normcase(base_name)
            if norm_cased_base_name not in subfiles:
                subfiles[norm_cased_base_name] = base_name

    def _remove_from_subfiles(self, norm_cased_filename):
        """Remove the specified file from ``_norm_cased_dir_to_subfiles``.

        That is, this removes the entry for
        ``os.path.basename(norm_cased_filename)`` from the
        ``_norm_cased_dir_to_subfiles`` entry for
        ``os.path.dirname(norm_cased_filename)``. This assumes that
        either the file is present in ``_norm_cased_dir_to_subfiles`` or
        it is a root directory.

        Arguments:
            norm_cased_filename (str): The norm-cased filename.

        Returns:
            bool: Whether this resulted in removing the entry for
                ``os.path.dirname(norm_cased_filename)``, due to that
                directory having no other created subfiles. This returns
                ``False`` if ``norm_cased_filename`` is a root
                directory.
        """
        norm_cased_dir_name, norm_cased_base_name = os.path.split(
            norm_cased_filename)
        if norm_cased_dir_name == norm_cased_filename:
            return False
        subfiles = self._norm_cased_dir_to_subfiles[norm_cased_dir_name]
        subfiles.pop(norm_cased_base_name)
        if subfiles:
            return False
        else:
            self._norm_cased_dir_to_subfiles.pop(norm_cased_dir_name)
            return True
