"""
結合テスト: ECUシミュレータを使った実TCP通信テスト

テスト内でシミュレータをスレッド起動し、
実際にDoIP/TCPで通信してE2Eを検証する。
実ECU不要でCIでも実行可能。
"""
import threading
import time
import pytest

from ecu_simulator import run_server
from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol

SIM_HOST = "127.0.0.1"
SIM_PORT = 15740  # テスト専用ポート


@pytest.fixture(scope="module")
def ecu_simulator():
    """モジュールスコープでECUシミュレータをスレッド起動・停止する。"""
    stop_event = threading.Event()
    thread = threading.Thread(
        target=run_server,
        kwargs={"host": SIM_HOST, "port": SIM_PORT, "stop_event": stop_event},
        daemon=True,
    )
    thread.start()
    time.sleep(0.2)  # サーバ起動待ち
    yield {"host": SIM_HOST, "port": SIM_PORT}
    stop_event.set()
    thread.join(timeout=2.0)


class TestIntegrationDoIP:
    """実TCP通信を使った結合テスト。"""

    def test_read_vin_did_f190(self, ecu_simulator):
        """DID=F190のVINが正常に取得できる"""
        protocol = DoIPProtocol(
            host=ecu_simulator["host"],
            port=ecu_simulator["port"],
            target_address=0x1000,
        )
        protocol.connect()
        service = DiagnosticService(protocol=protocol)
        try:
            result = service.read_data_by_identifier(did=0xF190)
        finally:
            protocol.disconnect()

        assert result.success is True
        assert result.did == 0xF190
        assert result.data == b"SIMVIN0000000001"

    def test_read_unknown_did_returns_nrc(self, ecu_simulator):
        """存在しないDIDはNRC 0x31になる"""
        protocol = DoIPProtocol(
            host=ecu_simulator["host"],
            port=ecu_simulator["port"],
            target_address=0x1000,
        )
        protocol.connect()
        service = DiagnosticService(protocol=protocol)
        try:
            result = service.read_data_by_identifier(did=0x1234)
        finally:
            protocol.disconnect()

        assert result.success is False
        assert result.nrc_code == 0x31
        assert result.nrc_message == "Request Out Of Range"

    def test_read_with_log_output(self, ecu_simulator, tmp_path):
        """結合テストでもログが正常に記録される"""
        import json
        log_file = tmp_path / "integration.log.json"

        protocol = DoIPProtocol(
            host=ecu_simulator["host"],
            port=ecu_simulator["port"],
            target_address=0x1000,
        )
        protocol.connect()
        service = DiagnosticService(
            protocol=protocol,
            log_path=str(log_file),
        )
        try:
            service.read_data_by_identifier(did=0xF190)
        finally:
            protocol.disconnect()

        entries = [json.loads(l) for l in log_file.read_text().splitlines()]
        assert any(e["direction"] == "TX" for e in entries)
        assert any(e["direction"] == "RX" for e in entries)
