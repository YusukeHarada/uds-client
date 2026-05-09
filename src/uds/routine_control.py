"""UDS SID=0x31 RoutineControl。

対応サブファンクション:
  0x01 startRoutine
  0x02 stopRoutine
  0x03 requestRoutineResults
"""
from dataclasses import dataclass
from typing import Optional
import udsoncan
from udsoncan.services import RoutineControl as _RC
from src.uds.service_base import SimpleResult
from src.uds.nrc import NRCDecoder

START_ROUTINE   = 0x01
STOP_ROUTINE    = 0x02
REQUEST_RESULTS = 0x03
VALID_SUBFUNCTIONS = {START_ROUTINE, STOP_ROUTINE, REQUEST_RESULTS}


@dataclass
class RoutineControlResult:
    success: bool
    subfunction: Optional[int] = None
    routine_id: Optional[int] = None
    routine_status_record: Optional[bytes] = None
    nrc_code: Optional[int] = None
    nrc_message: Optional[str] = None
    raw_response: Optional[bytes] = None


class RoutineControl:

    def build_request(
        self,
        subfunction: int,
        routine_id: int,
        option_record: bytes = b"",
    ) -> bytes:
        if subfunction not in VALID_SUBFUNCTIONS:
            raise ValueError(
                f"subfunction must be one of "
                f"{[hex(s) for s in VALID_SUBFUNCTIONS]}, got {hex(subfunction)}"
            )
        if not (0x0000 <= routine_id <= 0xFFFF):
            raise ValueError(f"routine_id must be in 0x0000-0xFFFF, got {hex(routine_id)}")

        request = udsoncan.Request(service=_RC, subfunction=subfunction)
        request.data = bytes([(routine_id >> 8) & 0xFF, routine_id & 0xFF]) + option_record
        return request.get_payload()

    def parse_response(self, raw: bytes) -> RoutineControlResult:
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return RoutineControlResult(
                success=False, nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc), raw_response=raw,
            )

        data = response.data
        # data[0]=subfunction echo, data[1:3]=routineId echo, data[3:]=statusRecord
        subfunction = data[0]
        routine_id  = (data[1] << 8) | data[2]
        status_record = data[3:] if len(data) > 3 else b""

        return RoutineControlResult(
            success=True,
            subfunction=subfunction,
            routine_id=routine_id,
            routine_status_record=status_record,
            raw_response=raw,
        )
