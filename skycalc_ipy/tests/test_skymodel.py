"""Offline tests for SkyModel's request handling and FITS helpers."""

from unittest.mock import Mock

import httpx
import pytest
from astropy.io import fits

from skycalc_ipy import core


@pytest.fixture
def model():
    model = core.SkyModel()
    with fits.HDUList([fits.PrimaryHDU(data=[1, 2, 3])]) as data:
        model.data = data
        yield model


@pytest.fixture
def server_model(model, monkeypatch, tmp_path):
    """Isolate requests and server cleanup from the real ESO service."""
    monkeypatch.setattr(core, "get_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model, "_send_request", Mock(return_value=httpx.Response(
        200, json={"status": "success", "tmpdir": "test-directory"})))
    monkeypatch.setattr(model, "_retrieve_data", Mock())
    monkeypatch.setattr(model, "_delete_server_tmpdir", Mock())
    return model


class TestSkyModelRequest:
    def test_success_retrieves_and_stores_spectrum(self, server_model, tmp_path):
        model = server_model
        model(airmass=2, observatory="lasilla", unknown_parameter=42)

        assert model["airmass"] == 2
        assert model["observatory"] == "2400"
        assert "unknown_parameter" not in model.params
        assert model._last_status == "success"
        model._send_request.assert_called_once_with()
        model._retrieve_data.assert_called_once_with(
            model.BASE_URL + "/tmp/test-directory/skytable.fits")
        model._delete_server_tmpdir.assert_called_once_with("test-directory")
        files = list(tmp_path.glob("*.fits"))
        assert len(files) == 1
        with fits.open(files[0]) as stored:
            assert stored[0].data.tolist() == [1, 2, 3]

    def test_validation_failure_does_not_retrieve_spectrum(
            self, server_model, tmp_path, monkeypatch):
        model = server_model
        model._send_request.return_value = httpx.Response(200, json={
            "status": "error", "tmpdir": "", "error": "Invalid airmass"})
        logger = Mock()
        monkeypatch.setattr(core, "logger", logger)

        model()

        assert model._last_status == "error"
        model._retrieve_data.assert_not_called()
        model._delete_server_tmpdir.assert_not_called()
        assert not list(tmp_path.iterdir())
        logger.error.assert_called_once_with(
            "Parameter validation error: %s", "Invalid airmass")

    @pytest.mark.parametrize("response, error", [
        (httpx.Response(200, text="not JSON"), ValueError),
        (httpx.Response(200, json={"tmpdir": "test-directory"}), KeyError),
        (httpx.Response(200, json={"status": "success"}), KeyError),
    ])
    def test_malformed_response_raises(self, server_model, response, error):
        server_model._send_request.return_value = response

        with pytest.raises(error):
            server_model()

        server_model._retrieve_data.assert_not_called()
        server_model._delete_server_tmpdir.assert_not_called()

    def test_retrieval_error_propagates(self, server_model):
        error = httpx.ConnectError("Cannot download spectrum")
        server_model._retrieve_data.side_effect = error

        with pytest.raises(httpx.ConnectError) as caught:
            server_model()

        assert caught.value is error

    @pytest.mark.parametrize("error", [PermissionError, FileNotFoundError])
    def test_storage_error_still_cleans_up_server(
            self, server_model, monkeypatch, error):
        monkeypatch.setattr(server_model.data, "writeto", Mock(side_effect=error))

        server_model()

        assert server_model.data[0].data.tolist() == [1, 2, 3]
        server_model._delete_server_tmpdir.assert_called_once_with(
            "test-directory")


class TestSkyModelFits:
    def test_retrieval_sets_fixed_date(self, model, tmp_path):
        filename = tmp_path / "spectrum.fits"
        model.data[0].header["DATE"] = "2026-01-01T12:00:00"
        model.data.writeto(filename)

        try:
            model._retrieve_data(filename)
            assert model.data[0].data.tolist() == [1, 2, 3]
            assert model.data[0].header["DATE"] == "2017-01-07T00:00:00"
        finally:
            model.data.close()

    def test_retrieval_error_propagates(self, model, tmp_path):
        with pytest.raises(FileNotFoundError):
            model._retrieve_data(tmp_path / "missing.fits")

    def test_write_forwards_overwrite_option(self, model, tmp_path):
        filename = tmp_path / "spectrum.fits"
        model.write(filename)
        model.data[0].header["UPDATED"] = True
        model.write(filename, overwrite=True)

        with fits.open(filename) as stored:
            assert stored[0].header["UPDATED"]
            assert stored[0].data.tolist() == [1, 2, 3]

    def test_write_failure_is_logged(self, model, tmp_path, monkeypatch):
        logger = Mock()
        monkeypatch.setattr(core, "logger", logger)

        model.write(tmp_path / "missing-directory" / "spectrum.fits")

        logger.exception.assert_called_once_with(
            "Exception raised trying to write fits file.")


@pytest.mark.parametrize("reply", [" OK \n", "deletion failed", None])
def test_server_cleanup(model, monkeypatch, reply):
    client_class = httpx.Client

    def handle_request(request):
        assert request.url.path.endswith("/bin/script/rmtmp.py")
        assert request.url.params["d"] == "test-directory"
        if reply is None:
            raise httpx.ConnectError("Server unavailable", request=request)
        return httpx.Response(200, text=reply)

    transport = httpx.MockTransport(handle_request)
    monkeypatch.setattr(core.httpx, "Client", lambda **kwargs: client_class(
        transport=transport, **kwargs))
    logger = Mock()
    monkeypatch.setattr(core, "logger", logger)

    model._delete_server_tmpdir("test-directory")

    assert logger.error.called == (reply == "deletion failed")
    assert logger.exception.called == (reply is None)
