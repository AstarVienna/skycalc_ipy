import os
import inspect
from copy import deepcopy
from datetime import datetime as dt

import yaml
import numpy as np

from astropy import units as u
from astropy.io import fits

from .core import AlmanacQuery, SkyModel

__all__ = ["SkyCalc"]

observatory_dict = {"lasilla"   : "2400",
                    "paranal"   : "2640",
                    "3060m"     : "3060",
                    "armazones" : "3060",
                    "5000m"     : "5000",
                    "highanddry": "5000"}


class SkyCalc:

    def __init__(self, ipt_str=None):

        if ipt_str is None:
            dirname = os.path.dirname(inspect.getfile(inspect.currentframe()))
            ipt_str = os.path.join(dirname, "params.yaml")

        params = load_yaml(ipt_str)

        self.defaults   = {pp : params[pp][0] for pp in params}
        self.values     = {pp : params[pp][0] for pp in params}
        self.data_type  = {pp : params[pp][1] for pp in params}
        self.check_type = {pp : params[pp][2] for pp in params}
        self.allowed    = {pp : params[pp][3] for pp in params}
        self.comments   = {pp : params[pp][4] for pp in params}

    def print_comments(self, param_names=None):

        if param_names is None:
            param_names = list(self.comments.keys())

        if type(param_names) is str:
            param_names = [param_names]

        for pname in param_names:
            if pname not in self.comments:
                msg = pname + " not found"
                print(msg)
            else:
                print("{} : {}".format(pname, self.comments[pname]))

    def validate_params(self):

        valid = True
        invalid_keys = []
        for key in self.values:

            if self.check_type[key] == "no_check" or self.defaults[key] is None:
                continue

            elif self.check_type[key] in ["range", "nearest"]:
                if self.values[key] < self.allowed[key][0] or \
                   self.values[key] > self.allowed[key][-1]:
                    valid = False
                    invalid_keys += [key]

                    if self.check_type[key] == "nearest":
                        ii = np.argmin(np.abs(self.allowed[key] -
                                              self.values[key]))
                        self.values[key] = self.allowed[key][ii]

            elif self.check_type[key] in ["choice", "flag"]:
                if self.values[key] not in self.allowed[key]:
                    valid = False
                    invalid_keys += [key]

            elif self.check_type[key] == "greater_than":
                if self.values[key] < self.allowed[key]:
                    valid = False
                    invalid_keys += [key]

            else:
                pass

        if not valid:
            print("See <SkyCalc>.comments[<key>] for help")
            print("The following entries are invalid:")
            for key in invalid_keys:
                print("'{}' : {} :".format(key, self.values[key]),
                      self.comments[key])

        return valid


    def get_almanac_data(self, ra, dec, date=None, mjd=None,
                         observatory=None, update_values=False):

        if date is None and mjd is None:
            raise ValueError("Either date or mjd must be set")

        result = get_almanac_data(ra=ra, dec=dec, date=date, mjd=mjd,
                                  observatory=observatory)
        if update_values:
            self.values.update(result)

        return result


    def get_sky_spectrum(self, return_type="table", filename=None):

        from astropy import table

        if filename is None:
            filename = "skycalc_temp.fits"

        if not self.validate_params():
            raise ValueError("Object contains invalid parameters. "
                             "Not calling ESO")

        skm = SkyModel()
        skm.callwith(self.values)
        skm.write(filename)

        with fits.open(filename) as hdu:

            tbl = table.Table(hdu[1].data)
            tbl["lam"].unit = u.um
            for colname in tbl.colnames:
                if "flux" in colname:
                    tbl[colname].unit = u.Unit("ph s-1 m-2 um-1 arcsec-2")

        date_created = dt.now().strftime('%Y-%m-%dT%H:%M:%S')
        meta_data = {"DESCRIPT": "Sky transmission and emission curves",
                     "SOURCE": "ESO Skycalc utility",
                     "AUTHOR": "ESO Skycalc utility",
                     "STATUS": "Tested - Generated from ESO Skycalc utility",
                     "DATE_CRE": date_created,
                     "ETYPE": "TERCurve",
                     "EDIM": 1}

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

        elif "arr" in return_type:

            wave  = tbl["lam"].data * tbl["lam"].unit
            trans = tbl["trans"].data
            flux  = tbl["flux"].data * tbl["flux"].unit

            return wave, trans, flux

        elif "syn" in return_type:
            import synphot as sp

            trans = sp.SpectralElement(sp.Empirical1D,
                                      points=tbl["lam"].data*tbl["lam"].unit,
                                      lookup_table=tbl["trans"].data)

            funit = u.Unit("ph s-1 m-2 um-1")
            flux = sp.SourceSpectrum(sp.Empirical1D,
                                     points=tbl["lam"].data * tbl["lam"].unit,
                                     lookup_table=tbl["flux"].data*funit)
            print("Warning: synphot doesn't accept surface brightnesses \n"
                  "The resulting spectrum should be multiplied by arcsec-2")

            return trans, flux

        elif "fit" in return_type:

            hdu0 = fits.PrimaryHDU()
            for key in meta_data:
                hdu0.header[key] = meta_data[key]
            hdu1 = fits.table_to_hdu(tbl)
            hdu = fits.HDUList([hdu0, hdu1])

            return hdu


    def update(self, kwargs):
        self.values.update(kwargs)

    def __setitem__(self, key, value):
        if key not in self.keys:
            raise ValueError(key+" not in self.defaults")
        self.values[key] = value

    def __getitem__(self, item):
        return self.values[item]

    @property
    def keys(self):
        return list(self.defaults.keys())


def load_yaml(ipt_str):

    if ".yaml" in ipt_str.lower():
        if not os.path.exists(ipt_str):
            raise ValueError(ipt_str + " not found")

        with open(ipt_str, "r") as fd:
            fd = "\n".join(fd.readlines())
        opts_dict = yaml.load(fd)
    else:
        opts_dict = yaml.load(ipt_str)

    return opts_dict


def get_almanac_data(ra, dec, date=None, mjd=None, return_full_dict=False,
                     observatory=None):

    if date is not None and mjd is not None:
        print("Warning: Both date and mjd are set. Using date")

    skycalc_params = SkyCalc()
    skycalc_params.values.update({"ra": ra, "dec": dec,
                                  "date": date, "mjd": mjd})
    if observatory is not None:
        skycalc_params.values["observatory"] = observatory
    skycalc_params.validate_params()
    alm = AlmanacQuery(skycalc_params.values)
    response = alm.query()

    if return_full_dict:
        skycalc_params.values.update(response)
        return skycalc_params.values
    else:
        return response


# def fix_observatory(in_dict):
#
#     if isinstance(in_dict, SkyCalc):
#         in_dict = in_dict.values
#
#     if "observatory" in in_dict and in_dict["observatory"] in observatory_dict:
#         in_dict["observatory_orig"] = deepcopy(in_dict["observatory"])
#         in_dict["observatory"] = observatory_dict[in_dict["observatory"]]
#     else:
#         raise ValueError("Wrong Observatory name. "
#                          "See `skycalc.ui.observatory_dict`")
#
#     return in_dict