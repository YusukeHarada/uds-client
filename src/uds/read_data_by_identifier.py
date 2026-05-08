"""
UDS SID=0x22 ReadDataByIdentifier。

udsoncanのRequest/Responseクラスを利用してフレーム生成・解析を行う。
自前でバイト列を組み立てないことでフレーム構造バグを防ぐ。
NRC表示文言のみ自前のNRCDecoderを使用する。
"""
import udsoncan
from udsoncan.services import ReadDataByIdentifier as _RDBI
from src.uds.service_base import UDSResult
from src.uds.nrc import NRCDecoder


class ReadDataByIdentifier:

    def build_request(self, did: int) -> bytes:
        """DIDを指定してUDSリクエストペイロードを生成する。"""
        if not (0x0000 <= did <= 0xFFFF):
            raise ValueError(
                f"DID must be in range 0x0000-0xFFFF, got {hex(did)}"
            )
        request = udsoncan.Request(service=_RDBI)
        request.data = bytes([(did >> 8) & 0xFF, did & 0xFF])
        return request.get_payload()

    def parse_response(self, raw: bytes, did: int) -> UDSResult:
        """
        ECUからの生バイト列をUDSResultに変換する。

        Negative Response (0x7F) の場合はsuccess=Falseとnrc情報を返す。
        DIDミスマッチはValueErrorとする（プロトコル異常として扱う）。
        """
        try:
            response = udsoncan.Response.from_payload(raw)
        except udsoncan.exceptions.InvalidResponseException as e:
            raise ValueError(f"Invalid UDS response: {e}") from e

        if not response.positive:
            nrc = response.code
            return UDSResult(
                success=False,
                did=did,
                nrc_code=nrc,
                nrc_message=NRCDecoder.decode(nrc),
                raw_response=raw,
            )

        # Positive Response: ペイロード先頭2バイトがDID
        payload = response.data
        resp_did = (payload[0] << 8) | payload[1]
        if resp_did != did:
            raise ValueError(
                f"DID mismatch: expected {hex(did)}, got {hex(resp_did)}"
            )

        return UDSResult(
            success=True,
            did=did,
            data=payload[2:],
            raw_response=raw,
        )
