import warnings as _warnings
from astropy.utils.exceptions import AstropyWarning as _AstropyWarning

_warnings.simplefilter("ignore", category=_AstropyWarning)

from . import ui
from . import core

from .ui import SkyCalc

from logging import NullHandler
from astar_utils import get_logger

_logger = get_logger(__package__)
_logger.addHandler(NullHandler())

from importlib import metadata

__version__ = metadata.version(__package__)
