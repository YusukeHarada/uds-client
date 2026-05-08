"""UDSResult pydanticモデル ユニットテスト"""
import pytest
from pydantic import ValidationError
from src.uds.service_base import UDSResult


class TestUDSResult:

    def test_positive_result_fields(self):
        r = UDSResult(success=True, did=0xF190, data=b"VIN12345678901234")
        assert r.success is True
        assert r.did == 0xF190
        assert r.data == b"VIN12345678901234"

    def test_negative_result_fields(self):
        r = UDSResult(success=False, nrc_code=0x31, nrc_message="Request Out Of Range")
        assert r.success is False
        assert r.nrc_code == 0x31

    def test_did_out_of_range_raises_validation_error(self):
        with pytest.raises(ValidationError, match="0x0000-0xFFFF"):
            UDSResult(success=True, did=0x10000)

    def test_nrc_code_out_of_range_raises_validation_error(self):
        with pytest.raises(ValidationError, match="0x0000-0xFFFF"):
            UDSResult(success=False, nrc_code=-1)

    def test_optional_fields_default_to_none(self):
        r = UDSResult(success=True)
        assert r.did is None
        assert r.data is None
        assert r.nrc_code is None
