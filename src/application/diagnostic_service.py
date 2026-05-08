"""ApplicationLayer: CLI/GUIが共有するコアロジック。"""
from typing import Optional
from src.protocol.protocol_base import ProtocolBase
from src.uds.read_data_by_identifier import ReadDataByIdentifier
from src.uds.diagnostic_session_control import DiagnosticSessionControl
from src.uds.tester_present import TesterPresent
from src.uds.service_base import UDSResult, SessionResult, TesterPresentResult
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
        self._dsc  = DiagnosticSessionControl()
        self._tp   = TesterPresent()

    # ------------------------------------------------------------------ #
    # SID 0x22 ReadDataByIdentifier
    # ------------------------------------------------------------------ #
    def read_data_by_identifier(self, did: int) -> UDSResult:
        request = self._rdbi.build_request(did)
        self._send(sid=0x22, request=request)
        raw = self._protocol.receive()
        result = self._rdbi.parse_response(raw, did=did)
        self._recv_log(sid=0x22, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x10 DiagnosticSessionControl
    # ------------------------------------------------------------------ #
    def change_session(self, session_type: int) -> SessionResult:
        request = self._dsc.build_request(session_type)
        self._send(sid=0x10, request=request)
        raw = self._protocol.receive()
        result = self._dsc.parse_response(raw)
        self._recv_log(sid=0x10, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x3E TesterPresent
    # ------------------------------------------------------------------ #
    def tester_present(self, suppress_response: bool = False) -> TesterPresentResult:
        request = self._tp.build_request(suppress_response=suppress_response)
        self._send(sid=0x3E, request=request)

        # suppress_response=Trueのときはレスポンスを待たない
        if suppress_response:
            return TesterPresentResult(success=True)

        raw = self._protocol.receive()
        result = self._tp.parse_response(raw)
        self._recv_log(sid=0x3E, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # 共通ヘルパー
    # ------------------------------------------------------------------ #
    def _send(self, sid: int, request: bytes) -> None:
        if self._logger:
            self._logger.log_tx(sid=sid, raw=request)
        self._protocol.send(request)

    def _recv_log(self, sid: int, raw: bytes, nrc: Optional[int]) -> None:
        if self._logger:
            self._logger.log_rx(sid=sid, raw=raw, nrc=nrc)
