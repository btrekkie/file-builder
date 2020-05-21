`samples/parallel_seam_carving` is a sample project for the "file-builder"
library. It demonstrates one possible approach to parallelizing a build.
Parallelism can speed up a build by making use of multiple CPUs or cores, or
more generally by using hardware resources when they would otherwise be idle.

In `parallel_seam_carving`, the build file functions are CPU intensive, so we
run them in parallel. To do so, we create a `ThreadPoolExecutor` and a
`ProcessPoolExecutor`. We wrap the calls to `FileBuilder.build_file` in threads
in the `ThreadPoolExecutor`, and we offload the main work of the build file
function to separate processes in the `ProcessPoolExecutor`. The use of separate
processes is a workaround for the global interpreter lock; see
<https://wiki.python.org/moin/GlobalInterpreterLock>.

`parallel_seam_carving` provides a `ParallelSeamCarveBuilder.build` method,
which reduces the width-to-height ratio of all of the image files in a given
input directory (including subdirectories) using seam carving. For each image
file in the input directory, `ParallelSeamCarveBuilder.build` creates a smaller
image file in the output directory with the same name. It creates a directory
structure in the output directory that matches the directory structure in the
input directory.

Seam carving is an algorithm for content-aware image resizing, which carves out
pieces of an image that are low energy (i.e. not content rich). Visually, the
results of `parallel_seam_carving`'s implementation of seam carving are not very
impressive, because it uses a simplistic energy function. The sample is not
intended to produce good-looking visuals, but to demonstrate the use of
parallelism in `FileBuilder`.

`parallel_seam_carving` also provides a non-parallel method
`SerialSeamCarveBuilder.build` that has the same behavior as
`ParallelSeamCarveBuilder.build`, for purposes of comparison.
