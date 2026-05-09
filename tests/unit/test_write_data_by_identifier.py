"""WriteDataByIdentifier SID=0x2E ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import WriteDataByIdentifier as _WDBI
from src.uds.write_data_by_identifier import WriteDataByIdentifier


def _positive(did: int) -> bytes:
    resp = udsoncan.Response(service=_WDBI, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([(did >> 8) & 0xFF, did & 0xFF])
    return resp.get_payload()

def _nrc(code: int) -> bytes:
    return udsoncan.Response(service=_WDBI, code=code).get_payload()


class TestWDBIRequest:
    def test_build_request(self):
        frame = WriteDataByIdentifier().build_request(did=0xF190, data=b"TEST")
        assert frame[0] == 0x2E
        assert frame[1:3] == bytes([0xF1, 0x90])
        assert frame[3:] == b"TEST"

    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="data must not be empty"):
            WriteDataByIdentifier().build_request(did=0xF190, data=b"")

    def test_invalid_did_raises(self):
        with pytest.raises(ValueError, match="DID must be"):
            WriteDataByIdentifier().build_request(did=0x10000, data=b"X")


class TestWDBIResponse:
    def test_parse_positive(self):
        result = WriteDataByIdentifier().parse_response(_positive(0xF190), did=0xF190)
        assert result.success is True

    def test_parse_nrc(self):
        result = WriteDataByIdentifier().parse_response(_nrc(0x31), did=0xF190)
        assert result.success is False
        assert result.nrc_message == "Request Out Of Range"

    def test_did_mismatch_raises(self):
        with pytest.raises(ValueError, match="DID mismatch"):
            WriteDataByIdentifier().parse_response(_positive(0xF191), did=0xF190)
