"""NRCDecoder ユニットテスト"""
import pytest
from src.uds.nrc import NRCDecoder


class TestNRCDecoder:

    def test_0x31_returns_request_out_of_range(self):
        assert NRCDecoder.decode(0x31) == "Request Out Of Range"

    def test_0x22_returns_conditions_not_correct(self):
        assert NRCDecoder.decode(0x22) == "Conditions Not Correct"

    def test_0x78_returns_response_pending(self):
        assert NRCDecoder.decode(0x78) == "Response Pending"

    def test_0x7f_returns_service_not_supported_in_active_session(self):
        assert NRCDecoder.decode(0x7F) == "Service Not Supported In Active Session"

    def test_unknown_nrc_returns_formatted_hex(self):
        assert NRCDecoder.decode(0xFF) == "Unknown NRC (0xff)"

    def test_unknown_nrc_0x00_returns_formatted_hex(self):
        assert NRCDecoder.decode(0x00) == "Unknown NRC (0x0)"
