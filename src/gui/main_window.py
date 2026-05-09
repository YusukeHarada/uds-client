"""
GUIメインウィンドウ (PySide6)

設計原則:
- DiagnosticServiceのみに依存し、UDS/プロトコル層には直接触れない
- UIロジック（表示・入力）のみを担当する
- UDS通信はQThreadで実行してGUIスレッドをブロックしない
- sid_finished シグナルでテストからスレッド完了を待機できる
"""
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QPlainTextEdit, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol
from src.protocol.protocol_base import ProtocolBase

SESSION_TYPES = [
    ("0x01  Default Session",            0x01),
    ("0x02  Programming Session",        0x02),
    ("0x03  Extended Diagnostic Session", 0x03),
]


class _Worker(QObject):
    finished = Signal(str)
    error    = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            self.finished.emit(self._fn(*self._args, **self._kwargs))
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    # テストからスレッド完了を待機するためのシグナル
    sid_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UDS診断ツール")
        self.setMinimumWidth(560)

        self._protocol: Optional[ProtocolBase] = None
        self._service:  Optional[DiagnosticService] = None
        self._thread:   Optional[QThread] = None
        self._worker:   Optional[_Worker] = None

        self._build_ui()
        self._set_connected(False)

    # ------------------------------------------------------------------ #
    # UI構築
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setSpacing(8)
        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_rdbi_group())
        layout.addWidget(self._build_session_group())
        layout.addWidget(self._build_tp_group())
        layout.addWidget(self._build_result_group())

    def _build_connection_group(self) -> QGroupBox:
        box = QGroupBox("接続設定")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("IP:"))
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setFixedWidth(140)
        row.addWidget(self.ip_input)
        row.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("13400")
        self.port_input.setFixedWidth(70)
        row.addWidget(self.port_input)
        self.connect_button = QPushButton("接続")
        self.connect_button.clicked.connect(self._on_connect)
        row.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("切断")
        self.disconnect_button.clicked.connect(self._on_disconnect)
        row.addWidget(self.disconnect_button)
        self.status_label = QLabel("● 未接続")
        self.status_label.setFixedWidth(100)
        row.addWidget(self.status_label)
        row.addStretch()
        return box

    def _build_rdbi_group(self) -> QGroupBox:
        box = QGroupBox("0x22  ReadDataByIdentifier")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("DID (hex):"))
        self.did_input = QLineEdit("F190")
        self.did_input.setFixedWidth(80)
        row.addWidget(self.did_input)
        self.rdbi_button = QPushButton("実行")
        self.rdbi_button.clicked.connect(self._on_rdbi)
        row.addWidget(self.rdbi_button)
        row.addStretch()
        return box

    def _build_session_group(self) -> QGroupBox:
        box = QGroupBox("0x10  DiagnosticSessionControl")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("Session:"))
        self.session_combo = QComboBox()
        for label, _ in SESSION_TYPES:
            self.session_combo.addItem(label)
        row.addWidget(self.session_combo)
        self.session_button = QPushButton("実行")
        self.session_button.clicked.connect(self._on_session)
        row.addWidget(self.session_button)
        row.addStretch()
        return box

    def _build_tp_group(self) -> QGroupBox:
        box = QGroupBox("0x3E  TesterPresent")
        row = QHBoxLayout(box)
        self.tp_suppress_check = QCheckBox("suppress response")
        row.addWidget(self.tp_suppress_check)
        self.tp_button = QPushButton("実行")
        self.tp_button.clicked.connect(self._on_tp)
        row.addWidget(self.tp_button)
        row.addStretch()
        return box

    def _build_result_group(self) -> QGroupBox:
        box = QGroupBox("結果")
        vbox = QVBoxLayout(box)
        self.clear_button = QPushButton("クリア")
        self.clear_button.setFixedWidth(80)
        self.clear_button.clicked.connect(self._on_clear)
        vbox.addWidget(self.clear_button, alignment=Qt.AlignRight)
        self.result_view = QPlainTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setFont(QFont("Courier", 10))
        self.result_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_view.setMinimumHeight(160)
        vbox.addWidget(self.result_view)
        return box

    # ------------------------------------------------------------------ #
    # 接続状態管理
    # ------------------------------------------------------------------ #
    def _set_connected(self, connected: bool):
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.ip_input.setEnabled(not connected)
        self.port_input.setEnabled(not connected)
        for btn in (self.rdbi_button, self.session_button, self.tp_button):
            btn.setEnabled(connected)
        if connected:
            self.status_label.setText("● 接続中")
            self.status_label.setStyleSheet("color: green")
        else:
            self.status_label.setText("● 未接続")
            self.status_label.setStyleSheet("color: gray")

    # ------------------------------------------------------------------ #
    # イベントハンドラ
    # ------------------------------------------------------------------ #
    def _on_connect(self):
        host = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            self._append_result("[ERROR] ポート番号が不正です")
            return
        try:
            self._protocol = DoIPProtocol(host=host, port=port)
            self._protocol.connect()
            self._service = DiagnosticService(protocol=self._protocol)
            self._set_connected(True)
            self._append_result(f"[INFO] {host}:{port} に接続しました")
        except Exception as e:
            self._append_result(f"[ERROR] 接続失敗: {e}")

    def _on_disconnect(self):
        if self._protocol:
            self._protocol.disconnect()
            self._protocol = None
            self._service = None
        self._set_connected(False)
        self._append_result("[INFO] 切断しました")

    def _on_rdbi(self):
        did_str = self.did_input.text().strip()
        try:
            did = int(did_str, 16)
        except ValueError:
            self._append_result(f"[ERROR] DIDの形式が不正です: {did_str}")
            return
        self._run_in_thread(self._exec_rdbi, did)

    def _on_session(self):
        _, session_type = SESSION_TYPES[self.session_combo.currentIndex()]
        self._run_in_thread(self._exec_session, session_type)

    def _on_tp(self):
        self._run_in_thread(self._exec_tp, self.tp_suppress_check.isChecked())

    def _on_clear(self):
        self.result_view.clear()

    # ------------------------------------------------------------------ #
    # UDS実行（DiagnosticServiceに委譲）
    # ------------------------------------------------------------------ #
    def _exec_rdbi(self, did: int) -> str:
        result = self._service.read_data_by_identifier(did=did)
        if result.success:
            return f"[OK]  DID={hex(did)}  Data={result.data.hex(' ').upper()}"
        return (f"[NRC] DID={hex(did)}  "
                f"NRC={hex(result.nrc_code)}  ({result.nrc_message})")

    def _exec_session(self, session_type: int) -> str:
        result = self._service.change_session(session_type=session_type)
        if result.success:
            return f"[OK]  Session={hex(result.session_type)}"
        return (f"[NRC] Session={hex(session_type)}  "
                f"NRC={hex(result.nrc_code)}  ({result.nrc_message})")

    def _exec_tp(self, suppress: bool) -> str:
        result = self._service.tester_present(suppress_response=suppress)
        if result.success:
            return f"[OK]  TesterPresent" + (" (suppressed)" if suppress else "")
        return (f"[NRC] TesterPresent  "
                f"NRC={hex(result.nrc_code)}  ({result.nrc_message})")

    # ------------------------------------------------------------------ #
    # スレッド実行
    # ------------------------------------------------------------------ #
    def _run_in_thread(self, fn, *args):
        self._set_sid_buttons_enabled(False)
        self._thread = QThread()
        self._worker = _Worker(fn, *args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_thread_finished)
        self._worker.error.connect(self._on_thread_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_done)
        self._thread.start()

    def _on_thread_finished(self, message: str):
        self._append_result(message)

    def _on_thread_error(self, message: str):
        self._append_result(f"[ERROR] {message}")

    def _on_thread_done(self):
        self._set_sid_buttons_enabled(True)
        self.sid_finished.emit()   # テスト用シグナル

    def _set_sid_buttons_enabled(self, enabled: bool):
        for btn in (self.rdbi_button, self.session_button, self.tp_button):
            btn.setEnabled(enabled)

    # ------------------------------------------------------------------ #
    # 結果表示
    # ------------------------------------------------------------------ #
    def _append_result(self, text: str):
        self.result_view.appendPlainText(text)
