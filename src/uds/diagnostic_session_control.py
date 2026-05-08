"""UDS SID=0x10 DiagnosticSessionControl。"""
import udsoncan
from udsoncan.services import DiagnosticSessionControl as _DSC
from src.uds.service_base import SessionResult
from src.uds.nrc import NRCDecoder

# ISO 14229-1: 0x00は予約済み、0x80-0xFFはISOReserved
_VALID_SESSION_RANGE = range(0x01, 0x80)


class DiagnosticSessionControl:

    def build_request(self, session_type: int) -> bytes:
        if session_type not in _VALID_SESSION_RANGE:
            raise ValueError(
                f"session_type must be in 0x01-0x7F, got {hex(session_type)}"
            )
        # DSCはuse_subfunction=Trueなのでsubfunctionにセットする
        request = udsoncan.Request(service=_DSC, subfunction=session_type)
        return request.get_payload()

    def parse_response(self, raw: bytes) -> SessionResult:
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return SessionResult(
                success=False,
                nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc),
                raw_response=raw,
            )

        # Positive Response: data[0] = echo-back of session_type
        session_type = response.data[0]
        return SessionResult(
            success=True,
            session_type=session_type,
            raw_response=raw,
        )
