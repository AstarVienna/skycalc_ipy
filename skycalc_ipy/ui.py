import os
import inspect
import yaml
import numpy as np


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
                print(pname, "not found")
            else:
                print(self.comments[pname])

    def validate_params(self):

        valid = True
        invalid_keys = []
        for key in self.values:

            if self.check_type[key] in ["range", "nearest"]:
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

        if not valid:
            print("See <SkyCalcParams>.comments[<key>] for help")
            print("The following entries are invalid:")
            for key in invalid_keys:
                print("'{}' : {} :".format(key, self.values[key]),
                      self.comments[key])

        return valid

    @property
    def keys(self):
        return list(self.defaults.keys())

    def __setitem__(self, key, value):
        if key not in self.keys:
            raise ValueError(key+" not in self.defaults")
        self.values[key] = value

    def __getitem__(self, item):
        return self.values[item]


def load_yaml(ipt_str):

    if ipt_str[-4:].lower() == "yaml":
        if not os.path.exists(ipt_str):
            raise ValueError(ipt_str + " not found")

        with open(ipt_str, "r") as fd:
            fd = "\n".join(fd.readlines())
        opts_dict = yaml.load(fd)
    else:
        opts_dict = yaml.load(ipt_str)

    return opts_dict
