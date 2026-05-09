"""ReadDTCInformation SID=0x19 ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import ReadDTCInformation as _ReadDTC
from src.uds.read_dtc_information import ReadDTCInformation


def _positive(subfn: int, dtc_data: bytes = b"") -> bytes:
    resp = udsoncan.Response(service=_ReadDTC, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([subfn, 0xFF]) + dtc_data
    return resp.get_payload()

def _nrc(code: int) -> bytes:
    return udsoncan.Response(service=_ReadDTC, code=code).get_payload()


class TestReadDTCRequest:
    def test_build_request_by_status_mask(self):
        frame = ReadDTCInformation().build_request(subfunction=0x02, status_mask=0xFF)
        assert frame[0] == 0x19
        assert frame[1] == 0x02
        assert frame[2] == 0xFF

    def test_build_request_supported_dtc(self):
        frame = ReadDTCInformation().build_request(subfunction=0x0A)
        assert frame[1] == 0x0A

    def test_invalid_subfunction_raises(self):
        with pytest.raises(ValueError, match="subfunction"):
            ReadDTCInformation().build_request(subfunction=0x01)


class TestReadDTCResponse:
    def test_parse_positive_no_dtc(self):
        result = ReadDTCInformation().parse_response(_positive(0x02))
        assert result.success is True
        assert result.dtc_records == []

    def test_parse_positive_with_dtc_records(self):
        # DTC=0x012345, status=0x08  /  DTC=0xABCDEF, status=0x09
        dtc_data = bytes([0x01, 0x23, 0x45, 0x08, 0xAB, 0xCD, 0xEF, 0x09])
        result = ReadDTCInformation().parse_response(_positive(0x02, dtc_data))
        assert result.success is True
        assert len(result.dtc_records) == 2
        assert result.dtc_records[0].dtc == 0x012345
        assert result.dtc_records[0].status == 0x08
        assert result.dtc_records[1].dtc == 0xABCDEF

    def test_parse_nrc(self):
        result = ReadDTCInformation().parse_response(_nrc(0x31))
        assert result.success is False
        assert result.nrc_message == "Request Out Of Range"
