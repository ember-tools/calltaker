"""The two roles that look at an exercise."""

from enum import StrEnum


class Rolle(StrEnum):
    """Who looks at an exercise."""

    AUSBILDER = "ausbilder"
    TRAINEE = "trainee"
