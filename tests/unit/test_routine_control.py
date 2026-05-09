"""RoutineControl SID=0x31 ユニットテスト"""
import pytest
import udsoncan
from udsoncan.services import RoutineControl as _RC
from src.uds.routine_control import RoutineControl


def _positive(subfn: int, routine_id: int, status: bytes = b"") -> bytes:
    resp = udsoncan.Response(service=_RC, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = bytes([subfn, (routine_id >> 8) & 0xFF, routine_id & 0xFF]) + status
    return resp.get_payload()

def _nrc(code: int) -> bytes:
    return udsoncan.Response(service=_RC, code=code).get_payload()


class TestRoutineControlRequest:
    def test_build_start_routine(self):
        frame = RoutineControl().build_request(subfunction=0x01, routine_id=0x0201)
        assert frame[0] == 0x31
        assert frame[1] == 0x01
        assert frame[2:4] == bytes([0x02, 0x01])

    def test_build_stop_routine(self):
        frame = RoutineControl().build_request(subfunction=0x02, routine_id=0x0201)
        assert frame[1] == 0x02

    def test_build_request_results(self):
        frame = RoutineControl().build_request(subfunction=0x03, routine_id=0x0201)
        assert frame[1] == 0x03

    def test_invalid_subfunction_raises(self):
        with pytest.raises(ValueError, match="subfunction"):
            RoutineControl().build_request(subfunction=0x04, routine_id=0x0201)

    def test_invalid_routine_id_raises(self):
        with pytest.raises(ValueError, match="routine_id"):
            RoutineControl().build_request(subfunction=0x01, routine_id=0x10000)


class TestRoutineControlResponse:
    def test_parse_positive_without_status(self):
        result = RoutineControl().parse_response(_positive(0x01, 0x0201))
        assert result.success is True
        assert result.subfunction == 0x01
        assert result.routine_id == 0x0201
        assert result.routine_status_record == b""

    def test_parse_positive_with_status(self):
        result = RoutineControl().parse_response(_positive(0x03, 0x0201, b"\x00\x01"))
        assert result.routine_status_record == b"\x00\x01"

    def test_parse_nrc(self):
        result = RoutineControl().parse_response(_nrc(0x31))
        assert result.success is False
        assert result.nrc_message == "Request Out Of Range"
