"""DiagnosticSessionControl SID=0x10 ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import DiagnosticSessionControl as _DSC
from src.uds.diagnostic_session_control import DiagnosticSessionControl


def _positive_response(session_type: int) -> bytes:
    resp = udsoncan.Response(service=_DSC, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([session_type, 0x00, 0x19, 0x01, 0xF4])
    return resp.get_payload()


def _nrc_response(nrc_code: int) -> bytes:
    return udsoncan.Response(service=_DSC, code=nrc_code).get_payload()


class TestDiagnosticSessionControlRequest:

    def test_build_request_default_session(self):
        svc = DiagnosticSessionControl()
        frame = svc.build_request(session_type=0x01)
        assert frame[0] == 0x10
        assert frame[1] == 0x01

    def test_build_request_extended_session(self):
        svc = DiagnosticSessionControl()
        frame = svc.build_request(session_type=0x03)
        assert frame[0] == 0x10
        assert frame[1] == 0x03

    def test_build_request_programming_session(self):
        svc = DiagnosticSessionControl()
        frame = svc.build_request(session_type=0x02)
        assert frame[1] == 0x02

    def test_session_type_0x00_raises(self):
        svc = DiagnosticSessionControl()
        with pytest.raises(ValueError, match="session_type must be"):
            svc.build_request(session_type=0x00)

    def test_session_type_0x80_raises(self):
        svc = DiagnosticSessionControl()
        with pytest.raises(ValueError, match="session_type must be"):
            svc.build_request(session_type=0x80)


class TestDiagnosticSessionControlResponse:

    def test_parse_positive_response_default(self):
        svc = DiagnosticSessionControl()
        result = svc.parse_response(_positive_response(0x01))
        assert result.success is True
        assert result.session_type == 0x01

    def test_parse_positive_response_extended(self):
        svc = DiagnosticSessionControl()
        result = svc.parse_response(_positive_response(0x03))
        assert result.success is True
        assert result.session_type == 0x03

    def test_parse_nrc_0x12(self):
        svc = DiagnosticSessionControl()
        result = svc.parse_response(_nrc_response(0x12))
        assert result.success is False
        assert result.nrc_code == 0x12
        assert result.nrc_message == "Sub Function Not Supported"

    def test_parse_nrc_0x22(self):
        svc = DiagnosticSessionControl()
        result = svc.parse_response(_nrc_response(0x22))
        assert result.success is False
        assert result.nrc_message == "Conditions Not Correct"

    def test_raw_response_is_preserved(self):
        svc = DiagnosticSessionControl()
        raw = _positive_response(0x01)
        result = svc.parse_response(raw)
        assert result.raw_response == raw
