"""ATDD: Step2 受け入れテストシナリオ"""
import pytest
import udsoncan
from udsoncan.services import DiagnosticSessionControl as _DSC
from udsoncan.services import TesterPresent as _TP
from udsoncan.services import ReadDataByIdentifier as _RDBI
from unittest.mock import MagicMock
from src.application.diagnostic_service import DiagnosticService
from src.protocol.protocol_base import ProtocolBase


def _positive(service, data: bytes = b"") -> bytes:
    resp = udsoncan.Response(service=service, code=udsoncan.Response.Code.PositiveResponse)
    resp.data = data
    return resp.get_payload()


def _nrc(service, nrc_code: int) -> bytes:
    return udsoncan.Response(service=service, code=nrc_code).get_payload()


class TestStep2AcceptanceSession:

    def setup_method(self):
        self.mock_protocol = MagicMock(spec=ProtocolBase)
        self.service = DiagnosticService(protocol=self.mock_protocol)

    def test_transition_to_default_session(self):
        self.mock_protocol.receive.return_value = _positive(
            _DSC, bytes([0x01, 0x00, 0x19, 0x01, 0xF4])
        )
        result = self.service.change_session(session_type=0x01)
        assert result.success is True
        assert result.session_type == 0x01

    def test_transition_to_extended_session(self):
        self.mock_protocol.receive.return_value = _positive(
            _DSC, bytes([0x03, 0x00, 0x19, 0x01, 0xF4])
        )
        result = self.service.change_session(session_type=0x03)
        assert result.success is True
        assert result.session_type == 0x03

    def test_invalid_session_type_raises_before_send(self):
        with pytest.raises(ValueError, match="session_type must be"):
            self.service.change_session(session_type=0xFF)
        self.mock_protocol.send.assert_not_called()

    def test_nrc_from_ecu_returns_failure(self):
        self.mock_protocol.receive.return_value = _nrc(_DSC, 0x22)
        result = self.service.change_session(session_type=0x02)
        assert result.success is False
        assert result.nrc_code == 0x22
        assert result.nrc_message == "Conditions Not Correct"

    def test_tester_present_succeeds(self):
        self.mock_protocol.receive.return_value = _positive(_TP, bytes([0x00]))
        result = self.service.tester_present()
        assert result.success is True

    def test_tester_present_suppress_does_not_call_receive(self):
        result = self.service.tester_present(suppress_response=True)
        assert result.success is True
        self.mock_protocol.receive.assert_not_called()

    def test_session_then_rdbi(self):
        rdbi_resp = udsoncan.Response(
            service=_RDBI, code=udsoncan.Response.Code.PositiveResponse
        )
        rdbi_resp.data = bytes([0xF1, 0x90]) + b"1HGBH41JXMN109186"
        self.mock_protocol.receive.side_effect = [
            _positive(_DSC, bytes([0x03, 0x00, 0x19, 0x01, 0xF4])),
            rdbi_resp.get_payload(),
        ]
        session_result = self.service.change_session(session_type=0x03)
        rdbi_result = self.service.read_data_by_identifier(did=0xF190)
        assert session_result.success is True
        assert rdbi_result.success is True
        assert rdbi_result.data == b"1HGBH41JXMN109186"
