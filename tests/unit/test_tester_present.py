"""TesterPresent SID=0x3E ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import TesterPresent as _TP
from src.uds.tester_present import TesterPresent


def _positive_response() -> bytes:
    resp = udsoncan.Response(service=_TP, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([0x00])
    return resp.get_payload()


def _nrc_response(nrc_code: int) -> bytes:
    return udsoncan.Response(service=_TP, code=nrc_code).get_payload()


class TestTesterPresentRequest:

    def test_build_request_default(self):
        svc = TesterPresent()
        frame = svc.build_request()
        assert frame[0] == 0x3E
        assert frame[1] == 0x00

    def test_build_request_suppress_response(self):
        svc = TesterPresent()
        frame = svc.build_request(suppress_response=True)
        assert frame[0] == 0x3E
        assert frame[1] == 0x80

    def test_build_request_not_suppressed(self):
        svc = TesterPresent()
        frame = svc.build_request(suppress_response=False)
        assert frame[1] & 0x80 == 0x00


class TestTesterPresentResponse:

    def test_parse_positive_response(self):
        svc = TesterPresent()
        result = svc.parse_response(_positive_response())
        assert result.success is True
        assert result.nrc_code is None

    def test_parse_nrc_0x22(self):
        svc = TesterPresent()
        result = svc.parse_response(_nrc_response(0x22))
        assert result.success is False
        assert result.nrc_code == 0x22
        assert result.nrc_message == "Conditions Not Correct"

    def test_raw_response_preserved(self):
        svc = TesterPresent()
        raw = _positive_response()
        result = svc.parse_response(raw)
        assert result.raw_response == raw
