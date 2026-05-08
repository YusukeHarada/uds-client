"""UDSLogger ユニットテスト"""
import json
import pytest
from src.logger.uds_logger import UDSLogger


class TestUDSLogger:

    def test_log_tx_writes_required_fields(self, tmp_path):
        log_file = tmp_path / "test.json"
        logger = UDSLogger(path=str(log_file), level="DEBUG")

        logger.log_tx(sid=0x22, raw=bytes([0x22, 0xF1, 0x90]))

        entries = [json.loads(line) for line in log_file.read_text().splitlines()]
        assert len(entries) == 1
        e = entries[0]
        assert e["direction"] == "TX"
        assert e["sid"] == "0x22"
        assert e["raw_hex"] == "22 F1 90"
        assert "timestamp" in e

    def test_log_rx_without_nrc(self, tmp_path):
        log_file = tmp_path / "test.json"
        logger = UDSLogger(path=str(log_file), level="DEBUG")

        logger.log_rx(sid=0x22, raw=bytes([0x62, 0xF1, 0x90, 0x01]))

        entries = [json.loads(line) for line in log_file.read_text().splitlines()]
        e = entries[0]
        assert e["direction"] == "RX"
        assert "nrc" not in e

    def test_log_rx_with_nrc_includes_decoded_message(self, tmp_path):
        log_file = tmp_path / "test.json"
        logger = UDSLogger(path=str(log_file), level="DEBUG")

        logger.log_rx(sid=0x22, raw=bytes([0x7F, 0x22, 0x31]), nrc=0x31)

        entries = [json.loads(line) for line in log_file.read_text().splitlines()]
        e = entries[0]
        assert e["nrc"] == "0x31"
        assert e["nrc_message"] == "Request Out Of Range"

    def test_multiple_entries_appended(self, tmp_path):
        log_file = tmp_path / "test.json"
        logger = UDSLogger(path=str(log_file), level="DEBUG")

        logger.log_tx(sid=0x22, raw=bytes([0x22, 0xF1, 0x90]))
        logger.log_rx(sid=0x22, raw=bytes([0x62, 0xF1, 0x90, 0xAB]))

        entries = [json.loads(line) for line in log_file.read_text().splitlines()]
        assert len(entries) == 2
        assert entries[0]["direction"] == "TX"
        assert entries[1]["direction"] == "RX"
