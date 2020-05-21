import contextlib
import gzip
import json
import os
import threading
import zlib

from .file_comparison import FileComparison
from .json_util import JsonUtil
from .operation import BuildFileOperation
from .operation import ComplexOperation
from .operation import SimpleOperation
from .operation import SubbuildOperation


class Cache:
    """Stores the cached results of a build.

    This is for both finished builds and builds that are in progress.
    ``Cache`` is thread-safe. See the comments for ``FileBuilder`` and
    ``FileBuilder.build_file_with_comparison``.

    A ``Cache`` may be designated "immutable," in which case we may not
    alter its contents. Immutable caches are slightly more performant,
    because they don't have to use locks.
    """

    # In order to avoid deadlock, if multiple locks are needed, then we must
    # acquire them in the following order: _files_lock, _subbuilds_lock,
    # _created_dirs_lock.
    #
    # Private attributes:
    #
    # str _build_name - The name of the build, as in the build_name argument to
    #     FileBuilder.build.
    # set<str> _created_dirs - The non-norm-cased filenames of the directories
    #     this build has virtually created. This information need not be
    #     current; at present, FileBuilder doesn't set this until after we
    #     finish calling the function passed to build_versioned.
    # Lock _created_dirs_lock - The lock guarding access to _created_dirs. If
    #     the cache is immutable, this is contextlib.nullcontext() instead.
    # dict<str, BuildFileOperation> _files - A map containing entries for the
    #     non-norm-cased filenames of the files we have started building. For
    #     the files that we have finished building, including those that
    #     resulted in exceptions, the entries are BuildFileOperation objects
    #     indicating the results. Their is_finished fields must be True. For
    #     the files we haven't finished building, the entries are None.
    # Lock _files_lock - The lock guarding access to _files and
    #     _norm_cased_files. If the cache is immutable, this is
    #     contextlib.nullcontext() instead.
    # dict<str, object> _func_versions - The functions' versions, as in the
    #     "versions" argument to FileBuilder.build_versioned.
    # dict<str, BuildFileOperation> _norm_cased_files - Same as _files, except
    #     the keys are the norm-cased filenames.
    # dict<str, object> _operation_versions - The versions of the simple
    #     operations, as in _OPERATION_VERSIONS.
    # dict<object, SubbuildOperation> _subbuilds - A map containing entries for
    #     the cache keys of the subbuilds that we have started, as in
    #     subbuild_key. For the subbuilds that we have finished, including
    #     those that resulted in exceptions, the entries are SubbuildOperation
    #     objects indicating the results. Their is_finished fields must be
    #     True. For the subbuilds that we haven't finished, the entries are
    #     None.
    # Lock _subbuilds_lock - The lock guarding access to _subbuilds. If the
    #     cache is immutable, this is contextlib.nullcontext() instead.

    # A (sanitized) JSON object indicating the current version of the file
    # format used to store Cache objects, as in "write" and read_immutable. We
    # should change this every time we change the file format. The version also
    # incorporates the semantics of the FileBuilder class. If we change the
    # semantics, we may want to change the version, in order to invalidate old
    # cache files (or to enable us to "migrate" them).
    _CACHE_FILE_VERSION = None

    # A map from the names of simple operations, as in SimpleOperation.name, to
    # (sanitized) JSON objects indicating their versions. If a simple operation
    # doesn't have an entry, its version is None. Whenever we change the
    # interface or implementation of a simple operation, we should change its
    # version.
    _OPERATION_VERSIONS = {}

    # A string identifying this software package
    _SOFTWARE = 'file_builder'

    def __init__(
            self, build_name, files, subbuilds, created_dirs, func_versions,
            operation_versions, is_mutable):
        self._build_name = build_name
        self._files = files
        self._subbuilds = subbuilds
        self._created_dirs = created_dirs
        self._func_versions = func_versions
        self._operation_versions = operation_versions

        if is_mutable:
            self._files_lock = threading.Lock()
            self._subbuilds_lock = threading.Lock()
            self._created_dirs_lock = threading.Lock()
        else:
            null_context = contextlib.nullcontext()
            self._files_lock = null_context
            self._subbuilds_lock = null_context
            self._created_dirs_lock = null_context

        self._norm_cased_files = {}
        for filename, operation in files.items():
            self._norm_cased_files[os.path.normcase(filename)] = operation

    @staticmethod
    def create_empty_mutable(build_name, func_versions):
        """Return a new empty mutable ``Cache`` object.

        Arguments:
            build_name (str): The name of the build whose results we are
                caching, as in the ``build_name`` argument to
                ``FileBuilder.build``.
            func_versions (dict<str, object>): The functions' versions,
                as in the ``versions`` argument to
                ``FileBuilder.build_versioned``.
        """
        return Cache._create_empty(build_name, func_versions, True)

    @staticmethod
    def create_empty_immutable(build_name, func_versions):
        """Return a new empty immutable ``Cache`` object.

        Arguments:
            build_name (str): The name of the build whose results we are
                caching, as in the ``build_name`` argument to
                ``FileBuilder.build``.
            func_versions (dict<str, object>): The functions' versions,
                as in the ``versions`` argument to
                ``FileBuilder.build_versioned``.
        """
        return Cache._create_empty(build_name, func_versions, False)

    @staticmethod
    def subbuild_key(operation):
        """Return the cache key for the specified ``SubbuildOperation``.

        The cache key is an object that uniquely identifies the
        operation's function name and arguments.
        """
        return JsonUtil.to_hashable([
            operation.func_name, operation.args, operation.kwargs])

    def build_name(self):
        return self._build_name

    def get_file(self, filename):
        """Return the operation associated with the specified file.

        Return the ``BuildFileOperation`` entry associated with the
        specified non-norm-cased filename. Return ``None`` if we haven't
        started or finished building the file (but not if the build
        function raised an exception).
        """
        with self._files_lock:
            return self._files.get(filename)

    def get_norm_cased_file(self, norm_cased_filename):
        """Return the operation associated with the specified file.

        Return the ``BuildFileOperation`` entry associated with the
        specified norm-cased filename. Return ``None`` if we haven't
        started or finished building the file (but not if the build
        function raised an exception).
        """
        with self._files_lock:
            return self._norm_cased_files.get(norm_cased_filename)

    def start_building_file(self, filename):
        """Record that we are about to build the specified file.

        This does not apply if we are simply reusing a previously cached
        result.

        Arguments:
            filename (str): The non-norm-cased filename.

        Raises:
            RuntimeError: If we already started building the file (e.g.
                in another thread).
        """
        norm_cased_filename = os.path.normcase(filename)
        with self._files_lock:
            self._assert_doesnt_have_norm_cased_file(
                norm_cased_filename, filename)
            self._files[filename] = None
            self._norm_cased_files[norm_cased_filename] = None

    def finish_building_file(self, operation):
        """Record the result of building the specified file.

        This includes the case where the function passed to
        ``FileBuilder.build_file_with_comparison`` raised an exception.
        It does not include the case where we simply reuse a previously
        cached result.

        Arguments:
            operation (BuildFileOperation): The result. The
                ``is_finished`` field must be ``True``, and the
                ``setup_failed`` field must be ``False``.
        """
        with self._files_lock:
            self._files[operation.filename] = operation
            self._norm_cased_files[os.path.normcase(operation.filename)] = (
                operation)

    def has_norm_cased_file(self, norm_cased_filename):
        """Return whether we have a cache entry for the specified filename.

        This returns ``True`` if we have started building the file, but
        haven't finished.

        Arguments:
            norm_cased_filename (str): The norm-cased filename.
        """
        with self._files_lock:
            return norm_cased_filename in self._norm_cased_files

    def created_file(self, filename):
        """Return whether we created the specified non-norm-cased file.

        This does not include cases where we called
        ``FileBuilder.build_file_with_comparison`` on the file, but the
        build function raised an exception.
        """
        with self._files_lock:
            operation = self._files.get(filename)
        return operation is not None and not operation.raised

    def created_norm_cased_file(self, norm_cased_filename):
        """Return whether we created the specified norm-cased file.

        This does not include cases where we called
        ``FileBuilder.build_file_with_comparison`` on the file, but the
        build function raised an exception.
        """
        with self._files_lock:
            operation = self._norm_cased_files.get(norm_cased_filename)
        return operation is not None and not operation.raised

    def assert_doesnt_have_norm_cased_file(
            self, norm_cased_filename, filename):
        """Raise if we have a cache entry for the specified filename.

        This raises if we have started building the file, but we haven't
        finished. It also raises if we started building a file that has
        a different filename, but the same norm-cased filename.

        Arguments:
            norm_cased_filename (str): The norm-cased filename.
            filename (str): The non-norm-cased filename.
        """
        with self._files_lock:
            self._assert_doesnt_have_norm_cased_file(
                norm_cased_filename, filename)

    def created_files(self):
        """Return the build files we have created.

        This is a list of the non-norm-cased filenames of all of the
        files that we have finished building that didn't result in an
        exception.
        """
        created_files = []
        with self._files_lock:
            for filename, operation in self._files.items():
                if operation is not None and not operation.raised:
                    created_files.append(filename)
        return created_files

    def get_subbuild(self, subbuild_key):
        """Return the operation associated with the specified subbuild key.

        Return the ``SubbuildOperation`` entry associated with the
        specified key, as in ``Cache.subbuild_key``. Return ``None`` if
        we haven't started or finished such a subbuild (but not if the
        subbuild function raised an exception).
        """
        with self._subbuilds_lock:
            return self._subbuilds.get(subbuild_key)

    def start_subbuild(self, subbuild_key, operation):
        """Record that we are about to perform the specified subbuild.

        This does not apply if we are simply reusing a previously cached
        result.

        Arguments:
            subbuild_key: The subbuild key, i.e. the return value of
                ``Cache.subbuild_key(operation)``.
            operation (SubbuildOperation): The operation we are
                starting. We only use this for any error messages. This
                may not be modified in another thread until after the
                call to ``start_subbuild`` has finished.

        Raises:
            RuntimeError: If we already started a subbuild with the same
                function name and arguments (e.g. in another thread).
        """
        with self._subbuilds_lock:
            self._assert_doesnt_have_subbuild(subbuild_key, operation)
            self._subbuilds[subbuild_key] = None

    def finish_subbuild(self, subbuild_key, operation):
        """Record the result of executing the specified subbuild.

        This includes the case where the function passed to
        ``FileBuilder.subbuild`` raised an exception. It does not
        include the case where we simply reuse a cached result.

        Arguments:
            subbuild_key: The subbuild key, i.e. the return value of
                ``Cache.subbuild_key(operation)``.
            operation (SubbuildOperation): The result. The
                ``is_finished`` field must be ``True``, and the
                ``setup_failed`` field must be ``False``.
        """
        with self._subbuilds_lock:
            self._subbuilds[subbuild_key] = operation

    def has_subbuild(self, subbuild_key):
        """Return whether we have a cache entry for the specified subbuild key.

        This returns ``True`` if we have started such a subbuild, but
        haven't finished.

        Arguments:
            subbuild_key: The subbuild key, as in
                ``Cache.subbuild_key``.
        """
        with self._subbuilds_lock:
            return subbuild_key in self._subbuilds

    def assert_doesnt_have_subbuild(self, subbuild_key, operation):
        """Raise if we have a cache entry for the specified subbuild key.

        This raises if we have started such a subbuild, but we haven't
        finished.

        Arguments:
            subbuild_key: The subbuild key, i.e. the return value of
                ``Cache.subbuild_key(operation)``.
            operation (SubbuildOperation): The operation to check. We
                only use this for any error messages. This may not be
                modified in another thread until after the call to
                ``assert_doesnt_have_subbuild`` has finished.
        """
        with self._subbuilds_lock:
            self._assert_doesnt_have_subbuild(subbuild_key, operation)

    def use_cached_operation(self, operation):
        """Reuse previously cached results for an operation tree.

        This stores cache entries for both ``operation`` and the
        operations in the ``operation.suboperations`` tree, excluding
        those whose ``setup_failed`` fields are ``False``.

        Arguments:
            operation (ComplexOperation): The operation. The
                ``is_finished`` field must be ``True``.

        Raises:
            RuntimeError: If we already performed one of the build file
                or subbuild operations in the operation tree (e.g. in
                another thread).
        """
        with self._files_lock, self._subbuilds_lock:
            self._assert_no_repeats(operation)
            self._use_cached_operation(operation)

    def add_created_dirs(self, created_dirs):
        """Record the virtual creation of the specified directories.

        Record that we virtually created the directories with the
        specified non-norm-cased filenames during this build.

        Arguments:
            created_dirs (list<str>): The directories.
        """
        with self._created_dirs_lock:
            self._created_dirs.update(created_dirs)

    def created_dirs(self):
        """Return a list of the directories we virtually created.

        Return a list of the non-norm-cased filenames of the directories
        we virtually created during this build. This information need
        not be current; at present, ``FileBuilder`` doesn't record the
        created directories until after we finish calling the function
        passed to ``build_versioned``.
        """
        with self._created_dirs_lock:
            return list(self._created_dirs)

    def get_func_version(self, func_name):
        """Return the version associated with the specified function name.

        Return the version associated with the specified function name,
        as in the ``versions`` argument to
        ``FileBuilder.build_versioned``.
        """
        return self._func_versions.get(func_name)

    def get_operation_version(self, operation_name):
        """Return the version associated with the specified simple operation.

        This is a sanitized JSON object. Whenever we change a simple
        operation's interface or implementation, we change its version.

        Arguments:
            operation_name (str): The operation name, as in
                ``SimpleOperation.name``.
        """
        return self._operation_versions.get(operation_name)

    def write(self, filename):
        """Write the contents of this ``Cache`` object to the specified file.

        We may subsequently read the cache using ``read_immutable``.
        This method assumes that no file building or subbuilds are still
        in progress.
        """
        with self._files_lock, self._subbuilds_lock, self._created_dirs_lock:
            operations = (
                list(self._files.values()) + list(self._subbuilds.values()))
            created_dirs = list(self._created_dirs)

        non_root_operations = set()
        for operation in operations:
            non_root_operations.update(operation.suboperations)
        root_operations_json = []
        for operation in operations:
            if operation not in non_root_operations:
                root_operations_json.append(self._operation_to_json(operation))

        cache_json = {
            'buildName': self._build_name,
            'cacheFileVersion': Cache._CACHE_FILE_VERSION,
            'createdDirs': created_dirs,
            'funcVersions': self._func_versions,
            'operationVersions': self._operation_versions,
            'rootOperations': root_operations_json,
            'software': Cache._SOFTWARE,
        }

        with gzip.open(filename, 'wt') as file_:
            # Sort keys in order to improve compression
            file_.write(
                json.dumps(cache_json, separators=(',', ':'), sort_keys=True))

    @staticmethod
    def read_immutable(filename):
        """Return the ``Cache`` object stored in the specified file.

        This should have been written using ``write``. The returned
        ``Cache`` object is immutable.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            IsADirectoryError: If the filename refers to a directory.
            OSError: If some other type of OS error occurred.
            RuntimeError: If there was an error parsing (or reading) the
                file. Parse errors are emitted on a best-effort basis.
                That is, it is possible that we will not raise even if
                the file is invalid, resulting in a broken ``Cache``
                object.
        """
        if not os.path.isfile(filename):
            if os.path.isdir(filename):
                raise IsADirectoryError(
                    'Cannot read a directory: {:s}'.format(filename))
            else:
                raise FileNotFoundError(
                    'The requested file does not exist: {:s}'.format(filename))

        try:
            with gzip.open(filename, 'rt') as file_:
                cache_json = json.load(file_)
        except (EOFError, OSError, ValueError, zlib.error):
            raise RuntimeError(
                'Error reading or parsing cache file {:s}'.format(filename))

        # A primitive attempt to check that the Cache class created the file.
        # This check is in lieu of checking all of the data types of everything
        # in cache_json and what not.
        if (not isinstance(cache_json, dict) or
                cache_json.get('software') != Cache._SOFTWARE):
            raise RuntimeError(
                'Error parsing cache file {:s}'.format(filename))

        if not JsonUtil.is_equal(
                cache_json['cacheFileVersion'], Cache._CACHE_FILE_VERSION):
            raise RuntimeError(
                'Error parsing cache file {:s}. This cache file was created '
                'with a newer version of the file_builder library. Try '
                'upgrading.'.format(filename))

        files = {}
        subbuilds = {}
        Cache._operations_from_json(
            cache_json['rootOperations'], files, subbuilds)
        return Cache(
            cache_json['buildName'], files, subbuilds,
            set(cache_json['createdDirs']), cache_json['funcVersions'],
            cache_json['operationVersions'], False)

    @staticmethod
    def _create_empty(build_name, func_versions, is_mutable):
        """Return a new empty ``Cache`` object.

        Arguments:
            build_name (str): The name of the build whose results we are
                caching, as in the ``build_name`` argument to
                ``FileBuilder.build``.
            func_versions (dict<str, object>): The functions' versions,
                as in the ``versions`` argument to
                ``FileBuilder.build_versioned``.
            is_mutable (bool): Whether the ``Cache`` object is mutable.
        """
        return Cache(
            build_name, {}, {}, set(), func_versions,
            Cache._OPERATION_VERSIONS, is_mutable)

    def _assert_doesnt_have_norm_cased_file(
            self, norm_cased_filename, filename):
        """Implementation of ``assert_doesnt_have_norm_cased_file``.

        The only difference is that
        ``assert_doesnt_have_norm_cased_file`` acquires ``_files_lock``
        first.
        """
        if norm_cased_filename in self._norm_cased_files:
            raise RuntimeError(
                'Building the same file twice is not allowed: {:s}'.format(
                    filename))

    def _assert_doesnt_have_subbuild(self, subbuild_key, operation):
        """Implementation of ``assert_doesnt_have_subbuild``.

        The only difference is that ``assert_doesnt_have_subbuild``
        acquires ``_subbuilds_lock`` first.
        """
        if subbuild_key in self._subbuilds:
            raise RuntimeError(
                'Calling the same subbuild function twice with the same '
                'arguments is not allowed. {:s} was called twice with args = '
                '{:s}, kwargs = {:s}.'.format(
                    operation.func_name, json.dumps(operation.args),
                    json.dumps(operation.kwargs)))

    def _assert_no_repeats(self, operation):
        """Assert that the specified operation tree contains no repeats.

        Raise a ``RuntimeError`` if we already performed the build file
        or subbuild operation ``operation`` or one of the build file or
        subbuild operations in the ``operation.suboperations`` tree. We
        ignore operations whose ``setup_failed`` fields are ``False``.

        Arguments:
            operation (ComplexOperation): The operation.
        """
        if not operation.setup_failed:
            if isinstance(operation, BuildFileOperation):
                self._assert_doesnt_have_norm_cased_file(
                    os.path.normcase(operation.filename), operation.filename)
            elif isinstance(operation, SubbuildOperation):
                subbuild_key = Cache.subbuild_key(operation)
                self._assert_doesnt_have_subbuild(subbuild_key, operation)
            else:
                raise RuntimeError('Unhandled operation type')

        for suboperation in operation.suboperations:
            if isinstance(suboperation, ComplexOperation):
                self._assert_no_repeats(suboperation)

    def _use_cached_operation(self, operation):
        """Implementation of ``use_cached_operation``.

        The difference is that ``use_cached_operation`` acquires locks
        and calls ``_assert_no_repeats`` first.
        """
        if not operation.setup_failed:
            if isinstance(operation, BuildFileOperation):
                self._files[operation.filename] = operation
                self._norm_cased_files[
                    os.path.normcase(operation.filename)] = operation
            elif isinstance(operation, SubbuildOperation):
                subbuild_key = Cache.subbuild_key(operation)
                self._subbuilds[subbuild_key] = operation
            else:
                raise RuntimeError('Unhandled operation type')

        for suboperation in operation.suboperations:
            if isinstance(suboperation, ComplexOperation):
                self._use_cached_operation(suboperation)

    def _simple_operation_to_json(self, operation):
        """Return the JSON representation of the specified ``SimpleOperation``.

        Return the JSON value representation that ``write`` uses to
        store the specified ``SimpleOperation``.
        """
        operation_json = {
            'args': operation.args,
            'returnValue': operation.return_value,
            'type': operation.name,
        }
        if operation.exception_type_str is not None:
            operation_json['exceptionType'] = operation.exception_type_str
        return operation_json

    def _complex_operation_to_json(self, operation):
        """Return the JSON representation of the given ``ComplexOperation``.

        Return the JSON value representation that ``write`` uses to
        store the specified ``ComplexOperation``.
        """
        suboperations_json = []
        for suboperation in operation.suboperations:
            suboperations_json.append(self._operation_to_json(suboperation))
        operation_json = {
            'args': operation.args,
            'funcName': operation.func_name,
            'kwargs': operation.kwargs,
            'returnValue': operation.return_value,
            'suboperations': suboperations_json,
        }
        if operation.raised:
            operation_json['raised'] = True
        if operation.setup_failed:
            operation_json['setupFailed'] = True

        if isinstance(operation, BuildFileOperation):
            operation_json['type'] = 'build_file'
            operation_json['filename'] = operation.filename
            operation_json['fileComparison'] = operation.file_comparison.name
            operation_json['fileComparisonResult'] = (
                operation.file_comparison_result)
        elif isinstance(operation, SubbuildOperation):
            operation_json['type'] = 'subbuild'
        else:
            raise RuntimeError('Unhandled operation type')
        return operation_json

    def _operation_to_json(self, operation):
        """Return the JSON representation of the specified ``Operation``.

        Return the JSON value representation that ``write`` uses to
        store the specified ``Operation``. This is the inverse of
        ``_operation_from_json``.
        """
        if isinstance(operation, SimpleOperation):
            return self._simple_operation_to_json(operation)
        elif isinstance(operation, ComplexOperation):
            return self._complex_operation_to_json(operation)
        else:
            raise RuntimeError('Unhandled operation type')

    @staticmethod
    def _operation_from_json(operation_json, files, subbuilds):
        """Return the ``Operation`` represented by the specified JSON value.

        This is the inverse of ``_operation_to_json``.

        Arguments:
            operation_json: The JSON value.
            files (dict<str, BuildFileOperation>): A map to which to add
                mappings from the filenames of the
                ``BuildFileOperations`` among the operation and its
                suboperation tree to the ``BuildFileOperations``. We
                only include ``BuildFileOperations`` whose
                ``setup_failed`` fields are ``False``.
            subbuilds (dict<object, SubbuildOperation>): A map to which
                to add mappings from the subbuild keys (as in
                ``subbuild_key``) of the ``SubbuildOperations`` among
                the operation and its suboperation tree to the
                ``SubbuildOperations``. We only include
                ``SubbuildOperations`` whose ``setup_failed`` fields are
                ``False``.
        """
        type_ = operation_json['type']
        if type_ == 'build_file':
            filename = operation_json['filename']
            operation = BuildFileOperation(
                filename, FileComparison[operation_json['fileComparison']],
                operation_json['funcName'], operation_json['args'],
                operation_json['kwargs'],
                Cache._operations_from_json(
                    operation_json['suboperations'], files, subbuilds),
                operation_json['returnValue'],
                operation_json['fileComparisonResult'],
                operation_json.get('raised', False),
                operation_json.get('setupFailed', False), True)

            if not operation.setup_failed:
                files[operation.filename] = operation
            return operation
        elif type_ == 'subbuild':
            operation = SubbuildOperation(
                operation_json['funcName'], operation_json['args'],
                operation_json['kwargs'],
                Cache._operations_from_json(
                    operation_json['suboperations'], files, subbuilds),
                operation_json['returnValue'],
                operation_json.get('raised', False),
                operation_json.get('setupFailed', False), True)

            if not operation.setup_failed:
                subbuild_key = Cache.subbuild_key(operation)
                subbuilds[subbuild_key] = operation
            return operation
        else:
            return SimpleOperation(
                type_, operation_json['args'], operation_json['returnValue'],
                operation_json.get('exceptionType'), True)

    @staticmethod
    def _operations_from_json(operations_json, files, subbuilds):
        """Equivalent implementation is contractually guaranteed."""
        operations = []
        for operation_json in operations_json:
            operations.append(
                Cache._operation_from_json(operation_json, files, subbuilds))
        return operations
