"""UDS SID=0x2E WriteDataByIdentifier。"""
import udsoncan
from udsoncan.services import WriteDataByIdentifier as _WDBI
from src.uds.service_base import SimpleResult
from src.uds.nrc import NRCDecoder


class WriteDataByIdentifier:

    def build_request(self, did: int, data: bytes) -> bytes:
        if not (0x0000 <= did <= 0xFFFF):
            raise ValueError(f"DID must be in 0x0000-0xFFFF, got {hex(did)}")
        if not data:
            raise ValueError("data must not be empty")
        request = udsoncan.Request(service=_WDBI)
        request.data = bytes([(did >> 8) & 0xFF, did & 0xFF]) + data
        return request.get_payload()

    def parse_response(self, raw: bytes, did: int) -> SimpleResult:
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

        # Positive Response: data = DID echo (2bytes)
        resp_did = (response.data[0] << 8) | response.data[1]
        if resp_did != did:
            raise ValueError(
                f"DID mismatch: expected {hex(did)}, got {hex(resp_did)}"
            )
        return SimpleResult(success=True, raw_response=raw)
