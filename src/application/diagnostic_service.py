"""ApplicationLayer: CLI/GUIが共有するコアロジック。"""
from typing import Optional
from src.protocol.protocol_base import ProtocolBase
from src.uds.read_data_by_identifier import ReadDataByIdentifier
from src.uds.diagnostic_session_control import DiagnosticSessionControl
from src.uds.tester_present import TesterPresent
from src.uds.ecu_reset import ECUReset
from src.uds.clear_dtc import ClearDTC
from src.uds.read_dtc_information import ReadDTCInformation
from src.uds.write_data_by_identifier import WriteDataByIdentifier
from src.uds.routine_control import RoutineControl
from src.uds.service_base import (
    UDSResult, SessionResult, TesterPresentResult, SimpleResult
)
from src.uds.read_dtc_information import ReadDTCResult
from src.uds.routine_control import RoutineControlResult
from src.logger.uds_logger import UDSLogger


class DiagnosticService:

    def __init__(
        self,
        protocol: ProtocolBase,
        log_path: Optional[str] = None,
        log_level: str = "INFO",
    ):
        self._protocol = protocol
        self._logger   = UDSLogger(log_path, log_level) if log_path else None
        self._rdbi  = ReadDataByIdentifier()
        self._dsc   = DiagnosticSessionControl()
        self._tp    = TesterPresent()
        self._reset = ECUReset()
        self._clear = ClearDTC()
        self._rdtc  = ReadDTCInformation()
        self._wdbi  = WriteDataByIdentifier()
        self._rc    = RoutineControl()

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
        if suppress_response:
            return TesterPresentResult(success=True)
        raw = self._protocol.receive()
        result = self._tp.parse_response(raw)
        self._recv_log(sid=0x3E, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x11 ECUReset
    # ------------------------------------------------------------------ #
    def ecu_reset(self, reset_type: int) -> SimpleResult:
        request = self._reset.build_request(reset_type)
        self._send(sid=0x11, request=request)
        raw = self._protocol.receive()
        result = self._reset.parse_response(raw)
        self._recv_log(sid=0x11, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x14 ClearDiagnosticInformation
    # ------------------------------------------------------------------ #
    def clear_dtc(self, group_of_dtc: int = 0xFFFFFF) -> SimpleResult:
        request = self._clear.build_request(group_of_dtc)
        self._send(sid=0x14, request=request)
        raw = self._protocol.receive()
        result = self._clear.parse_response(raw)
        self._recv_log(sid=0x14, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x19 ReadDTCInformation
    # ------------------------------------------------------------------ #
    def read_dtc(self, subfunction: int, status_mask: int = 0xFF) -> ReadDTCResult:
        request = self._rdtc.build_request(subfunction, status_mask)
        self._send(sid=0x19, request=request)
        raw = self._protocol.receive()
        result = self._rdtc.parse_response(raw)
        self._recv_log(sid=0x19, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x2E WriteDataByIdentifier
    # ------------------------------------------------------------------ #
    def write_data_by_identifier(self, did: int, data: bytes) -> SimpleResult:
        request = self._wdbi.build_request(did, data)
        self._send(sid=0x2E, request=request)
        raw = self._protocol.receive()
        result = self._wdbi.parse_response(raw, did=did)
        self._recv_log(sid=0x2E, raw=raw, nrc=result.nrc_code)
        return result

    # ------------------------------------------------------------------ #
    # SID 0x31 RoutineControl
    # ------------------------------------------------------------------ #
    def routine_control(
        self,
        subfunction: int,
        routine_id: int,
        option_record: bytes = b"",
    ) -> RoutineControlResult:
        request = self._rc.build_request(subfunction, routine_id, option_record)
        self._send(sid=0x31, request=request)
        raw = self._protocol.receive()
        result = self._rc.parse_response(raw)
        self._recv_log(sid=0x31, raw=raw, nrc=result.nrc_code)
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
