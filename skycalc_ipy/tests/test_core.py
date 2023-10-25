import pytest
from pytest import raises
from skycalc_ipy import ui
from skycalc_ipy import core

from datetime import datetime as dt


@pytest.fixture
def skp():
    return ui.SkyCalc()


@pytest.fixture
def skp_basic(skp):
    skp.update({"ra": 0, "dec": 0})
    return skp


class TestAlmanacInit:
    def test_throws_exception_when_passed_virgin_SkyCalcParams(self, skp):
        with raises(ValueError):
            core.AlmanacQuery(skp)

    def test_passes_for_valid_SkyCalcParams_with_date(self, skp):
        skp.update({"ra": 0, "dec": 0, "date": "2000-1-1T0:0:0", "mjd": None})
        alm = core.AlmanacQuery(skp)
        assert alm.params["coord_year"] == 2000
        assert alm.params["coord_ut_sec"] == 0
        assert alm.params["input_type"] == "ut_time"

    def test_passes_for_valid_SkyCalcParams_with_mjd(self, skp_basic):
        skp_basic.update({"mjd": 0, "date": None})
        alm = core.AlmanacQuery(skp_basic)
        assert alm.params["mjd"] == 0
        assert alm.params["input_type"] == "mjd"

    def test_throws_exception_when_date_and_mjd_are_empty(self, skp_basic):
        skp_basic.update({"mjd": None, "date": None})
        with raises(ValueError):
            core.AlmanacQuery(skp_basic)

    def test_passes_for_date_as_datetime_object(self, skp_basic):
        skp_basic.update({"date": dt(1986, 4, 26, 1, 24)})
        alm = core.AlmanacQuery(skp_basic)
        assert alm.params["coord_ut_min"] == 24
        assert alm.params["input_type"] == "ut_time"

    def test_throws_exception_when_date_is_unintelligible(self, skp_basic):
        skp_basic.update({"date": "bogus"})
        with raises(ValueError):
            core.AlmanacQuery(skp_basic)

    def test_throws_exception_when_mjd_is_unintelligible(self, skp_basic):
        skp_basic.update({"mjd": "bogus"})
        with raises(ValueError):
            core.AlmanacQuery(skp_basic)


class TestLoadDataFromCache:
    def test_load_skymodel_from_cache(self):
        """Should load cached data in data directory."""
        params = {
            "ra": 11.,
            "dec": 22.,
            "date": "1999-01-02T02:03:04",
            "wdelta": 100.,
        }

        skymodel = core.SkyModel()
        skymodel(**params)

        alm = core.AlmanacQuery(params)
        _ = alm()
