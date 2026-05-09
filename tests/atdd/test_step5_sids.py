"""
ATDD: Step5 受け入れテストシナリオ

Scenario 1: ECUReset (hard/soft) が成功する
Scenario 2: ClearDTC (全消去) が成功する
Scenario 3: ReadDTC でDTCレコードが取得できる
Scenario 4: WriteDataByIdentifier でDIDに書き込める
Scenario 5: RoutineControl (start/stop/results) が成功する
Scenario 6: NRC応答が人間可読で返る（各SID共通）
"""
import pytest
import udsoncan
from udsoncan.services import (
    ECUReset as _ECUReset,
    ClearDiagnosticInformation as _ClearDTC,
    ReadDTCInformation as _ReadDTC,
    WriteDataByIdentifier as _WDBI,
    RoutineControl as _RC,
)
from unittest.mock import MagicMock
from src.application.diagnostic_service import DiagnosticService
from src.protocol.protocol_base import ProtocolBase


def _positive(service, data: bytes = b"") -> bytes:
    resp = udsoncan.Response(service=service, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = data
    return resp.get_payload()

def _nrc(service, code: int) -> bytes:
    return udsoncan.Response(service=service, code=code).get_payload()


@pytest.fixture
def svc():
    mock = MagicMock(spec=ProtocolBase)
    return DiagnosticService(protocol=mock), mock


class TestStep5ECUReset:
    def test_hard_reset_succeeds(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_ECUReset, bytes([0x01]))
        result = service.ecu_reset(reset_type=0x01)
        assert result.success is True

    def test_soft_reset_succeeds(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_ECUReset, bytes([0x03]))
        result = service.ecu_reset(reset_type=0x03)
        assert result.success is True

    def test_nrc_returns_failure(self, svc):
        service, mock = svc
        mock.receive.return_value = _nrc(_ECUReset, 0x22)
        result = service.ecu_reset(reset_type=0x01)
        assert result.success is False
        assert result.nrc_message == "Conditions Not Correct"


class TestStep5ClearDTC:
    def test_clear_all_dtc_succeeds(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_ClearDTC)
        result = service.clear_dtc()
        assert result.success is True

    def test_nrc_returns_failure(self, svc):
        service, mock = svc
        mock.receive.return_value = _nrc(_ClearDTC, 0x31)
        result = service.clear_dtc()
        assert result.success is False
        assert result.nrc_message == "Request Out Of Range"


class TestStep5ReadDTC:
    def test_read_dtc_returns_records(self, svc):
        service, mock = svc
        dtc_data = bytes([0x01, 0x23, 0x45, 0x08, 0xAB, 0xCD, 0xEF, 0x09])
        mock.receive.return_value = _positive(_ReadDTC, bytes([0x02, 0xFF]) + dtc_data)
        result = service.read_dtc(subfunction=0x02, status_mask=0xFF)
        assert result.success is True
        assert len(result.dtc_records) == 2
        assert result.dtc_records[0].dtc == 0x012345

    def test_no_dtc_returns_empty_list(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_ReadDTC, bytes([0x02, 0xFF]))
        result = service.read_dtc(subfunction=0x02)
        assert result.success is True
        assert result.dtc_records == []


class TestStep5WriteDataByIdentifier:
    def test_write_did_succeeds(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_WDBI, bytes([0xF1, 0x90]))
        result = service.write_data_by_identifier(did=0xF190, data=b"NEWVIN00000000001")
        assert result.success is True

    def test_nrc_returns_failure(self, svc):
        service, mock = svc
        mock.receive.return_value = _nrc(_WDBI, 0x31)
        result = service.write_data_by_identifier(did=0xF190, data=b"TEST")
        assert result.success is False


class TestStep5RoutineControl:
    def test_start_routine_succeeds(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_RC, bytes([0x01, 0x02, 0x01]))
        result = service.routine_control(subfunction=0x01, routine_id=0x0201)
        assert result.success is True
        assert result.routine_id == 0x0201

    def test_request_results_with_status_record(self, svc):
        service, mock = svc
        mock.receive.return_value = _positive(_RC, bytes([0x03, 0x02, 0x01, 0x00, 0x01]))
        result = service.routine_control(subfunction=0x03, routine_id=0x0201)
        assert result.success is True
        assert result.routine_status_record == b"\x00\x01"

    def test_nrc_returns_failure(self, svc):
        service, mock = svc
        mock.receive.return_value = _nrc(_RC, 0x31)
        result = service.routine_control(subfunction=0x01, routine_id=0x0201)
        assert result.success is False
