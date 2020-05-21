import copy
import logging
import os
from pathlib import Path
import threading

from .build_dirs import BuildDirs
from .cache import Cache
from .created_files import CreatedFiles
from .file_backups import FileBackups
from .file_comparison import FileComparison
from .json_util import JsonUtil
from .operation import BuildFileOperation
from .operation import ComplexOperation
from .operation import SimpleOperation
from .operation import SubbuildOperation
from .simple_operation_executor import SimpleOperationExecutor

logger = logging.getLogger(__name__)


class FileBuilder:
    """Performs caching for operations that depend on files and file contents.

    ``FileBuilder`` is useful for "build" operations that are performed
    repeatedly on a group of files that mostly stay the same between
    builds. By caching arbitrary information about those files, it can
    significantly speed up build operations.

    An example use case would be linting all of the source code files in
    a given directory. By caching the lint results for each of the
    files, ``FileBuilder`` would ensure we don't re-lint any files that
    haven't changed since the last build.

    A more complex example would be scanning all of the files in a
    directory for mathematical formulas, and generating image files for
    each of those formulas. ``FileBuilder`` would ensure that we only
    scan files that have changed since the last build, since it would
    already have cached the set of formulas that appears in each of the
    unchanged files. Furthermore, ``FileBuilder`` would ensure that we
    only generate image files for formulas that don't already have image
    files, since it would reuse the appropriate images from the previous
    build.

    ``FileBuilder``'s interface makes it appear as though each time we
    build we start over from scratch, while still achieving the
    aforementioned performance benefits.

    -----

    ``FileBuilder`` is perhaps best introduced with an example. The
    ``lint_dir`` function below lints all of the Python files in a given
    directory, using the ``flake8`` command::

        import os, subprocess
        from file_builder import FileBuilder

        def lint_dir(root_dir, cache_filename):
            # Equivalent to lint_with_builder(-, root_dir)
            output = FileBuilder.build(
                cache_filename, 'lint_dir', lint_with_builder, root_dir)
            print(output, end='')

        def lint_with_builder(builder, root_dir):
            output = []
            for filename in python_files_in_dir(builder, root_dir):
                # Equivalent to lint_file(-, filename), but with caching
                file_output = builder.subbuild(
                    'lint_file', lint_file, filename)
                output.append(file_output)
            return ''.join(output)

        def python_files_in_dir(builder, root_dir):
            python_files = []
            for dir_, subdirs, subfiles in builder.walk(root_dir):
                for subfile in subfiles:
                    if subfile.endswith('.py'):
                        python_files.append(os.path.join(dir_, subfile))
            return python_files

        def lint_file(builder, filename):
            builder.declare_read(filename)

            # Return the output of the flake8 command
            process = subprocess.run(
                ['flake8', filename], capture_output=True)
            return process.stdout.decode()

    Calling ``FileBuilder.build`` or ``FileBuilder.build_versioned``
    runs a build operation. There are two types of cacheable operations
    that may occur during a build: "build file" operations, triggered by
    calling ``FileBuilder.build_file`` or
    ``FileBuilder.build_file_with_comparison``, and "subbuild"
    operations, triggered by calling ``FileBuilder.subbuild``. Whenever
    we call ``build_file``, ``build_file_with_comparison``, or
    ``subbuild``, we check whether the result is cached. If so, we use
    the cached result. If not, we obtain the result by calling the
    function that was supplied as an argument.

    For this to work properly, the functions used to rebuild files or
    execute subbuilds must obey certain rules:

    * They must be functional. That is, they must depend only on their
      arguments and on the contents of the file system, and they may not
      have any side effects. (Irrelevant side effects like printing to
      standard output or writing to a log file are permitted.)
    * They must be deterministic. For their given arguments, and given
      the current contents of the file system, they must produce the
      same results - or at least equivalent results from the
      application's perspective.
    * All file system operations on the relevant files must be performed
      by calling a ``FileBuilder`` method. For example, it is invalid to
      call ``os.path.isdir``; the function must call
      ``FileBuilder.is_dir`` instead. This does not apply to
      "irrelevant" files that we are not operating on, such as log
      files, temporary files, or external binary files.
    * As a corollary, we may only read from files passed to the
      ``read_text``, ``read_binary``, and ``declare_read`` methods.
      Again, this does not apply to "irrelevant" files.
    * Another corollary: We may only write to a (relevant) file during a
      call to ``build_file`` or ``build_file_with_comparison`` for that
      file.

    If these restrictions are followed, then the behavior of
    ``FileBuilder.build`` is equivalent to the following:

    * Remove all files created during the previous build.
    * Call the function passed as an argument to ``FileBuilder.build``.
    * Whenever we call ``build_file``, ``build_file_with_comparison``,
      or ``subbuild``, call the function passed as an argument.
    * If the function passed to ``FileBuilder.build`` doesn't raise an
      exception, return that function's return value.
    * If the function passed to ``FileBuilder.build`` raises an
      exception, roll back. That is, remove all of the files created
      during the current build, and restore all of the files written
      during the previous build.

    Even though this is what ``FileBuilder.build`` appears to be doing,
    this is not what actually happens behind the scenes. In reality,
    whenever we can use a previously cached result instead of calling a
    function passed as an argument to a ``FileBuilder`` method, we do
    so. Using a cached result is legitimate if the filename and function
    name are the same, the arguments to the function are the same, the
    optional version is the same, and all of the file system operations
    have the same results.

    In addition, to save time, ``FileBuilder`` doesn't delete any of the
    files written during the previous build unless it has to overwrite
    them. The results of FileBuilder's file system methods, such as
    ``is_file`` and ``list_dir``, depend on the virtual state of the
    file system maintained by ``FileBuilder``, not simply on the real
    state of the file system.

    ``FileBuilder`` does its best to deal with concurrent external
    changes to files and directories, but it makes no guarantees.

    ``FileBuilder`` is thread-safe. A build process may be parallelized
    using multithreading or multiprocessing. However, be aware that the
    global interpreter lock affects the effectiveness of multithreading
    with regard to parallelism; see
    https://wiki.python.org/moin/GlobalInterpreterLock .
    """

    # Implementation notes:
    #
    # Unless otherwise specified, apart from public FileBuilder methods, all
    # arguments, return values, and fields in the source code (excluding tests
    # and samples) must be "sanitized":
    #
    # * All filenames must be sanitized, as in _sanitize_filename. (Depending
    #   on the use case, they may or not be "norm-cased", i.e. the result of a
    #   call to os.path.normcase.)
    # * All JSON values must be sanitized, as in JsonUtil.sanitize, unless
    #   they represent return values of simple operations, in which case they
    #   may include tuples.
    #
    # The real state of the file system is the same as the virtual state of the
    # file system, except for the following:
    #
    # * Additional files and directories created during the previous build may
    #   be present, including the cache file.
    # * Files we are currently building may be present.
    # * Additional directories that were created during the current build (for
    #   build_file*), but need to be removed due to exceptions in build_file*
    #   functions may be present.
    # * Files and directories in the relevant instance of CreatedFiles may be
    #   absent.
    #
    # FileBuilder methods attempt to represent the true virtual state of the
    # file system, but they are not always correct. However, they are intended
    # to satisfy the following requirements:
    #
    # * Correctness: If there are no external modifications to the file system
    #   during the build, then in the single-threaded case, all simple
    #   operations should return the correct results. In the multi-threaded
    #   case, simple operations might return incorrect results, because they
    #   are not always atomic. However, once all previous modifications have
    #   settled, a simple operation should return the correct result, provided
    #   there are no concurrent modifications.
    # * Eventual consistency: If there are external modifications to the
    #   file system, then all simple operations should eventually be
    #   consistent. To be precise, once all previous modifications have
    #   settled, if a series of simple operations Q is executed twice with no
    #   intervening internal or external file changes, then the results of the
    #   second execution should be consistent with each other. Examples of
    #   inconsistent results would be claiming that a given filename is both a
    #   file and a directory, or claiming that a file exists but one of its
    #   parent directories does not. (The purpose of executing the operations
    #   twice is to give FileBuilder the chance to realize that certain files
    #   exist.)
    #
    # Private attributes:
    #
    # FileBackups _backups - The FileBackups instance we are using to back up
    #     output files from the previous build. This is shared across all
    #     FileBuilder instances for the current build.
    # BuildDirs _build_dirs - The BuildDirs instance for the current build.
    #     This is shared across all FileBuilder instances for the build.
    # bool _is_finished_build - Whether this is a FileBuilder instance for the
    #     root build function (i.e. _operation is None), and the root build
    #     function has finished executing.
    # Lock _lock - The lock guarding writes to _operation.suboperations.
    # Cache _new_cache - The Cache object storing the cached results for the
    #     current build. This is shared across all FileBuilder instances for
    #     the build. Note that we don't add created directories to _new_cache
    #     until we've finished calling the function passed to build_versioned.
    #     It's easier to figure out which directories were created at the end
    #     of the build, considering how directories can be (virtually) created
    #     and removed concurrently.
    # Cache _old_cache - The Cache object storing the cached results from the
    #     previous build.
    # ComplexOperation _operation - The operation that this FileBuilder
    #     instance is responsible for executing. _operation is None if this is
    #     a FileBuilder instance for the root build function, i.e. there is no
    #     corresponding operation.
    # SimpleOperationExecutor _simple_operation_executor - The executor for
    #     executing simple operations, including operations that aren't
    #     recorded in _new_cache but are just part of the build process. This
    #     is shared across all FileBuilder instances for the build.

    # Whether the operating system is Windows
    _IS_WINDOWS = os.name == 'nt'

    def __init__(
            self, operation, old_cache, new_cache, simple_operation_executor,
            backups, build_dirs):
        """Private initializer."""
        self._operation = operation
        self._old_cache = old_cache
        self._new_cache = new_cache
        self._simple_operation_executor = simple_operation_executor
        self._backups = backups
        self._build_dirs = build_dirs
        self._is_finished_build = False
        self._lock = threading.Lock()

    @staticmethod
    def build(cache_filename, build_name, func, *args, **kwargs):
        """Execute a build operation.

        This is equivalent to ``build_versioned(cache_filename,
        build_name, {}, func, *args, **kwargs)``. See the comments for
        ``build_versioned``.
        """
        return FileBuilder.build_versioned(
            cache_filename, build_name, {}, func, *args, **kwargs)

    @staticmethod
    def build_versioned(
            cache_filename, build_name, versions, func, *args, **kwargs):
        """Execute a build operation.

        The behavior of ``build_versioned`` is equivalent to the
        following:

        * Delete all of the files written during the previous build
          (even if some of them have changed), including
          ``cache_filename``. Remove all of the directories created
          during the last build that are empty.
        * Call ``func(builder, *args, **kwargs)``, where ``builder`` is
          a new instance of ``FileBuilder``.
        * If ``func`` doesn't raise an exception, commit: store
          all of the results from the current build in
          ``cache_filename``.
        * If ``func`` raises an exception, roll back. That is, delete
          all of the files and directories created during the current
          build, and restore all of the files and directories written
          during the previous build (even if they had changed) and the
          old contents of ``cache_filename``. Also, restore the old
          contents of any files that ``build_file*` overwrote.

        However, ``build_versioned`` doesn't literally follow the above
        steps. Instead, it uses cached results from the previous build
        whenever possible. These results are read from
        ``cache_filename``. (If the file doesn't exist, we assume this
        is the first build and the cache is empty.)

        Note that the result of ``func(builder, *args, **kwargs)`` is
        not cached; only ``build_file*`` and subbuild results are
        cached. If you wish to cache the call to ``func``, you should
        wrap it in a subbuild.

        ``func`` must perform all file system operations by calling
        methods on the ``FileBuilder``. However, unlike build file and
        subbuild functions, it need not be functional or deterministic.

        ``versions`` is a map from functions' names to their versions. A
        function's "version" is an arbitrary JSON value describing its
        behavior. If you change a function's version, this invalidates
        all of its cache entries that were cached under a different
        version. It also invalidates the cache entries for the functions
        that called it, the functions that called the functions that
        called it, and so on. (If ``versions`` does not contain an entry
        for a given function, then its version is ``None``.)

        Here's a suggestion for how to use versions:

        * Initially, pass in ``{}`` for the versions.
        * Whenever you change a build file or subbuild function, say by
          improving its output or by fixing a bug, add a mapping from
          the function's name to the current timestamp. For example, you
          could use the output of the UNIX command
          ``date -u +"%Y-%m-%dT%H:%M:%SZ"``.

        Arguments:
            cache_filename (pathlike): The file used to store cached
                results. This must be a string or ``bytes`` object or a
                path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            build_name (str): A string identifying the build type. We
                raise an exception if this doesn't match the build name
                used when creating ``cache_filename``. The purpose of
                the build name is to ensure that we don't use a cache
                file created for a different build process.
            versions (dict): A map from functions' names to their
                versions.
            func (callable): The function. This accepts a
                ``FileBuilder`` as an argument, followed by ``*args``
                and ``**kwargs``. The function must perform all file
                system operations by calling methods on the
                ``FileBuilder``.
            *args: The positional arguments to the function, apart from
                the ``FileBuilder``. (These need not be JSON values.)
            **kwargs: The keyword arguments to the function. (These need
                not be JSON values.)

        Returns:
            The return value of ``func``. (This need not be a JSON
            value.)

        Raises:
            TypeError: If one of the arguments has the wrong type.
            OSError: If there was an OS error reading or writing the
                cache file, moving or removing files or directories from
                the previous build, etc.
            Exception: If there was an error parsing the cache file,
                ``build_name`` doesn't match the build name used when
                creating ``cache_filename``, or ``func`` raised an
                exception.
        """
        if not isinstance(build_name, str):
            raise TypeError('Build name must be a string')
        if not callable(func):
            raise TypeError('"func" must be callable')
        cache_filename = FileBuilder._sanitize_filename(cache_filename)
        sanitized_versions = FileBuilder._sanitize_versions(versions)

        if os.path.isfile(cache_filename):
            old_cache = Cache.read_immutable(cache_filename)
            if old_cache.build_name() != build_name:
                raise RuntimeError(
                    'The cache file was created for the build named {:s}, '
                    'which is different from the specified build name '
                    '{:s}'.format(old_cache.build_name(), build_name))
        elif os.path.isdir(cache_filename):
            raise IsADirectoryError(
                "The cache file is an existing directory, so we can't write "
                'to it: {:s}'.format(cache_filename))
        else:
            logger.info(
                'The cache file {:s} does not exist, so building everything '
                'from scratch'.format(cache_filename))
            old_cache = Cache.create_empty_immutable(
                build_name, sanitized_versions)

        new_cache = Cache.create_empty_mutable(build_name, sanitized_versions)
        build_dirs = BuildDirs(
            old_cache.created_dirs(),
            old_cache.created_files() + [cache_filename])
        simple_operation_executor = SimpleOperationExecutor(
            cache_filename, old_cache, new_cache, build_dirs)
        with FileBackups() as backups:
            builder = FileBuilder(
                None, old_cache, new_cache, simple_operation_executor, backups,
                build_dirs)
            try:
                return builder._build(cache_filename, func, args, kwargs)
            finally:
                builder._is_finished_build = True

    @staticmethod
    def clean(cache_filename, build_name):
        """Remove the files and directories created during the previous build.

        Remove the files created during the previous build (even if some
        of them have changed), including ``cache_filename``, and remove
        all of the directories created during the last build that are
        empty. (If ``cache_filename`` doesn't exist, we assume there
        were no previous builds, and calling ``clean`` has no effect.)

        If the intent is to redo the build after changing its
        implementation, consider calling ``build_versioned`` with a
        suitable ``versions`` argument instead.

        Arguments:
            cache_filename (pathlike): The file storing the cached
                results from the previous build. This must be a string
                or ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            build_name (str): A string identifying the build type, as in
                the ``build_name`` argument to ``build_versioned``. This
                may be ``None``, indicating that the build name is
                unknown.

        Raises:
            TypeError: If one of the arguments has the wrong type.
            OSError: If there was an OS error reading the cache file or
                removing the files or directories from the previous
                build.
            Exception: If there was an error parsing the cache file,
                or ``build_name`` isn't ``None`` and it doesn't match
                the build name used when creating ``cache_filename``.
        """
        if build_name is not None and not isinstance(build_name, str):
            raise TypeError('Build name must be a string')
        cache_filename = FileBuilder._sanitize_filename(cache_filename)
        if not os.path.exists(cache_filename):
            logger.info(
                "The cache file {:s} does not exist, so there's nothing to "
                'clean'.format(cache_filename))
            return

        cache = Cache.read_immutable(cache_filename)
        if build_name is not None and cache.build_name() != build_name:
            raise RuntimeError(
                'The cache file was created for the build named {:s}, which '
                'is different from the specified build name {:s}'.format(
                    cache.build_name(), build_name))

        for filename in cache.created_files():
            FileBuilder._try_to_remove_file(filename)
        FileBuilder._try_to_remove_file(cache_filename)
        FileBuilder._remove_empty_dirs(cache.created_dirs())

    def build_file(self, filename, func_name, func, *args, **kwargs):
        """Write the specified output file.

        This is equivalent to ``build_file_with_comparison(filename,
        FileComparison.METADATA, func_name, func, *args, **kwargs)``.
        See the comments for ``build_file_with_comparison``.
        """
        return self.build_file_with_comparison(
            filename, FileComparison.METADATA, func_name, func, *args,
            **kwargs)

    def build_file_with_comparison(
            self, filename, file_comparison, func_name, func, *args, **kwargs):
        """Write the specified output file.

        This is equivalent to calling ``func(builder, absolute_filename,
        *args, **kwargs)``, where ``builder`` is an instance of
        ``FileBuilder`` and ``absolute_filename`` is the absolute
        filename (i.e. the return value of
        ``os.path.abspath(os.fsdecode(filename))``). ``func`` must write
        to the given file - by calling ``open``, passing it as an
        argument to a shell command, or by some other means.

        If possible, we use the cached results from the previous build
        instead of calling ``func``; in other words, we retain the
        current contents of ``filename``.

        Before calling ``func``, ``build_file_with_comparison``
        automatically creates all of the parent directories of
        ``filename``, and it deletes the file if it is present. If
        ``func`` raises an exception, then
        ``build_file_with_comparison`` deletes ``filename`` if it is
        present, along with any parent directories it created if they
        are empty, and it re-raises the exception.

        Building a file is atomic. From the perspective of functions
        passed to ``FileBuilder``, the file isn't created until ``func``
        returns, at which point it receives its final contents. So until
        ``func`` returns, methods such as ``is_file`` and ``read_text``
        will act as though the file doesn't exist yet, even if it does.

        ``build_file``/``build_file_with_comparison`` may not be called
        twice on the same file in a single build. Calls to
        ``build_file*`` and ``subbuild`` may be nested within calls to
        ``build_file*``.

        The ``FileBuilder`` instance passed to ``func`` is not the same
        as ``self``. ``func`` must use the ``FileBuilder`` instance
        passed to it to perform all file system operations; it may not
        use ``self``.

        The arguments (``args`` and ``kwargs``) and the return value of
        ``func`` must be JSON values. ``FileBuilder`` copies and
        "sanitizes" these values, using
        ``json.loads(json.dumps(value))`` or something equivalent. (If
        we need to pass in an object that is not a JSON value, we can
        serialize it to a string first.)

        A note on concurrency: ``build_file_with_comparison`` must be
        called in the same process as the original call to ``build`` or
        ``build_versioned``. They need to share memory to communicate
        the cached results. In order to parallelize using
        multiprocessing, you should create a separate thread, call
        ``build_file*`` inside that thread, and spawn a new process
        inside of ``func``. (Make sure the new process doesn't call any
        ``FileBuilder`` methods.) See
        ``samples/parallel_seam_carving/parallel_seam_carve_builder.py``
        for an example.

        Sometimes it is desirable to pass arguments to ``func`` that
        don't affect the results, but are needed for coordinating
        parallelism or for some other allowable purpose. Examples
        include ``ThreadPoolExecutors`` and instances of
        ``multiprocessing.pool.Pool``. The problem with this is that the
        arguments passed to ``func`` are copies of ``args`` and
        ``kwargs``, rather than direct references. In such cases, we can
        smuggle in the arguments either by binding them using
        ``functools.partial``, or by making them fields of the some
        object (e.g. ``self._my_executor``) and passing in one of the
        object's methods for ``func`` (e.g. ``self._my_build_file``).

        Arguments:
            filename (pathlike): The file we are writing. This must be a
                string or ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            file_comparison (FileComparison): The method to use to
                compare the output file. During the next build, we will
                use this comparison to check whether the output file has
                changed, in which case we must rebuild the file.
            func_name (str): A string identifying the function ``func``.
            func (callable): The function. This accepts a
                ``FileBuilder`` and the absolute filename as arguments,
                followed by ``*args`` and ``**kwargs``. The function
                must be functional and deterministic, and it must
                perform all file system operations by calling methods on
                the ``FileBuilder``.
            *args: The positional arguments to the function, apart from
                the ``FileBuilder`` and filename.
            **kwargs: The keyword arguments to the function.

        Returns:
            The (actual or cached) return value of ``func``.

        Raises:
            TypeError: If one of the arguments has the wrong type, or
                the return value of ``func`` is not a JSON value.
            OSError: If there was an OS error creating the parent
                directories, moving or removing files or directories
                from the previous build to make room for the file, etc.
            Exception: If we have already called ``build_file*`` on the
                file during this build; the file is the cache file;
                ``func`` doesn't create the file; this ``FileBuilder``
                instance has finished executing the relevant call to
                ``build_file*``, ``subbuild``, ``build``, or
                ``build_versioned``; or ``func`` raised an exception.
        """
        self._assert_not_finished()
        filename = FileBuilder._sanitize_filename(filename)
        if not isinstance(func_name, str):
            raise TypeError('Function name must be a string')
        if not isinstance(file_comparison, FileComparison):
            raise TypeError(
                'file_comparison must be an instance of FileComparison')
        if not callable(func):
            raise TypeError('"func" must be callable')
        sanitized_args, sanitized_kwargs = FileBuilder._sanitize_args(
            args, kwargs, 'the build_file* call for {:s}'.format(filename))

        suboperation = BuildFileOperation(
            filename, file_comparison, func_name, sanitized_args,
            sanitized_kwargs, [], None, None, False, False, False)
        subbuilder = FileBuilder(
            suboperation, self._old_cache, self._new_cache,
            self._simple_operation_executor, self._backups, self._build_dirs)
        try:
            subbuilder._build_file(func)
        except Exception:
            if not suboperation.raised:
                suboperation.raised = True
                suboperation.setup_failed = True
            raise
        finally:
            suboperation.is_finished = True
            self._append_suboperation(suboperation)
        return suboperation.return_value

    def subbuild(self, func_name, func, *args, **kwargs):
        """Execute a cacheable operation.

        This is equivalent to calling ``func(builder, *args,
        **kwargs)``, except we don't call ``func`` if the result is
        cached. A typical use case would be to read a file, compute some
        information about its contents, and return the result. Calls to
        ``build_file*`` and ``subbuild`` may be nested within calls to
        ``subbuild``. ``subbuild`` may not be called twice with the same
        function name and arguments in a single build.

        How a build is divided into subbuilds has a significant effect
        on performance. A rule of thumb is that file reads should be
        divided into as many separate subbuilds and calls to
        ``build_file*`` as is possible (and practical). This assumes
        that the most time-consuming parts of the build process involve
        processing input files (i.e. reading from them and computing
        information about their contents) and generating output files.

        However, it's generally not a good idea for ``subbuild`` to read
        in a file and return its full contents. Then we would store the
        file's contents in the cache. This is likely a waste of space
        and time.

        It might be tempting to create deeply nested subbuilds, with the
        intention of increasing the opportunities for caching. However,
        this is not normally beneficial. For example, suppose we need to
        perform some time-consuming computation on each of the files in
        a given directory. Here, we would use a separate subbuild for
        each input file - so far so good. But we might also think to
        create a separate subbuild for each subdirectory, reasoning that
        if none of the files in a given directory have changed since the
        previous build, then we can save time by skipping over that
        directory. However, in order to determine whether we can use the
        cached results for a given directory, we'd have to repeat all of
        the file system operations performed for that directory. In
        other words, we'd have to recursively check all of the files in
        that directory to see whether they've changed since the last
        build. But this behavior is really no faster than the baseline
        case, where we don't create a separate subbuild for each
        directory. This is not to say that deeply nested subbuilds are
        never beneficial, but just to point out the implications of
        nesting subbuilds.

        The ``FileBuilder`` instance passed to ``func`` is not the same
        as ``self``. ``func`` must use the ``FileBuilder`` instance
        passed to it to perform all file system operations; it may not
        use ``self``.

        The arguments (``args`` and ``kwargs``) and the return value of
        ``func`` must be JSON values. ``FileBuilder`` copies and
        "sanitizes" these values, using
        ``json.loads(json.dumps(value))`` or something equivalent. (If
        we need to pass in an object that is not a JSON value, we can
        serialize it to a string first.)

        A note on concurrency: ``subbuild`` must be called in the same
        process as the original call to ``build`` or
        ``build_versioned``. They need to share memory to communicate
        the cached results. In order to parallelize using
        multiprocessing, you should create a separate thread, call
        ``subbuild`` inside that thread, and spawn a new process inside
        of ``func``. (Make sure the new process doesn't call any
        ``FileBuilder`` methods.) See
        ``samples/parallel_seam_carving/parallel_seam_carve_builder.py``
        for an example.

        Sometimes it is desirable to pass arguments to ``func`` that
        don't affect the results, but are needed for coordinating
        parallelism or for some other allowable purpose. Examples
        include ``ThreadPoolExecutors`` and instances of
        ``multiprocessing.pool.Pool``. The problem with this is that the
        arguments passed to ``func`` are copies of ``args`` and
        ``kwargs``, rather than direct references. In such cases, we can
        smuggle in the arguments either by binding them using
        ``functools.partial``, or by making them fields of the some
        object (e.g. ``self._my_executor``) and passing in one of the
        object's methods for ``func`` (e.g. ``self._my_subbuild``).

        Arguments:
            func_name (str): A string identifying the function ``func``.
            func (callable): The function. This accepts a
                ``FileBuilder`` as an argument, followed by ``*args``
                and ``**kwargs``. The function must be functional and
                deterministic, and it must perform all file system
                operations by calling methods on the ``FileBuilder``.
            *args: The positional arguments to the function, apart from
                the ``FileBuilder``.
            **kwargs: The keyword arguments to the function.

        Returns:
            The (actual or cached) return value of ``func``.

        Raises:
            TypeError: If one of the arguments has the wrong type, or
                the return value of ``func`` is not a JSON value.
            Exception: If we have already called ``subbuild`` with the
                same function name and arguments during this build; this
                ``FileBuilder`` instance has finished executing the
                relevant call to ``build_file*``, ``subbuild``,
                ``build``, or ``build_versioned``; or ``func`` raised an
                exception.
        """
        self._assert_not_finished()
        if not isinstance(func_name, str):
            raise TypeError('Function name must be a string')
        if not callable(func):
            raise TypeError('"func" must be callable')
        sanitized_args, sanitized_kwargs = FileBuilder._sanitize_args(
            args, kwargs, 'the subbuild function {:s}'.format(func_name))

        suboperation = SubbuildOperation(
            func_name, sanitized_args, sanitized_kwargs, [], None, False,
            False, False)
        subbuilder = FileBuilder(
            suboperation, self._old_cache, self._new_cache,
            self._simple_operation_executor, self._backups, self._build_dirs)
        try:
            subbuilder._subbuild(func)
        except Exception:
            if not suboperation.raised:
                suboperation.raised = True
                suboperation.setup_failed = True
            raise
        finally:
            suboperation.is_finished = True
            self._append_suboperation(suboperation)
        return suboperation.return_value

    def read_text(self, filename, file_comparison=FileComparison.METADATA):
        """Open the specified file for reading text.

        Return a file object for the file. This is the analogue of
        ``open(filename, 'r')``.

        Arguments:
            filename (pathlike): The file to read. This must be a string
                or ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            file_comparison (FileComparison): The method to use to
                compare the file. During the next build, we will use
                this comparison to check whether it has changed, in
                which case the cache entries containing the call to
                ``read_text`` are invalid.

        Raises:
            TypeError: If one of the arguments has the wrong type.
            FileNotFoundError: If the file does not exist, according to
                the virtual state of the file system.
            IsADirectoryError: If the filename refers to a directory,
                according to the virtual state of the file system.
            OSError: If some other type of OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        filename = FileBuilder._sanitize_filename(filename)
        if not isinstance(file_comparison, FileComparison):
            raise TypeError(
                'file_comparison must be an instance of FileComparison')
        self._exec_simple_operation(
            SimpleOperation('read', [filename, file_comparison.name]))
        return open(filename, 'r')

    def read_binary(self, filename, file_comparison=FileComparison.METADATA):
        """Open the specified file for reading binary content.

        Return a file object for the file. This is the analogue of
        ``open(filename, 'rb')``.

        Arguments:
            filename (pathlike): The file to read. This must be a string
                or ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            file_comparison (FileComparison): The method to use to
                compare the file. During the next build, we will use
                this comparison to check whether it has changed, in
                which case the cache entries containing the call to
                ``read_binary`` are invalid.

        Raises:
            TypeError: If one of the arguments has the wrong type.
            FileNotFoundError: If the file does not exist, according to
                the virtual state of the file system.
            IsADirectoryError: If the filename refers to a directory,
                according to the virtual state of the file system.
            OSError: If some other type of OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        filename = FileBuilder._sanitize_filename(filename)
        if not isinstance(file_comparison, FileComparison):
            raise TypeError(
                'file_comparison must be an instance of FileComparison')
        self._exec_simple_operation(
            SimpleOperation('read', [filename, file_comparison.name]))
        return open(filename, 'rb')

    def declare_read(self, filename, file_comparison=FileComparison.METADATA):
        """Declare that we are reading the specified file.

        Each function passed to ``build``, ``build_versioned``,
        ``subbuild``, or ``build_file*`` must declare all of the
        (relevant) files that it reads, excluding those which it reads
        by calling ``read_text`` or ``read_binary``. While ``read_text``
        and ``read_binary`` are more explicit, it's not always practical
        to call them. For example, the read might occur in a third-party
        library or in a shell script.

        It is recommended to call ``declare_read`` before reading a
        file, not after. This ensures that we declare the file even if
        there is an exception when reading it. If this is not practical,
        we may call ``declare_read`` after reading the relevant files.
        However, to ensure correct behavior, if we fail to declare the
        files due to an exception, we must make sure that this exception
        (or some other exception) is raised all the way up through the
        function passed to ``build`` or ``build_versioned``.

        Arguments:
            filename (pathlike): The file to read. This must be a string
                or ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            file_comparison (FileComparison): The method to use to
                compare the file. During the next build, we will use
                this comparison to check whether it has changed, in
                which case the cache entries containing the call to
                ``declare_read`` are invalid.

        Raises:
            TypeError: If one of the arguments has the wrong type.
            FileNotFoundError: If the file does not exist, according to
                the virtual state of the file system.
            IsADirectoryError: If the filename refers to a directory,
                according to the virtual state of the file system.
            OSError: If some other type of OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        if not isinstance(file_comparison, FileComparison):
            raise TypeError(
                'file_comparison must be an instance of FileComparison')
        self._exec_simple_operation(
            SimpleOperation(
                'read', [
                    FileBuilder._sanitize_filename(filename),
                    file_comparison.name]))

    def list_dir(self, dir_):
        """Return the subfiles of the specified directory.

        Return the subfiles of the specified directory, according to the
        virtual state of the file system. This is a list of the names of
        the files and directories that are direct children of the
        directory, in an arbitrary order. The names only contain the
        final components of each path, e.g. ``'bar'`` and not
        ``'/foo/bar'``. The return value does not include special
        entries like ``'.'`` and ``'..'``.

        This is almost an analogue of ``os.listdir(dir_)``. The
        difference is that the return value always contains strings
        rather than ``bytes`` objects, and ``FileBuilder.list_dir``
        doesn't handle file descriptors.

        Arguments:
            dir_ (pathlike): The directory. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``dir_`` has the wrong type.
            FileNotFoundError: If the file does not exist, according to
                the virtual state of the file system.
            NotADirectoryError: If the filename refers to a regular
                file, according to the virtual state of the file system.
            OSError: If some other type of OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        return self._exec_simple_operation(
            SimpleOperation(
                'list_dir', [FileBuilder._sanitize_filename(dir_)]))

    def walk(self, dir_, top_down=True):
        """Return the files in the specified directory, recursively.

        Return a list describing the files in the specified directory,
        according to the virtual state of the file system. This includes
        not just the immediate children, but all descendant files.
        However, it does not include descendants of directories other
        than ``dir_`` that are symbolic links. This returns ``[]`` if in
        the virtual state of the file system, the file does not exist or
        the filename refers to a regular file.

        The return value is a list of tuples (dir_name, subdirs,
        subfiles), each of which describes the immediate children of one
        directory. There is one tuple for each subdirectory of ``dir_``,
        including one tuple for ``dir_``. The first element of each
        tuple is the absolute filename for the subdirectory. The second
        element is a list of the names of its immediate subdirectories.
        The third element is a list of the names of its immediate
        subfiles, excluding directories.

        The names only contain the final components of each path, e.g.
        ``'bar'`` and not ``'/foo/bar'``. They do not include special
        entries like ``'.'`` and ``'..'``. Each list of names is in an
        arbitrary order.

        If ``top_down`` is true, then the tuple for a directory appears
        before the tuples for the directories it contains. Otherwise, it
        appears after. Apart from this constraint, the order of the
        tuples is unspecified.

        This is a loose analogue of ``os.walk(dir_, top_down)``, but
        there are some significant differences.

        Arguments:
            dir_ (pathlike): The directory. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).
            top_down (bool): Whether to return the contents of each
                directory before those of its subdirectories.

        Raises:
            TypeError: If one of the arguments has the wrong type.
            OSError: If an OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        if not isinstance(top_down, bool):
            raise TypeError('top_down must be a boolean')
        return self._exec_simple_operation(
            SimpleOperation(
                'walk', [FileBuilder._sanitize_filename(dir_), top_down]))

    def is_file(self, filename):
        """Return whether the specified filename refers to a regular file.

        Return whether the specified filename refers to an existing
        regular file, according to the virtual state of the file system.
        This follows symbolic links. This is the analogue of
        ``os.path.isfile(filename)``.

        Arguments:
            filename (pathlike): The filename. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``filename`` has the wrong type.
            OSError: If an OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        return self._exec_simple_operation(
            SimpleOperation(
                'is_file', [FileBuilder._sanitize_filename(filename)]))

    def is_dir(self, filename):
        """Return whether the specified filename refers to a directory.

        Return whether the specified filename refers to an existing
        directory, according to the virtual state of the file system.
        This follows symbolic links. This is the analogue of
        ``os.path.isdir(filename)``.

        Arguments:
            filename (pathlike): The filename. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``filename`` has the wrong type.
            OSError: If an OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        return self._exec_simple_operation(
            SimpleOperation(
                'is_dir', [FileBuilder._sanitize_filename(filename)]))

    def exists(self, filename):
        """Return whether the specified file exists.

        Return whether the specified filename refers to an existing file
        or directory, according to the virtual state of the file system.
        This returns ``False`` if the file is a broken symbolic link.
        Depending on the operating system, it may return ``False`` if we
        don't have permission to check the file.

        This is almost an analogue of ``os.path.exists(filename)``. The
        difference is that ``FileBuilder.exists`` doesn't handle file
        descriptors.

        Arguments:
            filename (pathlike): The filename. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``filename`` has the wrong type.
            OSError: If an OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        return self._exec_simple_operation(
            SimpleOperation(
                'exists', [FileBuilder._sanitize_filename(filename)]))

    def get_size(self, filename):
        """Return the size of the specified file in bytes.

        Return the size of the specified file in bytes, according to the
        virtual state of the file system. This follows symbolic links.
        This is the analogue of ``os.path.getsize``.

        Arguments:
            filename (pathlike): The filename. This must be a string or
                ``bytes`` object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``filename`` has the wrong type.
            FileNotFoundError: If the file does not exist, according to
                the virtual state of the file system.
            OSError: If some other type of OS error occurred.
            Exception: If this ``FileBuilder`` instance has finished
                executing the relevant call to ``build_file*``,
                ``subbuild``, ``build``, or ``build_versioned``.
        """
        return self._exec_simple_operation(
            SimpleOperation(
                'get_size', [FileBuilder._sanitize_filename(filename)]))

    def _assert_not_finished(self):
        """Raise if ``_operation.is_finished`` or ``_is_finished_build``."""
        operation = self._operation
        if operation is not None:
            is_finished = operation.is_finished
        else:
            is_finished = self._is_finished_build

        if is_finished:
            if isinstance(operation, BuildFileOperation):
                description = 'the build_file* call for {:s}'.format(
                    operation.filename)
            elif isinstance(operation, SubbuildOperation):
                description = 'the subbuild function {:s}'.format(
                    operation.func_name)
            elif operation is None:
                description = 'the build function'
            else:
                raise RuntimeError('Unhandled operation type')

            raise RuntimeError(
                'This FileBuilder instance has already finished executing '
                '{:s}'.format(description))

    def _append_suboperation(self, suboperation):
        """Append the specified ``Operation`` to ``_operation.suboperations``.

        If ``_operation`` is ``None``, this simply calls
        ``_assert_not_finished()``.
        """
        if self._operation is None:
            self._assert_not_finished()
        else:
            with self._lock:
                self._assert_not_finished()
                self._operation.suboperations.append(suboperation)

    def _exec_simple_operation(self, operation):
        """Perform the specified ``SimpleOperation``.

        After calling ``_assert_not_finished()``, this updates the
        ``return_value``, ``exception_type_str``, and ``is_finished``
        fields, as well as ``_operation.suboperations``. It returns the
        result (or raises the resulting exception).
        """
        self._assert_not_finished()
        try:
            operation.return_value = self._simple_operation_executor.exec(
                operation.name, operation.args, None)
        except OSError as exception:
            operation.exception_type_str = exception.__class__.__name__
            raise
        finally:
            operation.is_finished = True
            self._append_suboperation(operation)
        return operation.return_value

    def _noneable_file_comparison_result(self, filename, file_comparison):
        """Return the result of the specified file comparison.

        This returns the result of performing the specified file
        comparison, as in
        ``SimpleOperationExecutor.file_comparison_result``. If the
        filename does not refer to an existing regular file, this
        returns ``None`` instead. This is strictly an operation on the
        real file system, as opposed to the virtual file system.
        """
        try:
            return self._simple_operation_executor.file_comparison_result(
                filename, file_comparison.name)
        except (FileNotFoundError, IsADirectoryError):
            return None

    def _is_build_file_cached(self, operation):
        """Return whether the specified output file is cached.

        The comparison is based on ``operation.file_comparison_result``.
        This only checks the file's contents; it doesn't check the
        suboperations, function version, etc.

        Arguments:
            operation (BuildFileOperation): The operation whose output
                file we should check.
        """
        if not FileBuilder._has_case(operation.filename):
            return False
        else:
            file_comparison_result = self._noneable_file_comparison_result(
                operation.filename, operation.file_comparison)
            return JsonUtil.is_equal(
                operation.file_comparison_result, file_comparison_result)

    def _is_build_file_operation_cached(self, operation, created_files):
        """Return whether the specified ``BuildFileOperation`` is cached.

        Return whether the specified cached ``BuildFileOperation`` entry
        is valid, so we can use the cached results. This includes
        checking whether the operations in ``operation.suboperations``
        are cached.

        Arguments:
            operation (BuildFileOperation): The operation to check.
            created_files (CreatedFiles): The ``CreatedFiles`` for the
                check. This indicates the files that we should initially
                regard as created. ``_is_build_file_operation_cached``
                updates this according to the files that would be
                created if we executed the operation.
        """
        if (not JsonUtil.is_equal(
                self._old_cache.get_func_version(operation.func_name),
                self._new_cache.get_func_version(operation.func_name)) or
                (not operation.raised and
                    not self._is_build_file_cached(operation)) or

                # If setup failed, then the conditions that gave rise to the
                # failure might no longer hold. See SetupFailedTest for
                # examples.
                operation.setup_failed):
            return False

        # Return False in cases where _build_file raises
        filename = operation.filename
        if (self._new_cache.has_norm_cased_file(os.path.normcase(filename)) or
                self._simple_operation_executor.is_cache_file(filename)):
            return False
        try:
            self._dirs_to_make(os.path.dirname(filename), created_files)
        except OSError:
            return False

        created_files.started_building_file(filename)

        if not self._are_suboperations_cached(operation, created_files):
            return False

        if operation.raised:
            created_files.error_building_file(filename)
        else:
            created_files.finished_building_file(filename)
        return True

    def _is_subbuild_operation_cached(self, operation, created_files):
        """Return whether the specified ``SubbuildOperation`` is cached.

        Return whether the specified cached ``SubbuildOperation`` entry
        is valid, so we can use the cached results. This includes
        checking whether the operations in ``operation.suboperations``
        are cached.

        Arguments:
            operation (SubbuildOperation): The operation to check.
            created_files (CreatedFiles): The ``CreatedFiles`` for the
                check. This indicates the files that we should initially
                regard as created. ``_is_subbuild_operation_cached``
                updates this according to the files that would be
                created if we executed the operation.
        """
        if (not JsonUtil.is_equal(
                self._old_cache.get_func_version(operation.func_name),
                self._new_cache.get_func_version(operation.func_name)) or

                # If setup failed, then the conditions that gave rise to the
                # failure might no longer hold. See SetupFailedTest for an
                # example.
                operation.setup_failed):
            return False

        # Return False in the case where _subbuild raises
        subbuild_key = Cache.subbuild_key(operation)
        if self._new_cache.has_subbuild(subbuild_key):
            return False

        return self._are_suboperations_cached(operation, created_files)

    def _is_simple_operation_cached(self, operation, created_files):
        """Return whether the specified ``SimpleOperation`` is cached.

        Return whether the specified cached ``SimpleOperation`` entry is
        valid, i.e. its ``return_value`` and ``exception_type_str``
        fields match the current state of the file system.

        Arguments:
            operation (SimpleOperation): The operation to check.
            created_files (CreatedFiles): The ``CreatedFiles`` that we
                should regard as created, if any.
        """
        name = operation.name
        if (not JsonUtil.is_equal(
                self._old_cache.get_operation_version(name),
                self._new_cache.get_operation_version(name)) or

                # In case future releases of FileBuilder add new operations
                name not in SimpleOperationExecutor.OPERATIONS):
            return False

        try:
            return_value = self._simple_operation_executor.exec(
                name, operation.args, created_files)
            exception_type_str = None
        except OSError as exception:
            return_value = None
            exception_type_str = exception.__class__.__name__
        return (
            JsonUtil.is_equal(return_value, operation.return_value) and
            exception_type_str == operation.exception_type_str)

    def _are_suboperations_cached(self, operation, created_files):
        """Return whether the specified operation's suboperations are cached.

        Return whether the specified cached operation's suboperation
        entries are valid, so we may be able to use the cached results
        for ``operation``.

        Arguments:
            operation (ComplexOperation): The operation whose
                suboperations we should check.
            created_files (CreatedFiles): The ``CreatedFiles`` for the
                check. This indicates the files that we should initially
                regard as created. ``_are_suboperations_cached`` updates
                this according to the files that would be created if we
                executed the suboperations.
        """
        for suboperation in operation.suboperations:
            if isinstance(suboperation, BuildFileOperation):
                if not self._is_build_file_operation_cached(
                        suboperation, created_files):
                    return False
            elif isinstance(suboperation, SubbuildOperation):
                if not self._is_subbuild_operation_cached(
                        suboperation, created_files):
                    return False
            elif isinstance(suboperation, SimpleOperation):
                if not self._is_simple_operation_cached(
                        suboperation, created_files):
                    return False
            else:
                raise RuntimeError('Unhandled operation type')
        return True

    def _build_file_cache_lookup(self):
        """Return the cached ``BuildFileOperation`` entry we may use, if any.

        Return the cached ``BuildFileOperation`` entry whose results we
        may use in order to execute ``_operation``, if any. Assume that
        ``_operation`` is a ``BuildFileOperation``.
        """
        operation = self._operation
        cached_operation = self._old_cache.get_file(operation.filename)
        if (cached_operation is not None and not cached_operation.raised and
                cached_operation.func_name == operation.func_name and
                JsonUtil.is_equal(
                    self._old_cache.get_func_version(operation.func_name),
                    self._new_cache.get_func_version(operation.func_name)) and
                JsonUtil.is_equal(cached_operation.args, operation.args) and
                JsonUtil.is_equal(
                    cached_operation.kwargs, operation.kwargs) and
                self._is_build_file_cached(cached_operation) and
                self._are_suboperations_cached(
                    cached_operation, CreatedFiles())):
            return cached_operation
        else:
            return None

    def _subbuild_cache_lookup(self, subbuild_key):
        """Return the cached ``SubbuildOperation`` entry we may use, if any.

        Return the cached ``SubbuildOperation`` entry whose results we
        may use in order to execute ``_operation``, if any. Assume that
        ``_operation`` is a ``SubbuildOperation``.

        Arguments:
            subbuild_key: The return value of
                ``Cache.subbuild_key(self._operation)``.
        """
        operation = self._operation
        cached_operation = self._old_cache.get_subbuild(subbuild_key)
        if (cached_operation is not None and not cached_operation.raised and
                JsonUtil.is_equal(
                    self._old_cache.get_func_version(operation.func_name),
                    self._new_cache.get_func_version(operation.func_name)) and
                self._are_suboperations_cached(
                    cached_operation, CreatedFiles())):
            return cached_operation
        else:
            return None

    def _apply_cached_suboperations(self, operation):
        """Make the file system changes for reusing cached suboperations.

        Make the changes to the file system (including to ``_backups``
        and ``_build_dirs``) needed to apply the results of the
        suboperations of the specified cached ``ComplexOperation``
        entry.
        """
        for suboperation in operation.suboperations:
            if (isinstance(suboperation, BuildFileOperation) and
                    not suboperation.raised):
                filename = suboperation.filename
                created_dirs = self._make_dirs(os.path.dirname(filename))
                locked_created_dirs = self._build_dirs.started_building_file(
                    filename, created_dirs)
                try:
                    self._ensure_dirs_case(locked_created_dirs)
                    self._apply_cached_suboperations(suboperation)
                except Exception:
                    self._build_dirs.error_building_file(filename)
                    raise
            elif isinstance(suboperation, ComplexOperation):
                self._apply_cached_suboperations(suboperation)

    def _dirs_to_make(self, dir_, created_files):
        """Return the parents of ``dir_`` needed to create to make ``dir_``.

        Return the parents of ``dir_`` that we would need to create in
        order to ensure that the directory exists in the virtual state
        of the file system, possibly including ``dir_`` itself. Each
        directory appears after its parent.

        Arguments:
            dir_ (str): The non-norm-cased filename of the directory.
            created_files (CreatedFiles): The ``CreatedFiles`` that we
                should regard as created, if any.

        Returns:
            list<str>: The non-norm-cased filenames of the parent
                directories.

        Raises:
            OSError: If we are unable to create the directory.
        """
        parents = []
        parent = dir_
        is_dir = self._simple_operation_executor.is_dir(parent, created_files)
        is_file = (
            not is_dir and
            self._simple_operation_executor.is_file(parent, created_files))
        while not is_file and not is_dir:
            if self._simple_operation_executor.is_cache_file(parent):
                raise NotADirectoryError(
                    'Unable to create directory {:s}, because the parent {:s} '
                    'is the cache file'.format(dir_, parent))
            parents.append(parent)

            prev_parent = parent
            parent = os.path.dirname(parent)
            if parent == prev_parent:
                # The root directory does not exist
                raise FileNotFoundError(
                    'Unable to create directory {:s}, because {:s} does not '
                    'exist'.format(dir_, parent))

            is_dir = self._simple_operation_executor.is_dir(
                parent, created_files)
            is_file = (
                not is_dir and
                self._simple_operation_executor.is_file(parent, created_files))

        if is_file:
            raise NotADirectoryError(
                'Unable to create directory {:s}, because the parent {:s} is '
                'a regular file'.format(dir_, parent))
        return list(reversed(parents))

    def _make_dirs(self, dir_):
        """Create the specified directory and all needed parent directories.

        Create the specified directory in the real file system if it
        does not already exist, including creating any parent
        directories that do not exist.

        Returns:
            list<str>: The parent directories that we needed to create
                in the virtual state of the file system in order to
                create ``dir_``, possibly including ``dir_`` itself.
                Each directory appears after its parent. Note that this
                isn't atomic, so it's possible that ``_make_dirs`` could
                return a given directory multiple times in a single
                build, even without any external changes to the file
                system. See the comments for
                ``BuildDirs.started_building_file``, as that method
                deals with this case.

        Raises:
            OSError: If we are unable to create the directory.
        """
        dirs_to_make = self._dirs_to_make(dir_, None)
        for parent in dirs_to_make:
            if (os.path.isfile(parent) and
                    self._old_cache.created_norm_cased_file(
                        os.path.normcase(parent)) and
                    self._backups.back_up_and_remove(parent)):
                logger.info(
                    'Moved {:s} to a temporary directory, in order to create '
                    'a directory with that filename'.format(parent))

            try:
                os.mkdir(parent)
            except FileExistsError:
                continue
            logger.info('Created directory {:s}'.format(parent))
        return dirs_to_make

    def _make_room(self, dir_, make_room_filename):
        """Back up and remove the specified directory and its contents.

        Back up and remove any output files and directories that are in
        the specified directory and were created in the previous build,
        and then remove the directory. Assume that ``dir_`` doesn't
        exist in the virtual state of the file system.

        The ``_make_room`` method addresses the edge case where a
        filename that was a directory in the previous build is a regular
        file in the current build. It makes room for a new output file.

        Arguments:
            dir_ (str): The directory to remove.
            make_room_filename (str): The non-norm-cased filename of the
                output file we are making room for. We only use this if
                there is an error, as part of the error message.
        """
        for subfile in os.listdir(dir_):
            absolute_subfile = os.path.join(dir_, subfile)
            if os.path.isdir(absolute_subfile):
                if self._simple_operation_executor.is_dir(absolute_subfile):
                    error = True
                else:
                    self._make_room(absolute_subfile, make_room_filename)
                    error = False
            elif self._simple_operation_executor.is_file(absolute_subfile):
                error = True
            else:
                if self._backups.back_up_and_remove(absolute_subfile):
                    logger.info(
                        'Moved {:s} to a temporary directory'.format(
                            absolute_subfile))
                error = False

            if error:
                # The file was created externally or in another thread
                raise IsADirectoryError(
                    'The file passed to build_file* is an existing directory, '
                    "so we can't write to it: {:s}".format(make_room_filename))

        try:
            os.rmdir(dir_)
        except OSError:
            # e.g. a subfile was created externally or in another thread
            raise IsADirectoryError(
                'The file passed to build_file* is an existing directory, so '
                "we can't write to it: {:s}".format(make_room_filename))
        logger.info('Removed empty directory {:s}'.format(dir_))

    @staticmethod
    def _has_case(filename):
        r"""Return whether ``os.path.basename(filename)`` has the correct case.

        Return whether the case of the specified file's base name (the
        last component in its path) matches that of the file or
        directory on the file system. For example, since Windows is
        case-insensitive, if there is a file named ``C:\Foo\Bar``, then
        ``_has_case('C:\\Foo\\bar')`` will return ``False``. However,
        ``_has_case('C:\\foo\\Bar')`` will return ``True``. The return
        value is unspecified if the file does not exist.
        """
        return (
            # Optimization: Avoid calling Path.resolve() if not on Windows
            not FileBuilder._IS_WINDOWS or

            Path(filename).resolve().name == os.path.basename(filename))

    def _ensure_dir_case(self, dir_):
        r"""Ensure that the case of the specified directory is correct.

        Ensure that the case of the specified directory's base name (the
        last component in its path) matches that of
        ``os.path.basename(dir_)``. For example, since Windows is
        case-insensitive, if there is a directory named ``C:\Foo\Bar``,
        then ``_ensure_dir_case('C:\\Foo\\bar')`` will rename the
        directory to ``bar``. However,
        ``_ensure_dir_case('C:\\foo\\Bar')`` will have no effect.
        """
        if not FileBuilder._has_case(dir_):
            os.rename(dir_, dir_)

    def _ensure_dirs_case(self, dirs):
        """Equivalent implementation is contractually guaranteed."""
        for dir_ in dirs:
            self._ensure_dir_case(dir_)

    @staticmethod
    def _sanitize_args(args, kwargs, description):
        """Equivalent implementation is contractually guaranteed."""
        try:
            return (JsonUtil.sanitize(args), JsonUtil.sanitize(kwargs))
        except TypeError:
            raise TypeError(
                'The arguments to {:s} must be JSON values'.format(
                    description))

    def _call_and_sanitize_return_value(self, func, args, kwargs, description):
        """Equivalent implementation is contractually guaranteed."""
        return_value = func(*args, **kwargs)
        try:
            return JsonUtil.sanitize(return_value)
        except TypeError:
            raise TypeError(
                'The return value of {:s} must be a JSON value'.format(
                    description))

    @staticmethod
    def _sanitize_versions(versions):
        """Equivalent implementation is contractually guaranteed."""
        if not isinstance(versions, dict):
            raise TypeError('"versions" must be a dictionary')
        try:
            return JsonUtil.sanitize(versions)
        except TypeError:
            raise TypeError('"versions" must be a JSON value')

    @staticmethod
    def _sanitize_filename(filename):
        """Return the result of sanitizing the specified filename.

        Sanitized filenames are strings that are absolute, normalized
        paths.

        Arguments:
            filename: The filename. This should be a string or ``bytes``
                object or a path-like object (see
                https://docs.python.org/3/glossary.html#term-path-like-object
                ).

        Raises:
            TypeError: If ``filename`` has the wrong type.
        """
        # Cast the result to a string in case "filename"'s type is a subclass
        # of str
        return str(os.path.abspath(os.fsdecode(filename)))

    @staticmethod
    def _try_to_remove_file(filename):
        """Remove the specified regular file, if it exists.

        This does not raise an exception if the removal fails.
        """
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except OSError:
                logger.error(
                    'Failed to remove {:s}'.format(filename), exc_info=True)
                return
            logger.info('Removed {:s}'.format(filename))

    def _assert_build_file_call_valid(self):
        """Raise if we may not perform the ``BuildFileOperation``.

        Raise a ``RuntimeError`` if we may not validly perform
        ``_operation``. This assumes that ``_operation`` is a
        ``BuildFileOperation``.
        """
        filename = self._operation.filename
        self._new_cache.assert_doesnt_have_norm_cased_file(
            os.path.normcase(filename), filename)
        if self._simple_operation_executor.is_cache_file(filename):
            raise RuntimeError(
                'build_file* may not write to the cache file: {:s}'.format(
                    filename))

    def _prepare_file_creation(self):
        """Ensure the presence of ``os.path.dirname(_operation.filename)``.

        Create the directory ``os.path.dirname(_operation.filename)``
        and its parents if they don't already exist, and ensure that
        ``_operation.filename`` isn't a directory, in preparation for
        building the file ``_operation.filename``. This assumes that
        ``_operation`` is a ``BuildFileOperation``.

        Raises:
            OSError: If we are unable to prepare the directory.
        """
        filename = self._operation.filename
        if os.path.isdir(filename):
            if self._simple_operation_executor.is_dir(filename):
                raise IsADirectoryError(
                    'The file passed to build_file* is an existing directory, '
                    "so we can't write to it: {:s}".format(filename))
            logger.info(
                'Building {:s}, but that file is a directory created during a '
                'build operation, so moving its contents to a temporary '
                'directory and then removing it'.format(filename))
            self._make_room(filename, filename)

        return self._make_dirs(os.path.dirname(filename))

    def _handle_error_building_file(self):
        """Respond to an exception raised by the function for ``_operation``.

        Assume that ``_operation`` is a ``BuildFileOperation``.
        """
        operation = self._operation
        filename = operation.filename
        operation.raised = True
        self._build_dirs.error_building_file(filename)
        FileBuilder._try_to_remove_file(filename)
        logger.warning(
            'Failed to rebuild {:s}, due to an exception'.format(filename))

        with self._lock:
            operation.is_finished = True
        self._new_cache.finish_building_file(operation)

    def _try_to_reuse_cached_file(self):
        """Reuse a cached file result for ``_operation`` if possible.

        Reuse a cached result in ``_old_cache`` for the
        ``BuildFileOperation`` ``_operation`` if possible. Return
        whether we did so. This doesn't perform any error checking.
        """
        cached_operation = self._build_file_cache_lookup()
        if cached_operation is None:
            return False

        operation = self._operation
        file_comparison_result = self._noneable_file_comparison_result(
            operation.filename, operation.file_comparison)
        if file_comparison_result is None:
            return False

        self._apply_cached_suboperations(cached_operation)
        operation.file_comparison_result = file_comparison_result
        operation.suboperations = cached_operation.suboperations
        operation.return_value = cached_operation.return_value

        with self._lock:
            operation.is_finished = True
        self._new_cache.use_cached_operation(operation)
        return True

    def _rebuild_file(self, func):
        """Rebuild the output file ``_operation.filename``.

        Build the output file for the ``BuildFileOperation``
        ``_operation``. This rebuilds the file or builds it for the
        first time, rather than reusing a cached result. This assumes
        that we have completed any "setup", as in
        ``ComplexOperations.setup_failed``.

        Arguments:
            func (callable): The function passed to the corresponding
                call to ``build_file*``.

        Raises:
            Exception: If ``func`` raised an exception.
        """
        operation = self._operation
        filename = operation.filename
        try:
            operation.return_value = self._call_and_sanitize_return_value(
                func, [self, filename] + copy.deepcopy(operation.args),
                copy.deepcopy(operation.kwargs),
                'the build_file* call for {:s}'.format(filename))

            operation.file_comparison_result = (
                self._noneable_file_comparison_result(
                    filename, operation.file_comparison))
            if operation.file_comparison_result is None:
                raise RuntimeError(
                    "The build_file* call for {:s} didn't create that "
                    'file'.format(filename))
        except Exception:
            self._handle_error_building_file()
            raise

        with self._lock:
            operation.is_finished = True
        self._new_cache.finish_building_file(operation)

        if self._old_cache.created_file(filename):
            logger.info('Rebuilt file {:s}'.format(filename))
        else:
            logger.info('Built file {:s}'.format(filename))

    def _build_file(self, func):
        """Perform the ``BuildFileOperation`` ``_operation``.

        This uses the cached result for the operation if possible. This
        sets ``_operation.is_finished`` to ``True``, unless there is an
        error during "setup", as in ``ComplexOperation.setup_failed``.

        Arguments:
            func (callable): The function passed to the corresponding
                call to ``build_file*``.

        Returns:
            The (actual or cached) return value of ``func``.

        Raises:
            Exception: If ``func`` raised an exception.
        """
        operation = self._operation
        filename = operation.filename
        self._assert_build_file_call_valid()
        created_dirs = self._prepare_file_creation()
        locked_created_dirs = self._build_dirs.started_building_file(
            filename, created_dirs)

        try:
            self._ensure_dirs_case(locked_created_dirs)

            if self._try_to_reuse_cached_file():
                return operation.return_value

            if (os.path.isfile(filename) and
                    self._backups.back_up_and_remove(filename)):
                logger.info(
                    'Moved {:s} to a temporary directory, in preparation for '
                    'rebuilding the file'.format(filename))
            self._new_cache.start_building_file(filename)
        except Exception:
            self._build_dirs.error_building_file(filename)
            raise

        self._rebuild_file(func)
        return operation.return_value

    def _subbuild(self, func):
        """Perform the ``SubbuildOperation`` ``_operation``.

        This uses the cached result for the operation if possible. This
        sets ``_operation.is_finished`` to ``True``, unless there is an
        error during "setup", as in ``ComplexOperation.setup_failed``.

        Arguments:
            func (callable): The function passed to the corresponding
                call to ``subbuild``.

        Returns:
            The (actual or cached) return value of ``func``.

        Raises:
            Exception: If ``func`` raised an exception.
        """
        operation = self._operation
        subbuild_key = Cache.subbuild_key(operation)
        self._new_cache.assert_doesnt_have_subbuild(subbuild_key, operation)

        cached_operation = self._subbuild_cache_lookup(subbuild_key)
        if cached_operation is not None:
            self._apply_cached_suboperations(cached_operation)
            operation.suboperations = cached_operation.suboperations
            operation.return_value = cached_operation.return_value

            with self._lock:
                operation.is_finished = True
            self._new_cache.use_cached_operation(operation)
        else:
            description = 'the subbuild function {:s}'.format(
                operation.func_name)
            self._new_cache.start_subbuild(subbuild_key, operation)
            try:
                operation.return_value = self._call_and_sanitize_return_value(
                    func, [self] + copy.deepcopy(operation.args),
                    copy.deepcopy(operation.kwargs), description)
            except Exception:
                operation.raised = True
                raise
            finally:
                with self._lock:
                    operation.is_finished = True
                self._new_cache.finish_subbuild(subbuild_key, operation)
        return operation.return_value

    @staticmethod
    def _remove_empty_dirs(dirs):
        """Remove any empty directories in the specified list.

        Some directories in ``dirs`` may be parents of others, so to be
        more precise, we remove any directories that only contain other
        directories in ``dirs``. This does not raise any exceptions or
        log any messages for directories we are unable to remove.
        """
        sorted_dirs = sorted(dirs, key=lambda dir_: -len(dir_))
        for dir_ in sorted_dirs:
            try:
                os.rmdir(dir_)
            except OSError:
                continue
            logger.info('Removed empty directory {:s}'.format(dir_))

    @staticmethod
    def _create_dirs(dirs):
        """Create the specified directories, if they don't already exist.

        We do not automatically create the parent directories of the
        items in ``dirs``. However, some directories in ``dirs`` may be
        parents of others, so we do create any parents of a given
        directory that are in ``dirs``. This does not raise any
        exceptions for directories we are unable to create.

        Arguments:
            dirs (list<str>): The directories.
        """
        sorted_dirs = sorted(dirs, key=lambda dir_: len(dir_))
        for dir_ in sorted_dirs:
            try:
                os.mkdir(dir_)
            except OSError:
                if not os.path.isdir(dir_):
                    logger.error(
                        'Failed to create directory {:s}'.format(dir_),
                        exc_info=True)
                continue
            logger.info('Created directory {:s}'.format(dir_))

    def _set_created_dirs(self, cache_file_created_dirs):
        """Call ``_new_cache.add_created_dirs`` with the appropriate value.

        Call ``_new_cache.add_created_dirs``, passing as an argument any
        directories that are in ``_build_dirs.created_dirs()`` or
        ``cache_file_created_dirs``. This also calls
        ``_ensure_dir_case`` on any directories that are in
        ``cache_file_created_dirs`` but not
        ``_build_dirs.created_dirs()``.

        Arguments:
            cache_file_created_dirs (list<str>): The directories we
                created in order to store the cache file.

        Returns:
            list<str>: The norm-cased directories that we created in the
                real file system, to store build files, but are deleted
                in the virtual state of the file system.
        """
        created_dirs = self._build_dirs.created_dirs()
        norm_cased_created_dirs = set(
            [os.path.normcase(dir_) for dir_ in created_dirs])
        norm_cased_error_created_dirs = set(
            self._build_dirs.norm_cased_error_created_dirs())
        for dir_ in cache_file_created_dirs:
            norm_cased_dir = os.path.normcase(dir_)
            if norm_cased_dir not in norm_cased_created_dirs:
                created_dirs.append(dir_)
                norm_cased_error_created_dirs.discard(norm_cased_dir)
                self._ensure_dir_case(dir_)

        self._new_cache.add_created_dirs(created_dirs)
        return list(norm_cased_error_created_dirs)

    def _commit(self, norm_cased_error_created_dirs):
        """Commit (or finalize) a build operation.

        Note that this does not write the cache file, as that is the
        responsibility of the ``_build`` method.

        Arguments:
            norm_cased_error_created_dirs (list<str>): The norm-cased
                directories that we created in the real file system, to
                store build files, but are deleted in the virtual state
                of the file system.
        """
        logger.info('Committing build operation')
        for filename in self._old_cache.created_files():
            if (not self._simple_operation_executor.is_file(filename) and
                    not self._simple_operation_executor.is_cache_file(
                        filename)):
                FileBuilder._try_to_remove_file(filename)

        dirs_to_remove = set(norm_cased_error_created_dirs)
        for dir_ in self._old_cache.created_dirs():
            if not self._simple_operation_executor.is_dir(dir_):
                dirs_to_remove.add(os.path.normcase(dir_))
        FileBuilder._remove_empty_dirs(list(dirs_to_remove))
        logger.info('Committed build operation')

    def _roll_back(self, cache_file_created_dirs):
        """Roll back (or undo) a build operation.

        Arguments:
            cache_file_created_dirs (list<str>): The directories we
                created in order to store the cache file.
        """
        logger.warning('Rolling back build operation, due to an exception')

        created_dirs = (
            self._build_dirs.created_dirs() + cache_file_created_dirs)
        dirs_to_remove = set([os.path.normcase(dir_) for dir_ in created_dirs])
        dirs_to_remove.update(self._build_dirs.norm_cased_error_created_dirs())
        for dir_ in self._old_cache.created_dirs():
            dirs_to_remove.discard(os.path.normcase(dir_))

        for filename in self._new_cache.created_files():
            if not self._old_cache.created_file(filename):
                FileBuilder._try_to_remove_file(filename)
        FileBuilder._remove_empty_dirs(list(dirs_to_remove))

        FileBuilder._create_dirs(self._old_cache.created_dirs())
        self._backups.restore_all()
        logger.info('Rolled back build operation')

    def _build(self, cache_filename, func, args, kwargs):
        """Perform a root build operation.

        This includes writing the cache file and committing or rolling
        back. Assume this is a ``FileBuilder`` object for a root build
        operation.

        Arguments:
            cache_filename (str): The non-norm-cased file used to store
                cached results.
            func (callable): The function. This accepts a
                ``FileBuilder`` as an argument, followed by ``*args``
                and ``**kwargs``.
            args (tuple): The positional arguments to the function,
                apart from the ``FileBuilder``.
            kwargs (dict): The keyword arguments to the function.

        Returns:
            The return value of ``func``.

        Raises:
            OSError: If there was an OS error reading or writing the
                cache file, moving or removing files or directories from
                the previous build, etc.
            Exception: If ``func`` raised an exception.
        """
        cache_file_created_dirs = []
        try:
            # It might be impossible to create the directory for
            # cache_filename. We call _make_dirs early on so that we raise
            # right away if this is impossible. (Also, this prevents build file
            # operations from making the directory creation impossible.)
            cache_file_created_dirs = self._make_dirs(
                os.path.dirname(cache_filename))

            return_value = func(*((self,) + args), **kwargs)
            self._is_finished_build = True
            norm_cased_error_created_dirs = self._set_created_dirs(
                cache_file_created_dirs)

            if (os.path.isfile(cache_filename) and
                    self._backups.back_up_and_remove(cache_filename)):
                logger.info(
                    'Moved cache file {:s} to a temporary directory'.format(
                        cache_filename))
            self._new_cache.write(cache_filename)
            logger.info('Wrote cache file {:s}'.format(cache_filename))
        except Exception:
            self._is_finished_build = True
            self._roll_back(cache_file_created_dirs)
            raise

        self._commit(norm_cased_error_created_dirs)
        return return_value
