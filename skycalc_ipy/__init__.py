import warnings as _warnings
from astropy.utils.exceptions import AstropyWarning as _AstropyWarning

_warnings.simplefilter("ignore", category=_AstropyWarning)

from . import ui
from . import core

from .ui import SkyCalc

import logging
logger = logging.getLogger("astar." + __name__)
logger.addHandler(logging.NullHandler())

################################################################################
#                          VERSION INFORMATION                                 #
################################################################################

try:
    from .version import version as __version__
except ImportError:
    __version__ = "Version number is not available"
