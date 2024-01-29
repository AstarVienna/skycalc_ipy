# -*- coding: utf-8 -*-
"""
Based on the skycalc_cli package, but heavily modified.

The original code was taken from ``skycalc_cli`` version 1.1.
Credit for ``skycalc_cli`` goes to ESO
"""

import warnings

import hashlib
import json
from os import environ
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping
from importlib import import_module

import httpx

from astropy.io import fits

from astar_utils import get_logger

CACHE_DIR_FALLBACK = ".astar/skycalc_ipy"
logger = get_logger(__name__)


def get_cache_dir() -> Path:
    """Establish the cache directory.

    There are three possible locations for the cache directory:
    1. As set in `os.environ["SKYCALC_IPY_CACHE_DIR"]`
    2. As set in the `scopesim_data` package.
    3. The `data` directory in this package.
    """
    try:
        dir_cache = Path(environ["SKYCALC_IPY_CACHE_DIR"])
    except KeyError:
        try:
            sim_data = import_module("scopesim_data")
            dir_cache = Path(getattr(sim_data, "dir_cache_skycalc"))
        except (ImportError, AttributeError):
            dir_cache = Path.home() / CACHE_DIR_FALLBACK

    if not dir_cache.is_dir():
        dir_cache.mkdir(parents=True)

    return dir_cache


class ESOQueryBase:
    """Base class for queries to ESO skycalc server."""

    REQUEST_TIMEOUT = 2  # Time limit (in seconds) for server response
    BASE_URL = "https://etimecalret-002.eso.org/observing/etc"

    def __init__(self, url, params):
        self.url = url
        self.params = params

    def _send_request(self) -> httpx.Response:
        try:
            with httpx.Client(base_url=self.BASE_URL,
                              timeout=self.REQUEST_TIMEOUT) as client:
                response = client.post(self.url, json=self.params)
            response.raise_for_status()
        except httpx.RequestError as err:
            logger.exception("An error occurred while requesting %s.",
                             err.request.url)
            raise err
        except httpx.HTTPStatusError as err:
            logger.error("Error response %s while requesting %s.",
                         err.response.status_code, err.request.url)
            raise err
        return response

    def get_cache_filenames(self, prefix: str, suffix: str) -> str:
        """Produce filename from hass of parameters.

        Using three underscores between the key-value pairs and two underscores
        between the key and the value.
        """
        akey = "___".join(f"{k}__{v}" for k, v in self.params.items())
        ahash = hashlib.sha256(akey.encode("utf-8")).hexdigest()
        fname = f"{prefix}_{ahash}.{suffix}"
        return fname


class AlmanacQuery(ESOQueryBase):
    """
    A class for querying the SkyCalc Almanac.

    Parameters
    ----------
    indic : dict, SkyCalcParams
        A dictionary / :class:``SkyCalcParams`` object containing the following
        keywords: ``ra``, ``dec``, ``date`` or ``mjd``

        - ``ra`` : [deg] a float in the range [0, 360]
        - ``dec`` : [deg] a float in the range [-90, 90]

        And either ``data`` or ``mjd``:

        - ``date`` : a datetime string in the format 'yyyy-mm-ddThh:mm:ss'
        - ``mjd`` : a float with the modified julian date. Note that ``mjd=0``
            corresponds to the date "1858-11-17"

    """

    def __init__(self, indic):
        # FIXME: This basically checks isinstance(indic, ui.SkyCalc), but we
        #        can't import that because it would create a circual import.
        # TODO: Find a better way to do this!!
        if hasattr(indic, "defaults"):
            indic = indic.values

        super().__init__("/api//skycalc_almanac", {})

        # Left: users keyword (skycalc_cli),
        # Right: skycalc Almanac output keywords
        self.alm_parameters = {
            "airmass": "target_airmass",
            "msolflux": "sun_aveflux",
            "moon_sun_sep": "moon_sun_sep",
            "moon_target_sep": "moon_target_sep",
            "moon_alt": "moon_alt",
            "moon_earth_dist": "moon_earth_dist",
            "ecl_lon": "ecl_lon",
            "ecl_lat": "ecl_lat",
            "observatory": "observatory",
        }

        # The Almanac needs:
        # coord_ra      : float [deg]
        # coord_dec     : float [deg]
        # input_type    : ut_time | local_civil_time | mjd
        # mjd           : float
        # coord_year    : int
        # coord_month   : int
        # coord_day     : int
        # coord_ut_hour : int
        # coord_ut_min  : int
        # coord_ut_sec  : float

        self._set_date(indic)
        self._set_radec(indic, "ra")
        self._set_radec(indic, "dec")

        if "observatory" in indic:
            self.params["observatory"] = indic["observatory"]

    def _set_date(self, indic):
        if "date" in indic and indic["date"] is not None:
            if isinstance(indic["date"], str):
                isotime = datetime.strptime(indic["date"], "%Y-%m-%dT%H:%M:%S")
            else:
                isotime = indic["date"]

            updated = {
                "input_type": "ut_time",
                "coord_year": isotime.year,
                "coord_month": isotime.month,
                "coord_day": isotime.day,
                "coord_ut_hour": isotime.hour,
                "coord_ut_min": isotime.minute,
                "coord_ut_sec": isotime.second,
                }

        elif "mjd" in indic and indic["mjd"] is not None:
            updated = {
                "input_type": "mjd",
                "mjd": float(indic["mjd"]),
                }

        else:
            raise ValueError("No valid date or mjd given for the Almanac")

        self.params.update(updated)

    def _set_radec(self, indic, which):
        try:
            self.params[f"coord_{which}"] = float(indic[which])
        except KeyError as err:
            logger.exception("%s coordinate not given for the Almanac.", which)
            raise err
        except ValueError as err:
            logger.exception("Wrong %s format for the Almanac.", which)
            raise err

    def _get_jsondata(self, file_path: Path):
        if file_path.exists():
            return json.load(file_path.open(encoding="utf-8"))

        response = self._send_request()
        if not response.text:
            raise ValueError("Empty response.")

        jsondata = response.json()["output"]
        # Use a fixed date so the stored files are always identical for
        # identical requests.
        jsondata["execution_datetime"] = "2017-01-07T00:00:00 UTC"

        try:
            json.dump(jsondata, file_path.open("w", encoding="utf-8"))
            # json.dump(self.params, open(fn_params, 'w'))
        except (PermissionError, FileNotFoundError) as err:
            # Apparently it is not possible to save here.
            raise err

        return jsondata

    def __call__(self):
        """
        Query the ESO Skycalc server with the parameters in self.params.

        Returns
        -------
        almdata : dict
            Dictionary with the relevant parameters for the date given

        """
        cache_dir = get_cache_dir()
        cache_name = self.get_cache_filenames("almanacquery", "json")
        cache_path = cache_dir / cache_name
        jsondata = self._get_jsondata(cache_path)

        # Find the relevant (key, value)
        almdata = {}
        for key, value in self.alm_parameters.items():
            prefix = value.split("_", maxsplit=1)[0]
            if prefix in {"sun", "moon", "target"}:
                subsection = prefix
            elif prefix == "ecl":
                subsection = "target"
            else:
                subsection = "observation"
            try:
                almdata[key] = jsondata[subsection][value]
            except (KeyError, ValueError):
                logger.warning("Key '%s/%s' not found in Almanac response.",
                               subsection, value)

        return almdata

    def query(self):
        """Deprecated feature.

        .. deprecated:: v0.4.0

        This method is deprecated, Class is now callable, use that instead.
        """
        warnings.warn("The .query() method is deprecated and will be removed "
                      "in a future release. Please simply call the instance.",
                      DeprecationWarning, stacklevel=2)
        return self()


class SkyModel(ESOQueryBase):
    """
    Class for querying the Advanced SkyModel at ESO.

    Contains all the parameters needed for querying the ESO SkyCalc server.
    The parameters are contained in :attr:`.params` and the returned FITS file
    is in :attr:`.data` in binary form. This must be saved to disk before it
    can be read with the :meth:`.write` method.

    Parameter and their default values and comments can be found at:
    https://www.eso.org/observing/etc/bin/gen/form?INS.MODE=swspectr+INS.NAME=SKYCALC

    """

    def __init__(self):
        self.data = None
        self.data_url = "/tmp/"
        self.deleter_script_url = "/api/rmtmp"
        self._last_status = ""
        self.tmpdir = ""
        params = {
            # Airmass. Alt and airmass are coupled through the plane parallel
            # approximation airmass=sec(z), z being the zenith distance
            # z=90-Alt
            "airmass": 1.0,  # float range [1.0,3.0]
            # Season and Period of Night
            "pwv_mode": "pwv",  # string  grid ['pwv','season']
            # integer grid [0,1,2,3,4,5,6] (0=all year, 1=dec/jan,2=feb/mar...)
            "season": 0,
            # third of night integer grid [0,1,2,3] (0=all year, 1,2,3 = third
            # of night)
            "time": 0,
            # Precipitable Water Vapor PWV
            # mm float grid [-1.0,0.5,1.0,1.5,2.5,3.5,5.0,7.5,10.0,20.0]
            "pwv": 3.5,
            # Monthly Averaged Solar Flux
            "msolflux": 130.0,  # s.f.u float > 0
            # Scattered Moon Light
            # Moon coordinate constraints: |z - zmoon| <= rho <= |z + zmoon|
            # where rho = moon/target separation, z = 90-target altitude and
            # zmoon = 90-moon altitude.
            # string grid ['Y','N'] flag for inclusion of scattered moonlight.
            "incl_moon": "Y",
            # degrees float range [0.0,360.0] Separation of Sun and Moon as
            # seen from Earth ("moon phase")
            "moon_sun_sep": 90.0,
            # degrees float range [0.0,180.0] Moon-Target Separation ( rho )
            "moon_target_sep": 45.0,
            # degrees float range [-90.0,90.0] Moon Altitude over Horizon
            "moon_alt": 45.0,
            # float range [0.91,1.08] Moon-Earth Distance (mean=1)
            "moon_earth_dist": 1.0,
            # Starlight
            # string  grid ['Y','N'] flag for inclusion of scattered starlight
            "incl_starlight": "Y",
            # Zodiacal light
            # string grid ['Y','N'] flag for inclusion of zodiacal light
            "incl_zodiacal": "Y",
            # degrees float range [-180.0,180.0] Heliocentric ecliptic
            # longitude
            "ecl_lon": 135.0,
            # degrees float range [-90.0,90.0] Ecliptic latitude
            "ecl_lat": 90.0,
            # Molecular Emission of Lower Atmosphere
            # string grid ['Y','N'] flag for inclusion of lower atmosphere
            "incl_loweratm": "Y",
            # Emission Lines of Upper Atmosphere
            # string grid ['Y','N'] flag for inclusion of upper stmosphere
            "incl_upperatm": "Y",
            # Airglow Continuum (Residual Continuum)
            # string grid ['Y','N'] flag for inclusion of airglow
            "incl_airglow": "Y",
            # Instrumental Thermal Emission This radiance component represents
            # an instrumental effect. The emission is provided relative to the
            # other model components. To obtain the correct absolute flux, an
            # instrumental response curve must be applied to the resulting
            # model spectrum See section 6.2.4 in the documentation
            # http://localhost/observing/etc/doc/skycalc/
            # The_Cerro_Paranal_Advanced_Sky_Model.pdf
            # string grid ['Y','N'] flag for inclusion of instrumental thermal
            # radiation
            "incl_therm": "N",
            "therm_t1": 0.0,  # K float > 0
            "therm_e1": 0.0,  # float range [0,1]
            "therm_t2": 0.0,  # K float > 0
            "therm_e2": 0.0,  # float range [0,1]
            "therm_t3": 0.0,  # float > 0
            "therm_e3": 0.0,  # K float range [0,1]
            # Wavelength Grid
            "vacair": "vac",  # vac or air
            "wmin": 300.0,  # nm float range [300.0,30000.0] < wmax
            "wmax": 2000.0,  # nm float range [300.0,30000.0] > wmin
            # string grid ['fixed_spectral_resolution','fixed_wavelength_step']
            "wgrid_mode": "fixed_wavelength_step",
            # nm/step float range [0,30000.0] wavelength sampling step dlam
            # (not the res.element)
            "wdelta": 0.1,
            # float range [0,1.0e6] RESOLUTION is misleading, it is rather
            # lam/dlam where dlam is wavelength step (not the res.element)
            "wres": 20000,
            # Convolve by Line Spread Function
            "lsf_type": "none",  # string grid ['none','Gaussian','Boxcar']
            "lsf_gauss_fwhm": 5.0,  # wavelength bins float > 0
            "lsf_boxcar_fwhm": 5.0,  # wavelength bins float > 0
            "observatory": "paranal",  # paranal
        }

        super().__init__("/api/skycalc", params)

    def fix_observatory(self):
        """
        Convert the human readable observatory name into its ESO ID number.

        The following observatory names are accepted: ``lasilla``, ``paranal``,
        ``armazones`` or ``3060m``, ``highanddry`` or ``5000m``

        """
        # FIXME: DO WE ALWAYS WANT TO RAISE WHEN IT'S NOT ONE OF THOSE???
        if self.params["observatory"] not in {
            "paranal",
            "lasilla",
            "armazones",
            "3060m",
            "5000m",
        }:
            return  # nothing to do

        if self.params["observatory"] == "lasilla":
            self.params["observatory"] = "2400"
        elif self.params["observatory"] == "paranal":
            self.params["observatory"] = "2640"
        elif (
            self.params["observatory"] == "3060m"
            or self.params["observatory"] == "armazones"
        ):
            self.params["observatory"] = "3060"
        elif (
            self.params["observatory"] == "5000m"
            or self.params["observatory"] == "highanddry"
        ):
            self.params["observatory"] = "5000"
        else:
            raise ValueError(
                "Wrong Observatory name, please refer to the documentation."
            )
        return  # for consistency

    def __getitem__(self, item):
        return self.params[item]

    def __setitem__(self, key, value):
        self.params[key] = value
        if key == "observatory":
            self.fix_observatory()

    def _retrieve_data(self, url):
        try:
            self.data = fits.open(url)
            # Use a fixed date so the stored files are always identical for
            # identical requests.
            self.data[0].header["DATE"] = "2017-01-07T00:00:00"
        except Exception as err:
            logger.exception(
                "Exception raised trying to get FITS data from %s", url)
            raise err

    def write(self, local_filename, **kwargs):
        """Write data to file."""
        try:
            self.data.writeto(local_filename, **kwargs)
        except (IOError, FileNotFoundError):
            logger.exception("Exception raised trying to write fits file.")

    def getdata(self):
        """Deprecated feature.

        .. deprecated:: v0.4.0

        This method is deprecated, just use the .data attribute instead.
        """
        warnings.warn("The .getdata method is deprecated and will be removed "
                      "in a future release. Use the identical .data attribute "
                      "instead.", DeprecationWarning, stacklevel=2)
        return self.data

    def _delete_server_tmpdir(self, tmpdir):
        try:
            with httpx.Client(base_url=self.BASE_URL,
                              timeout=self.REQUEST_TIMEOUT) as client:
                response = client.get(self.deleter_script_url,
                                      params={"d": tmpdir})
            deleter_response = response.text.strip().lower()
            if deleter_response != "ok":
                logger.error("Could not delete server tmpdir %s: %s",
                             tmpdir, deleter_response)
        except httpx.HTTPError:
            logger.exception("Exception raised trying to delete tmp dir %s",
                             tmpdir)

    def _update_params(self, updated: Mapping) -> None:
        par_keys = self.params.keys()
        new_keys = updated.keys()
        self.params.update((key, updated[key]) for key in par_keys & new_keys)
        logger.debug("Ignoring invalid keywords: %s", new_keys - par_keys)

    def __call__(self, **kwargs):
        """Send server request."""
        if kwargs:
            logger.info("Setting new parameters: %s", kwargs)

        self._update_params(kwargs)
        self.fix_observatory()

        cache_dir = get_cache_dir()
        cache_name = self.get_cache_filenames("skymodel", "fits")
        cache_path = cache_dir / cache_name

        if cache_path.exists():
            self.data = fits.open(cache_path)
            return

        response = self._send_request()

        try:
            res = response.json()
            status = res["status"]
            tmpdir = res["tmpdir"]
        except (KeyError, ValueError) as err:
            logger.exception(
                "Exception raised trying to decode server response.")
            raise err

        self._last_status = status

        if status == "success":
            try:
                # retrive and save FITS data (in memory)
                self._retrieve_data(
                    self.BASE_URL + self.data_url + tmpdir + "/skytable.fits")
            except httpx.HTTPError as err:
                logger.exception("Could not retrieve FITS data from server.")
                raise err

            try:
                self.data.writeto(cache_path)
                # with fn_params.open("w", encoding="utf-8") as file:
                #     json.dump(self.params, file)
            except (PermissionError, FileNotFoundError):
                # Apparently it is not possible to save here.
                pass

            self._delete_server_tmpdir(tmpdir)

        else:  # print why validation failed
            logger.error("Parameter validation error: %s", res["error"])

    def call(self):
        """Deprecated feature.

        .. deprecated:: v0.4.0

        This method is deprecated, just call the instance instead.
        """
        warnings.warn("The .call() method is deprecated and will be removed "
                      "in a future release. Please simply call the instance.",
                      DeprecationWarning, stacklevel=2)
        self()

    def callwith(self, newparams):
        """Deprecated feature.

        .. deprecated:: v0.4.0

        This method is deprecated, just call the instance instead.
        """
        warnings.warn("The .callwith(args) method is deprecated and will be "
                      "removed in a future release. Please simply call the "
                      "instance with optional kwargs instead.",
                      DeprecationWarning, stacklevel=2)
        self(**newparams)

    def printparams(self, keys=None):
        """
        List the values of all, or a subset, of parameters.

        Parameters
        ----------
        keys : sequence of str, optional
            List of keys to print. If None, all keys will be printed.

        """
        for key in keys or self.params.keys():
            print(f"  {key}: {self.params[key]}")
