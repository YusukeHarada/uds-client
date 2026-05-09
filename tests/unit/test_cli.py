"""CLI サブコマンド ユニットテスト"""
import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from main import cli
from src.uds.service_base import UDSResult, SessionResult, TesterPresentResult, SimpleResult
from src.uds.read_dtc_information import ReadDTCResult, DTCRecord
from src.uds.routine_control import RoutineControlResult
from src.protocol.protocol_base import ProtocolBase


def _make_runner():
    return CliRunner()


def _patch_service(mock_service):
    """DoIPProtocolとDiagnosticServiceを両方モックするコンテキストマネージャ。"""
    return patch("main.DoIPProtocol", return_value=MagicMock(spec=ProtocolBase)), \
           patch("main.DiagnosticService", return_value=mock_service)


class TestCLIRdbi:
    def test_rdbi_success(self):
        svc = MagicMock()
        svc.read_data_by_identifier.return_value = UDSResult(
            success=True, did=0xF190, data=b"SIMVIN0000000001"
        )
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "rdbi", "F190"])
        assert result.exit_code == 0
        assert "[OK]" in result.output
        assert "f190" in result.output.lower()

    def test_rdbi_nrc(self):
        svc = MagicMock()
        svc.read_data_by_identifier.return_value = UDSResult(
            success=False, did=0x9999, nrc_code=0x31, nrc_message="Request Out Of Range"
        )
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "rdbi", "9999"])
        assert result.exit_code == 2
        assert "0x31" in result.output
        assert "Request Out Of Range" in result.output

    def test_rdbi_invalid_did(self):
        result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "rdbi", "ZZZZ"])
        assert result.exit_code != 0


class TestCLISession:
    def test_session_success(self):
        svc = MagicMock()
        svc.change_session.return_value = SessionResult(success=True, session_type=0x03)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "session", "03"])
        assert result.exit_code == 0
        assert "[OK]" in result.output
        assert "0x3" in result.output


class TestCLITesterPresent:
    def test_tester_present_success(self):
        svc = MagicMock()
        svc.tester_present.return_value = TesterPresentResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "tester-present"])
        assert result.exit_code == 0
        assert "[OK]" in result.output

    def test_tester_present_suppress(self):
        svc = MagicMock()
        svc.tester_present.return_value = TesterPresentResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "tester-present", "--suppress"]
            )
        assert result.exit_code == 0
        assert "suppressed" in result.output
        svc.tester_present.assert_called_once_with(suppress_response=True)


class TestCLIReset:
    def test_hard_reset(self):
        svc = MagicMock()
        svc.ecu_reset.return_value = SimpleResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "reset", "hard"])
        assert result.exit_code == 0
        assert "[OK]" in result.output
        svc.ecu_reset.assert_called_once_with(reset_type=0x01)

    def test_soft_reset(self):
        svc = MagicMock()
        svc.ecu_reset.return_value = SimpleResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "reset", "soft"])
        assert result.exit_code == 0
        svc.ecu_reset.assert_called_once_with(reset_type=0x03)


class TestCLIClearDTC:
    def test_clear_all_dtc(self):
        svc = MagicMock()
        svc.clear_dtc.return_value = SimpleResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(cli, ["--ip", "127.0.0.1", "clear-dtc"])
        assert result.exit_code == 0
        svc.clear_dtc.assert_called_once_with(group_of_dtc=0xFFFFFF)

    def test_clear_specific_group(self):
        svc = MagicMock()
        svc.clear_dtc.return_value = SimpleResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "clear-dtc", "--group", "012345"]
            )
        assert result.exit_code == 0
        svc.clear_dtc.assert_called_once_with(group_of_dtc=0x012345)


class TestCLIReadDTC:
    def test_read_dtc_with_records(self):
        svc = MagicMock()
        svc.read_dtc.return_value = ReadDTCResult(
            success=True,
            subfunction=0x02,
            dtc_records=[
                DTCRecord(dtc=0x012345, status=0x08),
                DTCRecord(dtc=0x00ABCD, status=0x09),
            ]
        )
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "read-dtc", "--subfn", "02"]
            )
        assert result.exit_code == 0
        assert "件数=2" in result.output
        assert "0x12345" in result.output

    def test_read_dtc_no_records(self):
        svc = MagicMock()
        svc.read_dtc.return_value = ReadDTCResult(
            success=True, subfunction=0x02, dtc_records=[]
        )
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "read-dtc", "--subfn", "02"]
            )
        assert result.exit_code == 0
        assert "DTCなし" in result.output


class TestCLIWdbi:
    def test_wdbi_success(self):
        svc = MagicMock()
        svc.write_data_by_identifier.return_value = SimpleResult(success=True)
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "wdbi", "F190", "--data", "4E455756494E"]
            )
        assert result.exit_code == 0
        assert "[OK]" in result.output

    def test_wdbi_invalid_data(self):
        result = _make_runner().invoke(
            cli, ["--ip", "127.0.0.1", "wdbi", "F190", "--data", "ZZZZ"]
        )
        assert result.exit_code != 0


class TestCLIRoutine:
    def test_routine_start_success(self):
        svc = MagicMock()
        svc.routine_control.return_value = RoutineControlResult(
            success=True, subfunction=0x01, routine_id=0x0201, routine_status_record=b""
        )
        proto_patch, svc_patch = _patch_service(svc)
        with proto_patch, svc_patch:
            result = _make_runner().invoke(
                cli, ["--ip", "127.0.0.1", "routine", "01", "0201"]
            )
        assert result.exit_code == 0
        assert "[OK]" in result.output
        assert "0x201" in result.output
