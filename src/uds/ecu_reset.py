"""UDS SID=0x11 ECUReset。"""
import udsoncan
from udsoncan.services import ECUReset as _ECUReset
from src.uds.service_base import SimpleResult
from src.uds.nrc import NRCDecoder

HARD_RESET  = 0x01
SOFT_RESET  = 0x03
VALID_RESET_TYPES = {HARD_RESET, SOFT_RESET}


class ECUReset:

    def build_request(self, reset_type: int) -> bytes:
        if reset_type not in VALID_RESET_TYPES:
            raise ValueError(
                f"reset_type must be 0x01 (hard) or 0x03 (soft), got {hex(reset_type)}"
            )
        return udsoncan.Request(service=_ECUReset, subfunction=reset_type).get_payload()

    def parse_response(self, raw: bytes) -> SimpleResult:
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return SimpleResult(
                success=False, nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc), raw_response=raw,
            )
        return SimpleResult(success=True, raw_response=raw)
