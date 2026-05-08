"""
ApplicationLayer: CLI/GUIが共有するコアロジック。

このクラスはUIに一切依存しない。
CLI（main.py）もGUI（PyQt、Step3で追加）もこのクラスのメソッドを呼ぶだけでよい。
プロトコルはProtocolBase経由で注入するため、テスト時はモックに差し替え可能。
"""
from typing import Optional
from src.protocol.protocol_base import ProtocolBase
from src.uds.read_data_by_identifier import ReadDataByIdentifier
from src.uds.service_base import UDSResult
from src.logger.uds_logger import UDSLogger


class DiagnosticService:

    def __init__(
        self,
        protocol: ProtocolBase,
        log_path: Optional[str] = None,
        log_level: str = "INFO",
    ):
        self._protocol = protocol
        self._logger = UDSLogger(log_path, log_level) if log_path else None
        self._rdbi = ReadDataByIdentifier()

    def read_data_by_identifier(self, did: int) -> UDSResult:
        """
        SID=0x22 ReadDataByIdentifierを実行してUDSResultを返す。

        TX/RXフレームはログに記録される（log_path指定時のみ）。
        NRC応答はsuccess=Falseとして返し、例外にはしない。
        プロトコル異常（接続切断・タイムアウト等）は例外として伝播する。
        """
        request = self._rdbi.build_request(did)

        if self._logger:
            self._logger.log_tx(sid=0x22, raw=request)

        self._protocol.send(request)
        raw_response = self._protocol.receive()

        result = self._rdbi.parse_response(raw_response, did=did)

        if self._logger:
            self._logger.log_rx(sid=0x22, raw=raw_response, nrc=result.nrc_code)

        return result
