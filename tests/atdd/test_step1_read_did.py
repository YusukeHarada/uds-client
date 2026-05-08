"""
ATDD: Step1 受け入れテストシナリオ

ユーザー視点のシナリオをProtocolBaseのモックでE2Eに近い形で検証する。
doipclient/ネットワークは不要。

Scenario 1: DID=F190(VIN)の読み取りに成功する
Scenario 2: 存在しないDIDを読もうとするとNRCエラーになる
Scenario 3: 通信ログがJSONファイルに記録される
"""
import json
import pytest
import udsoncan
from udsoncan.services import ReadDataByIdentifier as _RDBI
from unittest.mock import MagicMock
from src.application.diagnostic_service import DiagnosticService
from src.protocol.protocol_base import ProtocolBase


class TestStep1AcceptanceReadDID:

    def setup_method(self):
        # ProtocolBaseをモックすることでネットワーク不要
        self.mock_protocol = MagicMock(spec=ProtocolBase)
        self.service = DiagnosticService(protocol=self.mock_protocol)

    def _make_positive_response(self, did: int, data: bytes) -> bytes:
        """udsoncanで正規のPositive Responseペイロードを生成するヘルパー。"""
        resp = udsoncan.Response(
            service=_RDBI,
            code=udsoncan.Response.Code.PositiveResponse,
        )
        resp.data = bytes([(did >> 8) & 0xFF, did & 0xFF]) + data
        return resp.get_payload()

    def _make_nrc_response(self, nrc_code: int) -> bytes:
        """udsoncanで正規のNegative Responseペイロードを生成するヘルパー。"""
        resp = udsoncan.Response(
            service=_RDBI,
            code=nrc_code,
        )
        return resp.get_payload()

    # ------------------------------------------------------------------ #
    # Scenario 1: 正常応答
    # ------------------------------------------------------------------ #
    def test_read_did_f190_returns_vin(self):
        """
        Given: ECUがDID F190に対してVINデータを返す
        When:  read_data_by_identifier(did=0xF190)を呼ぶ
        Then:  success=True、dataにVINバイト列が入る
        """
        vin = b"1HGBH41JXMN109186"
        self.mock_protocol.receive.return_value = self._make_positive_response(0xF190, vin)

        result = self.service.read_data_by_identifier(did=0xF190)

        assert result.success is True
        assert result.did == 0xF190
        assert result.data == vin

    # ------------------------------------------------------------------ #
    # Scenario 2: NRCエラー
    # ------------------------------------------------------------------ #
    def test_read_did_unknown_returns_nrc_request_out_of_range(self):
        """
        Given: ECUがNRC 0x31(Request Out Of Range)を返す
        When:  read_data_by_identifier(did=0x9999)を呼ぶ
        Then:  success=False、nrc_message が人間可読になる
        """
        self.mock_protocol.receive.return_value = self._make_nrc_response(0x31)

        result = self.service.read_data_by_identifier(did=0x9999)

        assert result.success is False
        assert result.nrc_code == 0x31
        assert result.nrc_message == "Request Out Of Range"

    # ------------------------------------------------------------------ #
    # Scenario 3: ログ記録
    # ------------------------------------------------------------------ #
    def test_communication_log_is_written_as_json(self, tmp_path):
        """
        Given: log_pathを指定してDiagnosticServiceを作成する
        When:  read_data_by_identifier を呼ぶ
        Then:  JSON Linesファイルに TX/RX エントリが記録される
        """
        log_file = tmp_path / "uds.log.json"
        vin = b"TEST_VIN_12345678"
        self.mock_protocol.receive.return_value = self._make_positive_response(0xF190, vin)

        service = DiagnosticService(
            protocol=self.mock_protocol,
            log_path=str(log_file),
        )
        service.read_data_by_identifier(did=0xF190)

        assert log_file.exists()
        entries = [json.loads(line) for line in log_file.read_text().splitlines()]
        assert any(e["direction"] == "TX" for e in entries)
        assert any(e["direction"] == "RX" for e in entries)
        assert all("timestamp" in e for e in entries)
        assert all("raw_hex" in e for e in entries)
