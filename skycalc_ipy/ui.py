# -*- coding: utf-8 -*-
"""Skyclc IPY user interface."""

import warnings
from pathlib import Path
from datetime import datetime as dt

import yaml
import numpy as np

from astropy import units as u
from astropy.io import fits

from astar_utils import get_logger

from .core import AlmanacQuery, SkyModel

__all__ = ["SkyCalc"]

# TODO: this isn't used, but something VERY similar is done in core......
observatory_dict = {
    "lasilla": "2400",
    "paranal": "2640",
    "3060m": "3060",
    "armazones": "3060",
    "5000m": "5000",
    "highanddry": "5000",
}

PATH_HERE = Path(__file__).parent
logger = get_logger(__name__)


class SkyCalc:
    """Main UI class."""

    def __init__(self, ipt_str=None):
        if ipt_str is None:
            ipt_str = PATH_HERE / "params.yaml"

        params = load_yaml(ipt_str)

        self.defaults = {pp: params[pp][0] for pp in params}
        self.values = {pp: params[pp][0] for pp in params}
        self.data_type = {pp: params[pp][1] for pp in params}
        self.check_type = {pp: params[pp][2] for pp in params}
        self.allowed = {pp: params[pp][3] for pp in params}
        self.comments = {pp: params[pp][4] for pp in params}

        self.last_skycalc_response = None

    def print_comments(self, *param_names):
        """Print descriptions of parameters. Print all if no names given."""
        param_names = param_names or list(self.comments.keys())
        maxkeylen = len(max(param_names, key=len))

        for pname in param_names:
            comment = self.comments.get(pname, "<parameter not found>")
            print(f"{pname:>{maxkeylen}} : {comment}")

    def validate_params(self):
        """Check allowed range for parameters."""
        invalid_keys = []
        for key in self.values:
            if self.check_type[key] == "no_check" or self.defaults[key] is None:
                continue

            if self.check_type[key] in {"range", "nearest"}:
                if (
                    self.values[key] < self.allowed[key][0]
                    or self.values[key] > self.allowed[key][-1]
                ):
                    invalid_keys.append(key)

                    if self.check_type[key] == "nearest":
                        nearest = np.argmin(np.abs(self.allowed[key]
                                                   - self.values[key]))
                        self.values[key] = self.allowed[key][nearest]

            elif self.check_type[key] in {"choice", "flag"}:
                if self.values[key] not in self.allowed[key]:
                    invalid_keys.append(key)

            elif self.check_type[key] == "greater_than":
                if self.values[key] < self.allowed[key]:
                    invalid_keys.append(key)

        if invalid_keys:
            logger.warning("The following entries are invalid:")
            for key in invalid_keys:
                logger.warning("'%s' : %s : %s", key,
                               self.values[key], self.comments[key])

        return not invalid_keys

    def get_almanac_data(
        self,
        ra,
        dec,
        date=None,
        mjd=None,
        observatory=None,
        update_values=False,
    ):
        """Query ESO Almanac with given parameters."""
        if date is None and mjd is None:
            raise ValueError("Either date or mjd must be set")

        result = get_almanac_data(
            ra=ra, dec=dec, date=date, mjd=mjd, observatory=observatory
        )
        if update_values:
            self.values.update(result)

        return result

    def get_sky_spectrum(self, return_type="table", filename=None):
        """
        Retrieve a fits.HDUList object from the SkyCalc server.

        The HDUList can be returned in a variety of formats.

        As of v0.1.3 the HDUList is no longer saved to disk.
        Rather it is stored in the attribute <SkyCalc>.last_skycalc_response.

        Parameters
        ----------
        return_type : str
            ["table", "array", "synphot", "fits"]
        filename : str, optional
            Default None. If not None, the returned fits.HDUList object is
            saved to disk under this path.

        Returns
        -------
        Based on the return type, the method returns either:
        - "table": tbl_return (astropy.Table)
        - "array": wave, trans, flux (3x np.ndarray)
        - "synphot": trans, flux (SpectralElement, SourceSpectrum,)
        - "fits": hdu (HDUList)

        """
        from astropy import table

        if not self.validate_params():
            raise ValueError(
                "Object contains invalid parameters. Not calling ESO")

        skm = SkyModel()
        skm(**self.values)
        self.last_skycalc_response = skm.data
        if filename is not None:
            skm.write(filename)

        tbl = table.Table.read(skm.data)
        if tbl["lam"].unit is None:
            tbl["lam"].unit = u.um

        # Set formatting to reasonable precision
        tbl["lam"].format = "%.2f"
        tbl["trans"].format = "%.5f"
        tbl["flux"].format = "%.3f"

        for colname in tbl.colnames:
            if "flux" in colname:
                # Somehow, astropy doesn't quite parse the unit correctly.
                # Still, we shouldn't blindly overwrite it, so at least check.
                funit = tbl[colname].unit
                if str(funit) not in ("ph/s/m2/micron/arcsec2", "None"):
                    raise ValueError(f"Unexpected flux unit: {funit}")
                tbl[colname].unit = u.Unit("ph s-1 m-2 um-1 arcsec-2")

        date_created = dt.now().strftime("%Y-%m-%dT%H:%M:%S")
        meta_data = {
            "DESCRIPT": "Sky transmission and emission curves",
            "SOURCE": "ESO Skycalc utility",
            "AUTHOR": "ESO Skycalc utility",
            "STATUS": "Tested - Generated from ESO Skycalc utility",
            "DATE_CRE": date_created,
            "ETYPE": "TERCurve",
            "EDIM": 1,
        }

        params = {k: (self.values[k], self.comments[k]) for k in self.keys}
        meta_data.update(params)

        if "tab" in return_type:
            tbl.meta.update(meta_data)

            if "ext" in return_type:
                tbl_return = tbl
            else:
                tbl_small = table.Table()
                tbl_small.add_columns([tbl["lam"], tbl["trans"], tbl["flux"]])
                tbl_return = tbl_small

            return tbl_return

        if "arr" in return_type:
            wave = tbl["lam"].data * tbl["lam"].unit
            trans = tbl["trans"].data
            flux = tbl["flux"].data * tbl["flux"].unit

            return wave, trans, flux

        if "syn" in return_type:
            import synphot as sp

            trans = sp.SpectralElement(
                sp.Empirical1D,
                points=tbl["lam"].data * tbl["lam"].unit,
                lookup_table=tbl["trans"].data,
            )

            funit = u.Unit("ph s-1 m-2 um-1")
            flux = sp.SourceSpectrum(
                sp.Empirical1D,
                points=tbl["lam"].data * tbl["lam"].unit,
                lookup_table=tbl["flux"].data * funit,
            )
            logger.warning(
                "Synphot doesn't accept surface brightnesses \n"
                "The resulting spectrum should be multiplied by arcsec-2"
            )

            return trans, flux

        if "fit" in return_type:
            hdu0 = fits.PrimaryHDU()
            for key, meta_data_value in meta_data.items():
                hdu0.header[key] = meta_data_value
            hdu1 = fits.table_to_hdu(tbl)
            hdu = fits.HDUList([hdu0, hdu1])

            return hdu

    def update(self, kwargs):
        self.values.update(kwargs)

    def __setitem__(self, key, value):
        if key not in self.keys:
            raise KeyError(f"Key {key} is not defined. Only predefined keys "
                           "can be set. See SkyCalc.keys for a list of those.")
        self.values[key] = value

    def __getitem__(self, item):
        return self.values[item]

    @property
    def keys(self):
        return list(self.defaults.keys())


def load_yaml(ipt_str):
    # TODO: why not just load, what's all of this?
    if ".yaml" in str(ipt_str).lower():
        if not ipt_str.exists():
            raise ValueError(f"{ipt_str} not found")

        with ipt_str.open("r", encoding="utf-8") as fd:
            fd = "\n".join(fd.readlines())
        opts_dict = yaml.load(fd, Loader=yaml.FullLoader)
    else:
        opts_dict = yaml.load(ipt_str, Loader=yaml.FullLoader)

    return opts_dict


def get_almanac_data(
    ra,
    dec,
    date=None,
    mjd=None,
    return_full_dict=False,
    observatory=None,
):
    if date is not None and mjd is not None:
        warnings.warn("Both date and mjd are set. Using date",
                      UserWarning, stacklevel=2)

    skycalc_params = SkyCalc()
    skycalc_params.values.update(
        {"ra": ra, "dec": dec, "date": date, "mjd": mjd})
    if observatory is not None:
        skycalc_params.values["observatory"] = observatory
    skycalc_params.validate_params()
    response = AlmanacQuery(skycalc_params.values)()

    if return_full_dict:
        skycalc_params.values.update(response)
        return skycalc_params.values

    return response
