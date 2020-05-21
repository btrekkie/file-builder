class Operation:
    """A cacheable record of an operation occurring during a build.

    ``Operation`` is an abstract base class. There are two types of
    operations: simple operations and complex operations. A simple
    operation is a "primitive" file system operation, exposed through a
    public ``FileBuilder`` method. Simple operations include the "is
    file" and "walk" operations.

    A complex operation is a subbuild or build file operation. They are
    complex in that they may consist of calls to other operations.
    Unlike a subbuild, a build is not an operation, because it isn't
    cacheable.

    An ``Operation`` record stores a description of what operation is
    being performed along with the results of the operation. An
    operation may currently be in progress, in which case some of its
    result fields might not be filled in yet.

    See the comments for ``FileBuilder``.

    Public attributes:

    * ``list args``: The operation's positional arguments. In the case
      of a complex operation, this only includes the "declared"
      positional arguments; it does not include the function name,
      ``FileBuilder``, or filename.
    * ``bool is_finished``: Whether the operation has completed. If this
      is set to ``True``, then further modifications to the operation
      record are forbidden.
    * ``object return_value``: The operation's return value. This is
      ``None`` if the operation hasn't returned yet or it resulted in an
      exception.
    """

    def __init__(self, args, return_value, is_finished):
        self.args = args
        self.return_value = return_value
        self.is_finished = is_finished


class SimpleOperation(Operation):
    """A record of a simple operation.

    See the comments for ``Operation``.

    Public attributes:

    * ``str exception_type_str``: The name of the exception type that
      this operation raised, e.g. ``'FileNotFoundError'``. This is
      ``None`` if the operation didn't result in an exception or the
      operation hasn't finished yet.
    * ``str name``: The operation's name, as in
      ``SimpleOperationExecutor.OPERATIONS``.
    """

    def __init__(
            self, name, args, return_value=None, exception_type_str=None,
            is_finished=False):
        super().__init__(args, return_value, is_finished)
        self.name = name
        self.exception_type_str = exception_type_str


class ComplexOperation(Operation):
    """A record of a complex operation.

    This is an abstract class. See the comments for ``Operation``.

    Public attributes:

    * ``str func_name``: The name of the function we call to execute the
      operation.
    * ``dict<str, object> kwargs``: The keyword arguments to the
      function.
    * ``bool raised``: Whether the operation resulted in an exception.
      This is ``None`` if the operation hasn't finished yet. It is
      ``True`` if ``setup_failed`` is ``True``.

      If a build file or subbuild function raises an exception, we don't
      cache it, because it is impossible to reliably recreate an
      arbitrary exception object. However, it may still be possible to
      reuse a cache record for such an operation if another build file
      or subbuild function catches the exception.
    * ``bool setup_failed``: Whether an exception occurred during
      "setup": after validating the arguments' types, but before calling
      the function passed in as an argument or reusing a cached result.
      This is ``False`` if the operation hasn't finished yet.
    * ``list<Operation> suboperations``: The operations that this
      ``ComplexOperation`` has called so far, in order. The
      ``is_finished`` fields of all of the suboperations must be
      ``True``.
    """

    def __init__(
            self, func_name, args, kwargs, suboperations, return_value, raised,
            setup_failed, is_finished):
        super().__init__(args, return_value, is_finished)
        self.func_name = func_name
        self.kwargs = kwargs
        self.suboperations = suboperations
        self.raised = raised
        self.setup_failed = setup_failed


class BuildFileOperation(ComplexOperation):
    """A record of a build file operation.

    See the comments for ``Operation``.

    Public attributes:

    * ``FileComparison file_comparison``: The comparison used to compare
      the output file.
    * ``object file_comparison_result``: The result of the comparison
      used to compare the output file, as in
      ``SimpleOperationExecutor.file_comparison_result``. This is
      ``None`` if the operation hasn't returned yet or it resulted in an
      exception.
    * ``str filename``: The file being built.
    """

    def __init__(
            self, filename, file_comparison, func_name, args, kwargs,
            suboperations, return_value, file_comparison_result, raised,
            setup_failed, is_finished):
        super().__init__(
            func_name, args, kwargs, suboperations, return_value, raised,
            setup_failed, is_finished)
        self.filename = filename
        self.file_comparison = file_comparison
        self.file_comparison_result = file_comparison_result


class SubbuildOperation(ComplexOperation):
    """A record of a subbuild operation.

    See the comments for ``Operation``.
    """

    pass
