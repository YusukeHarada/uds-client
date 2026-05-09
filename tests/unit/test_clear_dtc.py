"""ClearDTC SID=0x14 ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import ClearDiagnosticInformation as _ClearDTC
from src.uds.clear_dtc import ClearDTC


def _positive() -> bytes:
    resp = udsoncan.Response(service=_ClearDTC, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = b""
    return resp.get_payload()

def _nrc(code: int) -> bytes:
    return udsoncan.Response(service=_ClearDTC, code=code).get_payload()


class TestClearDTCRequest:
    def test_build_request_all_dtc(self):
        frame = ClearDTC().build_request()
        assert frame[0] == 0x14
        assert frame[1:4] == bytes([0xFF, 0xFF, 0xFF])

    def test_build_request_specific_group(self):
        frame = ClearDTC().build_request(group_of_dtc=0x012345)
        assert frame[1:4] == bytes([0x01, 0x23, 0x45])

    def test_invalid_group_raises(self):
        with pytest.raises(ValueError, match="group_of_dtc"):
            ClearDTC().build_request(group_of_dtc=0x1000000)


class TestClearDTCResponse:
    def test_parse_positive(self):
        result = ClearDTC().parse_response(_positive())
        assert result.success is True

    def test_parse_nrc(self):
        result = ClearDTC().parse_response(_nrc(0x31))
        assert result.success is False
        assert result.nrc_message == "Request Out Of Range"
