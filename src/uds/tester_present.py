"""UDS SID=0x3E TesterPresent。"""
import udsoncan
from udsoncan.services import TesterPresent as _TP
from src.uds.service_base import TesterPresentResult
from src.uds.nrc import NRCDecoder

SUPPRESS_RESPONSE_BIT = 0x80


class TesterPresent:

    def build_request(self, suppress_response: bool = False) -> bytes:
        sub_function = SUPPRESS_RESPONSE_BIT if suppress_response else 0x00
        # TesterPresentはuse_subfunction=Trueなのでsubfunctionにセットする
        request = udsoncan.Request(service=_TP, subfunction=sub_function)
        return request.get_payload()

    def parse_response(self, raw: bytes) -> TesterPresentResult:
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return TesterPresentResult(
                success=False,
                nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc),
                raw_response=raw,
            )

        return TesterPresentResult(success=True, raw_response=raw)
