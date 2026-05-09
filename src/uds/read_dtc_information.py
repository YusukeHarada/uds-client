"""UDS SID=0x19 ReadDTCInformation。

対応サブファンクション:
  0x02 reportDTCByStatusMask
  0x0A reportSupportedDTC
"""
from dataclasses import dataclass
from typing import Optional
import udsoncan
from udsoncan.services import ReadDTCInformation as _ReadDTC
from src.uds.service_base import SimpleResult
from src.uds.nrc import NRCDecoder

REPORT_BY_STATUS_MASK = 0x02
REPORT_SUPPORTED_DTC  = 0x0A
VALID_SUBFUNCTIONS    = {REPORT_BY_STATUS_MASK, REPORT_SUPPORTED_DTC}

DTC_RECORD_SIZE = 4  # DTC(3bytes) + statusByte(1byte)


@dataclass
class DTCRecord:
    dtc: int        # 3バイトDTCコード
    status: int     # ステータスバイト

    def __str__(self) -> str:
        return f"DTC={hex(self.dtc)}  status={hex(self.status)}"


@dataclass
class ReadDTCResult:
    success: bool
    subfunction: Optional[int] = None
    dtc_records: Optional[list[DTCRecord]] = None
    nrc_code: Optional[int] = None
    nrc_message: Optional[str] = None
    raw_response: Optional[bytes] = None


class ReadDTCInformation:

    def build_request(self, subfunction: int, status_mask: int = 0xFF) -> bytes:
        if subfunction not in VALID_SUBFUNCTIONS:
            raise ValueError(
                f"subfunction must be one of "
                f"{[hex(s) for s in VALID_SUBFUNCTIONS]}, got {hex(subfunction)}"
            )
        request = udsoncan.Request(service=_ReadDTC, subfunction=subfunction)
        if subfunction == REPORT_BY_STATUS_MASK:
            request.data = bytes([status_mask])
        return request.get_payload()

    def parse_response(self, raw: bytes) -> ReadDTCResult:
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return ReadDTCResult(
                success=False, nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc), raw_response=raw,
            )

        data = response.data
        # data[0]=subfunction echo, data[1]=statusAvailabilityMask, data[2:]=DTC records
        subfunction = data[0]
        dtc_data = data[2:] if len(data) >= 2 else b""
        records = []
        for i in range(0, len(dtc_data) - (DTC_RECORD_SIZE - 1), DTC_RECORD_SIZE):
            dtc    = (dtc_data[i] << 16) | (dtc_data[i+1] << 8) | dtc_data[i+2]
            status = dtc_data[i+3]
            records.append(DTCRecord(dtc=dtc, status=status))

        return ReadDTCResult(
            success=True,
            subfunction=subfunction,
            dtc_records=records,
            raw_response=raw,
        )
