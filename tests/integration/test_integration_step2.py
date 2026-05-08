"""結合テスト Step2: ECUシミュレータを使った実TCP通信テスト"""
import threading
import time
import pytest

from ecu_simulator import run_server
from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol

SIM_HOST = "127.0.0.1"
SIM_PORT = 15741


@pytest.fixture(scope="module")
def ecu_simulator():
    stop_event = threading.Event()
    thread = threading.Thread(
        target=run_server,
        kwargs={"host": SIM_HOST, "port": SIM_PORT, "stop_event": stop_event},
        daemon=True,
    )
    thread.start()
    time.sleep(0.2)
    yield {"host": SIM_HOST, "port": SIM_PORT}
    stop_event.set()
    thread.join(timeout=2.0)


def _make_protocol(sim):
    return DoIPProtocol(host=sim["host"], port=sim["port"], target_address=0x1000)


class TestIntegrationSessionControl:

    def test_change_to_default_session(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        try:
            result = DiagnosticService(protocol=protocol).change_session(session_type=0x01)
        finally:
            protocol.disconnect()
        assert result.success is True
        assert result.session_type == 0x01

    def test_change_to_extended_session(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        try:
            result = DiagnosticService(protocol=protocol).change_session(session_type=0x03)
        finally:
            protocol.disconnect()
        assert result.success is True
        assert result.session_type == 0x03

    def test_unsupported_session_returns_nrc(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        try:
            result = DiagnosticService(protocol=protocol).change_session(session_type=0x7F)
        finally:
            protocol.disconnect()
        assert result.success is False
        assert result.nrc_code == 0x12


class TestIntegrationTesterPresent:

    def test_tester_present_response_required(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        try:
            result = DiagnosticService(protocol=protocol).tester_present()
        finally:
            protocol.disconnect()
        assert result.success is True

    def test_tester_present_suppress_response(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        try:
            result = DiagnosticService(protocol=protocol).tester_present(suppress_response=True)
        finally:
            protocol.disconnect()
        assert result.success is True


class TestIntegrationSessionThenRdbi:

    def test_extended_session_then_read_vin(self, ecu_simulator):
        protocol = _make_protocol(ecu_simulator)
        protocol.connect()
        service = DiagnosticService(protocol=protocol)
        try:
            session_result = service.change_session(session_type=0x03)
            rdbi_result = service.read_data_by_identifier(did=0xF190)
        finally:
            protocol.disconnect()
        assert session_result.success is True
        assert rdbi_result.success is True
        assert rdbi_result.data == b"SIMVIN0000000001"
