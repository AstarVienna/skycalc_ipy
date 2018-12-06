import os
import inspect
from pytest import raises
from skycalc_ipy import ui
from astropy import table
from astropy.io import fits
import synphot as sp

# Mocks
skp  = ui.SkyCalc()
skp2 = ui.SkyCalc()
skp_small = ui.SkyCalc()
skp_small["wdelta"] = 100

class TestLoadYaml:

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


class TestSkycalcParamsInit:
    def test_loads_default_when_no_file_given(self):
        assert type(skp.defaults) == dict
        assert skp.defaults["observatory"] == "paranal"
        assert skp.allowed["therm_t2"] == 0

    def test_print_comments_single_keywords(self, capsys):
        skp.print_comments("airmass")
        output = capsys.readouterr()[0].strip()
        assert output == "airmass : airmass in range [1.0, 3.0]"

    def test_print_comments_mutliple_keywords(self, capsys):
        skp.print_comments(["airmass", "season"])
        output = capsys.readouterr()[0].strip()
        assert output == "airmass : airmass in range [1.0, 3.0]\n" + \
                         "season : 0=all year, 1=dec/jan,2=feb/mar..."

    def test_print_comments_misspelled_keyword(self, capsys):
        skp.print_comments(["iarmass"])
        sys_out = capsys.readouterr()
        output = sys_out[0].strip()
        assert output == "iarmass not found"

    def test_keys_returns_list_of_keys(self):
        assert type(skp.keys) == list
        assert "observatory" in skp.keys


class TestSkycalcParamsValidateMethod(object):

    def test_returns_true_for_all_good(self):
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


class TestSkyCalcParamsGetSkySpectrum:

    def test_returns_data_with_valid_parameters(self):
        tbl = skp_small.get_sky_spectrum()
        assert "lam" in tbl.colnames
        assert "flux" in tbl.colnames
        assert "trans" in tbl.colnames
        assert len(tbl) == 18

    def test_throws_exception_for_invalid_parameters(self):
        skp["airmass"] = 9001
        with raises(ValueError):
            skp.get_sky_spectrum()

    def test_returns_table_for_return_type_table(self):
        tbl = skp_small.get_sky_spectrum(return_type="table")
        assert isinstance(tbl, table.Table)

    def test_returns_fits_for_return_type_fits(self):
        hdu = skp_small.get_sky_spectrum(return_type="fits")
        assert isinstance(hdu, fits.HDUList)

    def test_returned_fits_has_proper_meta_data(self):
        hdu = skp_small.get_sky_spectrum(return_type="fits")
        assert "DATE_CRE" in hdu[0].header
        assert "SOURCE" in hdu[0].header
        assert "AIRMASS" in hdu[0].header
        assert hdu[0].header["ETYPE"] == "TERCurve"

    def test_returns_three_arrays_for_return_type_array(self):
        arrs = skp_small.get_sky_spectrum(return_type="array")
        assert len(arrs) == 3

    def test_returns_two_synphot_objects_for_return_type_synphot(self):
        trans, flux = skp_small.get_sky_spectrum(return_type="synphot")
        assert isinstance(trans, sp.SpectralElement)
        assert isinstance(flux,  sp.SourceSpectrum)

    def test_returns_nothing_if_return_type_is_invalid(self):
        pass


class TestSkyCalcParamsGetAlmanacData:

    def test_return_updated_SkyCalcParams_values_dict_when_flag_true(self):
        out_dict = skp.get_almanac_data(ra=180, dec=0, mjd=50000,
                                        observatory="lasilla",
                                        update_values=True)
        assert out_dict["observatory"] == "lasilla"
        assert skp["observatory"] == "lasilla"

    def test_return_only_almanac_data_when_update_flag_false(self):
        skp2["observatory"] == "paranal"
        out_dict = skp.get_almanac_data(ra=180, dec=0, mjd=50000,
                                        observatory="lasilla",
                                        update_values=False)
        assert out_dict["observatory"] == "lasilla"
        assert skp2["observatory"] == "paranal"

    def raise_error_if_both_date_and_mjd_are_empty(self):
        with raises(ValueError):
            skp.get_almanac_data(180, 0)


class TestFunctionGetAlmanacData:

    def test_throws_exception_for_invalid_ra(self):
        with raises(ValueError):
            ui.get_almanac_data(ra=-10, dec=0, mjd=50000)

    def test_throws_exception_for_invalid_dec(self):
        with raises(ValueError):
            ui.get_almanac_data(ra=180, dec=100, mjd=50000)

    def test_throws_exception_for_invalid_mjd(self):
        with raises(ValueError):
            ui.get_almanac_data(ra=180, dec=0, mjd="s")

    def test_throws_exception_for_invalid_date(self):
        with raises(ValueError):
            ui.get_almanac_data(ra=180, dec=0, date="2000-0-0T0:0:0")

    def test_return_data_for_valid_parameters(self):
        out_dict = ui.get_almanac_data(ra=180, dec=0, date="2000-1-1T0:0:0",
                                       observatory="lasilla")
        assert type(out_dict) == dict
        assert len(out_dict) == 9
        assert out_dict["observatory"] == "lasilla"

    def test_return_full_dict_when_flag_true(self):
        out_dict = ui.get_almanac_data(ra=180, dec=0, date="2000-1-1T0:0:0",
                                       return_full_dict=True)
        assert type(out_dict) == dict
        assert len(out_dict) == 39
        assert type(out_dict["moon_sun_sep"]) == float


    def test_return_only_almanac_dict_when_flag_false(self):
        out_dict = ui.get_almanac_data(ra=180, dec=0, date="2000-1-1T0:0:0",
                                       return_full_dict=False)
        assert type(out_dict) == dict
        assert len(out_dict) == 9

    def test_take_date_only_if_date_and_mjd_are_valid(self, capsys):
        out_dict_date = ui.get_almanac_data(ra=180, dec=0,
                                             date="2000-1-1T0:0:0")
        out_dict_both = ui.get_almanac_data(ra=180, dec=0, mjd=50000,
                                             date="2000-1-1T0:0:0")
        output = capsys.readouterr()[0].strip()
        assert output == "Warning: Both date and mjd are set. Using date"
        assert out_dict_both == out_dict_date

#
# class TestFunctionFixObservatory:
#
#     def test_returns_corrected_dict_for_valid_observatory(self):
#         in_dict = {"observatory": "paranal"}
#         out_dict = ui.fix_observatory(in_dict)
#         assert out_dict["observatory"] == "2640"
#         assert out_dict["observatory_orig"] == "paranal"
#
#     def test_returns_corrected_SkyCalcParams_for_valid_observatory(self):
#         skp["observatory"] = "paranal"
#         out_dict = ui.fix_observatory(skp)
#         assert out_dict["observatory"] == "2640"
#
#     def test_returns_exception_for_in_valid_observatory(self):
#         in_dict = {"observatory" : "deutsch-wagram"}
#         with raises(Exception):
#             ui.fix_observatory(in_dict)
#
#     def test_returns_exception_for_wrong_indict_data_type(self):
#         with raises(Exception):
#             ui.fix_observatory("Bogus")
