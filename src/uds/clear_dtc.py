"""UDS SID=0x14 ClearDiagnosticInformation。"""
import udsoncan
from udsoncan.services import ClearDiagnosticInformation as _ClearDTC
from src.uds.service_base import SimpleResult
from src.uds.nrc import NRCDecoder

GROUP_OF_DTC_ALL = 0xFFFFFF


class ClearDTC:

    def build_request(self, group_of_dtc: int = GROUP_OF_DTC_ALL) -> bytes:
        if not (0x000000 <= group_of_dtc <= 0xFFFFFF):
            raise ValueError(
                f"group_of_dtc must be in 0x000000-0xFFFFFF, got {hex(group_of_dtc)}"
            )
        request = udsoncan.Request(service=_ClearDTC)
        request.data = group_of_dtc.to_bytes(3, "big")
        return request.get_payload()

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
