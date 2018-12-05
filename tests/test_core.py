from pytest import raises
from skycalc_ipy import ui
from skycalc_ipy import core

from datetime import datetime as dt

# Mocks
skp = ui.SkyCalcParams()

class TestAlmanacInit:

    def test_throws_exception_when_passed_virgin_SkyCalcParams(self):
        with raises(ValueError):
            core.AlmanacQuery(skp)

    def test_passes_for_valid_SkyCalcParams_with_date(self):
        skp.update({"ra": 0, "dec": 0, "date": "2000-1-1T0:0:0", "mjd": None})
        alm = core.AlmanacQuery(skp)
        print(alm.almindic)
        assert alm.almindic['coord_year'] == 2000
        assert alm.almindic['coord_ut_sec'] == 0
        assert alm.almindic['input_type'] == "ut_time"

    def test_passes_for_valid_SkyCalcParams_with_mjd(self):
        skp.update({"mjd": 0, "date": None})
        alm = core.AlmanacQuery(skp)
        print(alm.almindic)
        assert alm.almindic['mjd'] == 0
        assert alm.almindic['input_type'] == "mjd"

    def test_throws_exception_when_date_and_mjd_are_empty(self):
        skp.update({"mjd": None, "date": None})
        with raises(ValueError):
            core.AlmanacQuery(skp)

    def test_passes_for_date_as_datetime_object(self):
        skp.update({"date": dt(1986, 4, 26, 1, 24)})
        alm = core.AlmanacQuery(skp)
        assert alm.almindic['coord_ut_min'] == 24
        assert alm.almindic['input_type'] == "ut_time"

    def test_throws_exception_when_date_is_unintelligible(self):
        skp.update({"date": "bogus"})
        with raises(ValueError):
            core.AlmanacQuery(skp)

    def test_throws_exception_when_mjd_is_unintelligible(self):
        skp.update({"mjd": "bogus"})
        with raises(ValueError):
            core.AlmanacQuery(skp)
