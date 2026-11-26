"""Course builder: turns a GPX route and LiDAR DTM files into a course folder for the ride.

    python -m tools.coursebuilder build --id my-loop --name "My Loop" --route my-loop.gpx --dtm dtm/ ...

See docs/refactor-plan.md ("Course builder") and `python -m tools.coursebuilder --help`.
"""


class BuildError(Exception):
    """A problem with the inputs, explained for the person running the builder."""
