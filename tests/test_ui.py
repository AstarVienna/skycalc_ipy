from pytest import raises
from skycalc_ipy import ui

### Mocks
skp = ui.SkyCalcParams()

def test_load_yaml_finds_file():
    yaml_dict = ui.load_yaml("params.yaml")
    assert yaml_dict["season"][0] == 0

def test_load_yaml_throws_exception_for_nonexistent_file():
    with raises(ValueError):
        ui.load_yaml("bogus.yaml")

def test_load_yaml_accepts_string_block_input():
    str_yaml = """
    params : 
    - hello
    - world
    """
    yaml_dict = ui.load_yaml(str_yaml)
    assert yaml_dict["params"] == ["hello", "world"]

def test_skycalcparams_loads_default_when_no_file_given():
    assert type(skp.defaults) == dict
    assert skp.defaults["observatory"] == "paranal"
    assert skp.allowed["therm_t2"] == 0

def test_skycalcparams_print_comments_single_keywords(capsys):
    skp.print_comments("airmass")
    output = capsys.readouterr()[0].strip()
    assert output == "airmass in range [1.0, 3.0]"

def test_skycalcparams_print_comments_mutliple_keywords(capsys):
    skp.print_comments(["airmass", "season"])
    output = capsys.readouterr()[0].strip()
    assert output == "airmass in range [1.0, 3.0]\n" + \
                     "0=all year, 1=dec/jan,2=feb/mar..."

def test_skycalcparams_print_comments_misspelled_keyword(capsys):
    skp.print_comments(["iarmass"])
    output = capsys.readouterr()[0].strip()
    assert output == "iarmass not found"

def test_skycalcparams_keys_returns_list_of_keys():
    assert type(skp.keys) == list
    assert "observatory" in skp.keys

def test_skycalcparams_validate_returns_True_for_all_good():
    assert skp.validate_params() is True

def test_skycalcparams_validate_returns_False_for_bung_YN_flag():
    skp["incl_starlight"] = "Bogus"
    assert skp.validate_params() is False

def test_skycalcparams_validate_returns_False_for_bung_string_in_array():
    skp["lsf_type"] = "Bogus"
    assert skp.validate_params() is False

def test_skycalcparams_validate_returns_False_for_value_outside_range():
    skp["airmass"] = 0.5
    assert skp.validate_params() is False

def test_skycalcparams_validate_returns_False_for_value_below_zero():
    skp["lsf_boxcar_fwhm"] = -5.
    assert skp.validate_params() is False
