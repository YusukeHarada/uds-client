"""ECUReset SID=0x11 ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import ECUReset as _ECUReset
from src.uds.ecu_reset import ECUReset


def _positive(reset_type: int) -> bytes:
    resp = udsoncan.Response(service=_ECUReset, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([reset_type])
    return resp.get_payload()

def _nrc(code: int) -> bytes:
    return udsoncan.Response(service=_ECUReset, code=code).get_payload()


class TestECUResetRequest:
    def test_build_hard_reset(self):
        frame = ECUReset().build_request(reset_type=0x01)
        assert frame[0] == 0x11
        assert frame[1] == 0x01

    def test_build_soft_reset(self):
        frame = ECUReset().build_request(reset_type=0x03)
        assert frame[1] == 0x03

    def test_invalid_reset_type_raises(self):
        with pytest.raises(ValueError, match="reset_type must be"):
            ECUReset().build_request(reset_type=0x02)


class TestECUResetResponse:
    def test_parse_positive(self):
        result = ECUReset().parse_response(_positive(0x01))
        assert result.success is True

    def test_parse_nrc(self):
        result = ECUReset().parse_response(_nrc(0x22))
        assert result.success is False
        assert result.nrc_code == 0x22
        assert result.nrc_message == "Conditions Not Correct"
