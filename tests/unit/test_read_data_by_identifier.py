"""ReadDataByIdentifier (SID=0x22) ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import ReadDataByIdentifier as _RDBI
from src.uds.read_data_by_identifier import ReadDataByIdentifier


def make_positive_response(did: int, data: bytes) -> bytes:
    resp = udsoncan.Response(
        service=_RDBI,
        code=udsoncan.Response.Code.PositiveResponse,
    )
    resp.data = bytes([(did >> 8) & 0xFF, did & 0xFF]) + data
    return resp.get_payload()


def make_nrc_response(nrc_code: int) -> bytes:
    resp = udsoncan.Response(service=_RDBI, code=nrc_code)
    return resp.get_payload()


class TestReadDataByIdentifierRequest:

    def test_build_request_f190(self):
        svc = ReadDataByIdentifier()
        frame = svc.build_request(did=0xF190)
        # udsoncanが生成したフレームにSID=0x22とDIDが含まれること
        assert frame[0] == 0x22
        assert frame[1:3] == bytes([0xF1, 0x90])

    def test_build_request_0x0001(self):
        svc = ReadDataByIdentifier()
        frame = svc.build_request(did=0x0001)
        assert frame[1:3] == bytes([0x00, 0x01])

    def test_did_out_of_range_raises_value_error(self):
        svc = ReadDataByIdentifier()
        with pytest.raises(ValueError, match="DID must be in range"):
            svc.build_request(did=0x10000)


class TestReadDataByIdentifierResponse:

    def test_parse_positive_response_returns_data(self):
        svc = ReadDataByIdentifier()
        raw = make_positive_response(0xF190, b"1HGBH41JXMN109186")
        result = svc.parse_response(raw, did=0xF190)
        assert result.success is True
        assert result.data == b"1HGBH41JXMN109186"

    def test_parse_nrc_0x31_returns_failure(self):
        svc = ReadDataByIdentifier()
        raw = make_nrc_response(0x31)
        result = svc.parse_response(raw, did=0xF190)
        assert result.success is False
        assert result.nrc_code == 0x31
        assert result.nrc_message == "Request Out Of Range"

    def test_parse_nrc_0x22_returns_conditions_not_correct(self):
        svc = ReadDataByIdentifier()
        raw = make_nrc_response(0x22)
        result = svc.parse_response(raw, did=0xF190)
        assert result.nrc_message == "Conditions Not Correct"

    def test_did_mismatch_raises_value_error(self):
        svc = ReadDataByIdentifier()
        # DID=F191で応答が来たがF190を期待している
        raw = make_positive_response(0xF191, b"DATA")
        with pytest.raises(ValueError, match="DID mismatch"):
            svc.parse_response(raw, did=0xF190)
