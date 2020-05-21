from enum import Enum


class FileComparison(Enum):
    """A method for comparing a file at two points in time.

    ``FileBuilder`` uses file comparison to determine whether an input
    or output file has changed since the last build, in which case the
    relevant cache entries are invalid.

    Enum values:

    * ``METADATA``: Indicates comparing a file using its metadata:
      specifically, its modification time and its size in bytes. This
      method is recommended for most use cases. Although it is possible
      to incorrectly conclude that a file has changed (or even to
      incorrectly conclude that a file has not changed), this is a fast
      and normally accurate means of comparison.
    * ``HASH``: Indicates comparing a file using a SHA-256 hash of its
      contents. This is very likely to produce a correct comparison
      result. However, it's relatively slow, because it requires reading
      the entire file.
    """

    METADATA = 1
    HASH = 2
