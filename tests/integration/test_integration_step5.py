"""結合テスト Step5: ECUシミュレータを使った実TCP通信テスト"""
import threading
import time
import pytest

from ecu_simulator import run_server
from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol

SIM_HOST = "127.0.0.1"
SIM_PORT = 15742


@pytest.fixture(scope="module")
def ecu_simulator():
    stop_event = threading.Event()
    threading.Thread(
        target=run_server,
        kwargs={"host": SIM_HOST, "port": SIM_PORT, "stop_event": stop_event},
        daemon=True,
    ).start()
    time.sleep(0.2)
    yield {"host": SIM_HOST, "port": SIM_PORT}
    stop_event.set()


def _make_service(sim):
    protocol = DoIPProtocol(host=sim["host"], port=sim["port"], target_address=0x1000)
    protocol.connect()
    return DiagnosticService(protocol=protocol), protocol


class TestIntegrationECUReset:
    def test_hard_reset(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.ecu_reset(reset_type=0x01)
        finally:
            proto.disconnect()
        assert result.success is True

    def test_soft_reset(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.ecu_reset(reset_type=0x03)
        finally:
            proto.disconnect()
        assert result.success is True


class TestIntegrationClearDTC:
    def test_clear_all_dtc(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.clear_dtc()
        finally:
            proto.disconnect()
        assert result.success is True


class TestIntegrationReadDTC:
    def test_read_dtc_by_status_mask(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.read_dtc(subfunction=0x02, status_mask=0xFF)
        finally:
            proto.disconnect()
        assert result.success is True
        assert len(result.dtc_records) == 2
        assert result.dtc_records[0].dtc == 0x012345

    def test_read_supported_dtc(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.read_dtc(subfunction=0x0A)
        finally:
            proto.disconnect()
        assert result.success is True


class TestIntegrationWriteDataByIdentifier:
    def test_write_did_f190(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.write_data_by_identifier(did=0xF190, data=b"NEWVIN00000000001")
        finally:
            proto.disconnect()
        assert result.success is True

    def test_write_readonly_did_returns_nrc(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.write_data_by_identifier(did=0xF18C, data=b"TEST")
        finally:
            proto.disconnect()
        assert result.success is False
        assert result.nrc_code == 0x31


class TestIntegrationRoutineControl:
    def test_start_routine(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.routine_control(subfunction=0x01, routine_id=0x0201)
        finally:
            proto.disconnect()
        assert result.success is True
        assert result.routine_id == 0x0201

    def test_request_routine_results(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.routine_control(subfunction=0x03, routine_id=0x0201)
        finally:
            proto.disconnect()
        assert result.success is True

    def test_unsupported_routine_returns_nrc(self, ecu_simulator):
        svc, proto = _make_service(ecu_simulator)
        try:
            result = svc.routine_control(subfunction=0x01, routine_id=0x9999)
        finally:
            proto.disconnect()
        assert result.success is False
        assert result.nrc_code == 0x31
