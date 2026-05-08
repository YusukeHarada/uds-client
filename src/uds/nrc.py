"""
NRCコード定義と人間可読変換。

udsoncanがNRCの解釈を持つが、CLIやログでの表示文言を
プロジェクト側で制御するためにこのモジュールを維持する。
"""

_NRC_TABLE: dict[int, str] = {
    0x10: "General Reject",
    0x11: "Service Not Supported",
    0x12: "Sub Function Not Supported",
    0x13: "Incorrect Message Length Or Invalid Format",
    0x14: "Response Too Long",
    0x21: "Busy Repeat Request",
    0x22: "Conditions Not Correct",
    0x24: "Request Sequence Error",
    0x25: "No Response From Sub Net Component",
    0x26: "Failure Prevents Execution",
    0x31: "Request Out Of Range",
    0x33: "Security Access Denied",
    0x35: "Invalid Key",
    0x36: "Exceeded Number Of Attempts",
    0x37: "Required Time Delay Not Expired",
    0x70: "Upload Download Not Accepted",
    0x71: "Transfer Data Suspended",
    0x72: "General Programming Failure",
    0x73: "Wrong Block Sequence Counter",
    0x78: "Response Pending",
    0x7E: "Sub Function Not Supported In Active Session",
    0x7F: "Service Not Supported In Active Session",
}


class NRCDecoder:
    @staticmethod
    def decode(nrc_code: int) -> str:
        """NRCコードを人間可読文字列に変換する。未知のコードは16進数で返す。"""
        return _NRC_TABLE.get(nrc_code, f"Unknown NRC ({hex(nrc_code)})")
