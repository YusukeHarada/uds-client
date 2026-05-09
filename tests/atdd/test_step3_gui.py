"""ATDD: Step3 GUI受け入れテストシナリオ"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt

from src.uds.service_base import UDSResult, SessionResult, TesterPresentResult
from src.protocol.protocol_base import ProtocolBase


def _make_mock_service():
    svc = MagicMock()
    svc.read_data_by_identifier.return_value = UDSResult(
        success=True, did=0xF190, data=b"SIMVIN0000000001"
    )
    svc.change_session.return_value = SessionResult(success=True, session_type=0x03)
    svc.tester_present.return_value = TesterPresentResult(success=True)
    return svc


@pytest.fixture
def window(qtbot):
    mock_protocol = MagicMock(spec=ProtocolBase)
    mock_service  = _make_mock_service()
    with patch("src.gui.main_window.DoIPProtocol", return_value=mock_protocol), \
         patch("src.gui.main_window.DiagnosticService", return_value=mock_service):
        from src.gui.main_window import MainWindow
        w = MainWindow()
        qtbot.addWidget(w)
        w.show()
        yield w, mock_service, mock_protocol


def _connect(qtbot, w):
    w.ip_input.setText("127.0.0.1")
    w.port_input.setText("13400")
    qtbot.mouseClick(w.connect_button, Qt.LeftButton)


def _click_and_wait(qtbot, w, button):
    """sid_finishedシグナルを待ってからスレッド完了とみなす。"""
    with qtbot.waitSignal(w.sid_finished, timeout=3000):
        qtbot.mouseClick(button, Qt.LeftButton)


class TestStep3GUIAcceptance:

    def test_connect_button_calls_protocol_connect(self, qtbot, window):
        w, svc, protocol = window
        _connect(qtbot, w)
        protocol.connect.assert_called_once()
        assert "接続中" in w.status_label.text()

    def test_rdbi_result_displayed_on_success(self, qtbot, window):
        w, svc, protocol = window
        _connect(qtbot, w)
        w.did_input.setText("F190")
        _click_and_wait(qtbot, w, w.rdbi_button)
        result_text = w.result_view.toPlainText()
        assert "OK" in result_text
        assert "f190" in result_text.lower()

    def test_nrc_response_displayed_as_human_readable(self, qtbot, window):
        w, svc, protocol = window
        svc.read_data_by_identifier.return_value = UDSResult(
            success=False, did=0x1234,
            nrc_code=0x31, nrc_message="Request Out Of Range"
        )
        _connect(qtbot, w)
        w.did_input.setText("1234")
        _click_and_wait(qtbot, w, w.rdbi_button)
        result_text = w.result_view.toPlainText()
        assert "0x31" in result_text
        assert "Request Out Of Range" in result_text

    def test_session_control_result_displayed(self, qtbot, window):
        w, svc, protocol = window
        _connect(qtbot, w)
        w.session_combo.setCurrentIndex(2)  # 0x03 Extended
        _click_and_wait(qtbot, w, w.session_button)
        result_text = w.result_view.toPlainText()
        assert "OK" in result_text
        assert "0x3" in result_text

    def test_tester_present_result_displayed(self, qtbot, window):
        w, svc, protocol = window
        _connect(qtbot, w)
        _click_and_wait(qtbot, w, w.tp_button)
        result_text = w.result_view.toPlainText()
        assert "OK" in result_text
        assert "TesterPresent" in result_text

    def test_clear_button_empties_result_view(self, qtbot, window):
        w, svc, protocol = window
        _connect(qtbot, w)
        w.did_input.setText("F190")
        _click_and_wait(qtbot, w, w.rdbi_button)
        qtbot.mouseClick(w.clear_button, Qt.LeftButton)
        assert w.result_view.toPlainText() == ""
