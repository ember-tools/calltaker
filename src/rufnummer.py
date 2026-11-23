"""Phone numbers as the dispatch system records them: digits only, with the country code.

Grouping a number for display is the frontend's business; the server only stores and compares.
"""

import re

LANDESVORWAHL = "49"


def normalisieren(text: str) -> str:
    """Return a number typed in any common way as digits with the country code.

    `0176 1234567`, `+49 176 1234567`, `+49 (0)176 1234567`, `0049-176-1234567` and
    `491761234567` all become `491761234567`; a number without a leading zero or country code is
    taken as it stands.
    """
    ziffern = re.sub(r"\D", "", text.replace("(0)", ""))
    if ziffern.startswith("00"):
        ziffern = ziffern[2:]
    elif ziffern.startswith("0"):
        ziffern = LANDESVORWAHL + ziffern[1:]
    if ziffern.startswith(LANDESVORWAHL + "0"):
        ziffern = LANDESVORWAHL + ziffern[len(LANDESVORWAHL) + 1 :]
    return ziffern
