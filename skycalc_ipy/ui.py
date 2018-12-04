import os
import inspect
from copy import deepcopy
import yaml
import numpy as np

from .core import AlmanacQuery

#__all__ = [SkyCalcParams]

class SkyCalcParams:

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
            if pname not in self.comments.keys():
                print(pname + " not found")
            else:
                print(self.comments[pname])

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
            print("See <SkyCalcParams>.comments[<key>] for help")
            print("The following entries are invalid:")
            for key in invalid_keys:
                print("'{}' : {} :".format(key, self.values[key]),
                      self.comments[key])

        return valid

    def get_almanac_data(self, ra, dec, date=None, mjd=None,
                            update_values=False):

        response = get_almanac_data(ra, dec, date, mjd, update_values)
        if update_values:
            self.values.update(response)

        return response


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


def get_almanac_data(ra, dec, date=None, mjd=None, return_full_dict=False):

    skycalc_params = SkyCalcParams()
    skycalc_params.values.update({"ra": ra, "dec": dec,
                                  "date": date, "mjd": mjd})
    alm = AlmanacQuery(skycalc_params.values)
    response = alm.query()

    if return_full_dict:
        skycalc_params.values.update(response)
        return skycalc_params.values
    else:
        return response
