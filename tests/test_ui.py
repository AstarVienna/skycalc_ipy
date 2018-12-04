import os
import inspect
from pytest import raises
from skycalc_ipy import ui
# Mocks
skp = ui.SkyCalcParams()


class TestLoadYaml:
    def test_finds_default_file(self):
        yaml_dict = ui.load_yaml()
        assert yaml_dict["season"][0] == 0

    def test_finds_file_for_specified_path(self):
        dirname = os.path.dirname(inspect.getfile(inspect.currentframe()))
        yaml_dict = ui.load_yaml(os.path.join(dirname, "../skycalc_ipy",
                                              "params.yaml"))
        assert yaml_dict["season"][0] == 0


    def test_throws_exception_for_nonexistent_file(self):
        with raises(ValueError):
            ui.load_yaml("bogus.yaml")

    def test_accepts_string_block_input(self):
        str_yaml = """
        params : 
        - hello
        - world
        """
        yaml_dict = ui.load_yaml(str_yaml)
        assert yaml_dict["params"] == ["hello", "world"]


class TestSkycalcParamsMisc:
    def test_loads_default_when_no_file_given(self):
        assert type(skp.defaults) == dict
        assert skp.defaults["observatory"] == "paranal"
        assert skp.allowed["therm_t2"] == 0

    def test_print_comments_single_keywords(self, capsys):
        skp.print_comments("airmass")
        output = capsys.readouterr()[0].strip()
        assert output == "airmass in range [1.0, 3.0]"

    def test_print_comments_mutliple_keywords(self, capsys):
        skp.print_comments(["airmass", "season"])
        output = capsys.readouterr()[0].strip()
        assert output == "airmass in range [1.0, 3.0]\n" + \
                         "0=all year, 1=dec/jan,2=feb/mar..."

    def test_print_comments_misspelled_keyword(self, capsys):
        skp.print_comments(["iarmass"])
        output = capsys.readouterr()[0].strip()
        assert output == "iarmass not found"

    def test_keys_returns_list_of_keys(self):
        assert type(skp.keys) == list
        assert "observatory" in skp.keys


class TestSkycalcParamsValidateMethod(object):
    def test_returns_True_for_all_good(self):
        assert skp.validate_params() is True

    def test_returns_false_for_bung_YN_flag(self):
        skp["incl_starlight"] = "Bogus"
        assert skp.validate_params() is False

    def test_returns_false_for_bung_string_in_array(self):
        skp["lsf_type"] = "Bogus"
        assert skp.validate_params() is False

    def test_returns_false_for_value_outside_range(self):
        skp["airmass"] = 0.5
        assert skp.validate_params() is False

    def test_returns_false_for_value_below_zero(self):
        skp["lsf_boxcar_fwhm"] = -5.
        assert skp.validate_params() is False
