import warnings as _warnings
from astropy.utils.exceptions import AstropyWarning as _AstropyWarning
_warnings.simplefilter('ignore', category=_AstropyWarning)

from . import ui
from . import core

from .ui import SkyCalc