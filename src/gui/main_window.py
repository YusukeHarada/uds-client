"""
GUIメインウィンドウ (PySide6)

設計原則:
- DiagnosticServiceのみに依存し、UDS/プロトコル層には直接触れない
- UIロジック（表示・入力）のみを担当する
- UDS通信はQThreadで実行してGUIスレッドをブロックしない
- sid_finished シグナルでテストからスレッド完了を待機できる
- ログ出力はDiagnosticServiceに委ねる（ログファイルパス/レベルをGUIで指定）
"""
from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QPlainTextEdit, QSizePolicy,
    QFileDialog,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from src.application.diagnostic_service import DiagnosticService
from src.protocol.doip import DoIPProtocol
from src.protocol.protocol_base import ProtocolBase

SESSION_TYPES = [
    ("0x01  Default Session",             0x01),
    ("0x02  Programming Session",         0x02),
    ("0x03  Extended Diagnostic Session", 0x03),
]

RESET_TYPES = [
    ("0x01  Hard Reset", 0x01),
    ("0x03  Soft Reset", 0x03),
]

DTC_SUBFUNCTIONS = [
    ("0x02  reportDTCByStatusMask", 0x02),
    ("0x0A  reportSupportedDTC",    0x0A),
]

RC_SUBFUNCTIONS = [
    ("0x01  startRoutine",         0x01),
    ("0x02  stopRoutine",          0x02),
    ("0x03  requestRoutineResults",0x03),
]

LOG_LEVELS = ["DEBUG", "INFO", "WARNING"]


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
    sid_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UDS診断ツール")
        self.setMinimumWidth(620)

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
        layout.setSpacing(6)
        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_log_group())
        layout.addWidget(self._build_rdbi_group())
        layout.addWidget(self._build_wdbi_group())
        layout.addWidget(self._build_session_group())
        layout.addWidget(self._build_tp_group())
        layout.addWidget(self._build_reset_group())
        layout.addWidget(self._build_clear_dtc_group())
        layout.addWidget(self._build_read_dtc_group())
        layout.addWidget(self._build_routine_group())
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

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("ログ設定")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("ログファイル:"))
        self.log_path_input = QLineEdit("uds_log.json")
        row.addWidget(self.log_path_input)
        self.log_browse_button = QPushButton("参照")
        self.log_browse_button.setFixedWidth(60)
        self.log_browse_button.clicked.connect(self._on_log_browse)
        row.addWidget(self.log_browse_button)
        row.addWidget(QLabel("レベル:"))
        self.log_level_combo = QComboBox()
        for level in LOG_LEVELS:
            self.log_level_combo.addItem(level)
        self.log_level_combo.setCurrentText("INFO")
        row.addWidget(self.log_level_combo)
        self.log_enable_check = QCheckBox("ログ出力")
        self.log_enable_check.setChecked(True)
        row.addWidget(self.log_enable_check)
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

    def _build_wdbi_group(self) -> QGroupBox:
        box = QGroupBox("0x2E  WriteDataByIdentifier")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("DID (hex):"))
        self.wdbi_did_input = QLineEdit("F190")
        self.wdbi_did_input.setFixedWidth(80)
        row.addWidget(self.wdbi_did_input)
        row.addWidget(QLabel("Data (hex):"))
        self.wdbi_data_input = QLineEdit()
        self.wdbi_data_input.setPlaceholderText("例: 53 49 4D 56 49 4E")
        row.addWidget(self.wdbi_data_input)
        self.wdbi_button = QPushButton("実行")
        self.wdbi_button.clicked.connect(self._on_wdbi)
        row.addWidget(self.wdbi_button)
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

    def _build_reset_group(self) -> QGroupBox:
        box = QGroupBox("0x11  ECUReset")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("Type:"))
        self.reset_combo = QComboBox()
        for label, _ in RESET_TYPES:
            self.reset_combo.addItem(label)
        row.addWidget(self.reset_combo)
        self.reset_button = QPushButton("実行")
        self.reset_button.clicked.connect(self._on_reset)
        row.addWidget(self.reset_button)
        row.addStretch()
        return box

    def _build_clear_dtc_group(self) -> QGroupBox:
        box = QGroupBox("0x14  ClearDiagnosticInformation")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("GroupOfDTC (hex):"))
        self.clear_dtc_input = QLineEdit("FFFFFF")
        self.clear_dtc_input.setFixedWidth(80)
        self.clear_dtc_input.setToolTip("FFFFFF = 全DTC消去")
        row.addWidget(self.clear_dtc_input)
        self.clear_dtc_button = QPushButton("実行")
        self.clear_dtc_button.clicked.connect(self._on_clear_dtc)
        row.addWidget(self.clear_dtc_button)
        row.addStretch()
        return box

    def _build_read_dtc_group(self) -> QGroupBox:
        box = QGroupBox("0x19  ReadDTCInformation")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("SubFunction:"))
        self.dtc_subfn_combo = QComboBox()
        for label, _ in DTC_SUBFUNCTIONS:
            self.dtc_subfn_combo.addItem(label)
        row.addWidget(self.dtc_subfn_combo)
        row.addWidget(QLabel("StatusMask (hex):"))
        self.dtc_mask_input = QLineEdit("FF")
        self.dtc_mask_input.setFixedWidth(50)
        row.addWidget(self.dtc_mask_input)
        self.read_dtc_button = QPushButton("実行")
        self.read_dtc_button.clicked.connect(self._on_read_dtc)
        row.addWidget(self.read_dtc_button)
        row.addStretch()
        return box

    def _build_routine_group(self) -> QGroupBox:
        box = QGroupBox("0x31  RoutineControl")
        row = QHBoxLayout(box)
        row.addWidget(QLabel("SubFunction:"))
        self.rc_subfn_combo = QComboBox()
        for label, _ in RC_SUBFUNCTIONS:
            self.rc_subfn_combo.addItem(label)
        row.addWidget(self.rc_subfn_combo)
        row.addWidget(QLabel("RoutineID (hex):"))
        self.rc_id_input = QLineEdit("0201")
        self.rc_id_input.setFixedWidth(60)
        row.addWidget(self.rc_id_input)
        self.rc_button = QPushButton("実行")
        self.rc_button.clicked.connect(self._on_routine)
        row.addWidget(self.rc_button)
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
        self.log_path_input.setEnabled(not connected)
        self.log_browse_button.setEnabled(not connected)
        self.log_level_combo.setEnabled(not connected)
        self.log_enable_check.setEnabled(not connected)
        for btn in self._sid_buttons():
            btn.setEnabled(connected)
        if connected:
            self.status_label.setText("● 接続中")
            self.status_label.setStyleSheet("color: green")
        else:
            self.status_label.setText("● 未接続")
            self.status_label.setStyleSheet("color: gray")

    def _sid_buttons(self) -> list:
        return [
            self.rdbi_button, self.wdbi_button, self.session_button,
            self.tp_button, self.reset_button, self.clear_dtc_button,
            self.read_dtc_button, self.rc_button,
        ]

    # ------------------------------------------------------------------ #
    # イベントハンドラ
    # ------------------------------------------------------------------ #
    def _on_log_browse(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "ログファイルを選択", "uds_log.json", "JSON Lines (*.json)"
        )
        if path:
            self.log_path_input.setText(path)

    def _on_connect(self):
        host = self.ip_input.text().strip()
        try:
            port = int(self.port_input.text().strip())
        except ValueError:
            self._append_result("[ERROR] ポート番号が不正です")
            return

        log_path  = self.log_path_input.text().strip() if self.log_enable_check.isChecked() else None
        log_level = self.log_level_combo.currentText()

        try:
            self._protocol = DoIPProtocol(host=host, port=port)
            self._protocol.connect()
            self._service = DiagnosticService(
                protocol=self._protocol,
                log_path=log_path,
                log_level=log_level,
            )
            self._set_connected(True)
            log_info = f"  ログ: {log_path} ({log_level})" if log_path else "  ログ: 無効"
            self._append_result(f"[INFO] {host}:{port} に接続しました{log_info}")
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
        try:
            did = int(self.did_input.text().strip(), 16)
        except ValueError:
            self._append_result(f"[ERROR] DIDの形式が不正です")
            return
        self._run_in_thread(self._exec_rdbi, did)

    def _on_wdbi(self):
        try:
            did = int(self.wdbi_did_input.text().strip(), 16)
        except ValueError:
            self._append_result("[ERROR] DIDの形式が不正です")
            return
        try:
            data = bytes.fromhex(self.wdbi_data_input.text().replace(" ", ""))
        except ValueError:
            self._append_result("[ERROR] Dataの形式が不正です（hex文字列で入力）")
            return
        self._run_in_thread(self._exec_wdbi, did, data)

    def _on_session(self):
        _, session_type = SESSION_TYPES[self.session_combo.currentIndex()]
        self._run_in_thread(self._exec_session, session_type)

    def _on_tp(self):
        self._run_in_thread(self._exec_tp, self.tp_suppress_check.isChecked())

    def _on_reset(self):
        _, reset_type = RESET_TYPES[self.reset_combo.currentIndex()]
        self._run_in_thread(self._exec_reset, reset_type)

    def _on_clear_dtc(self):
        try:
            group = int(self.clear_dtc_input.text().strip(), 16)
        except ValueError:
            self._append_result("[ERROR] GroupOfDTCの形式が不正です")
            return
        self._run_in_thread(self._exec_clear_dtc, group)

    def _on_read_dtc(self):
        _, subfn = DTC_SUBFUNCTIONS[self.dtc_subfn_combo.currentIndex()]
        try:
            mask = int(self.dtc_mask_input.text().strip(), 16)
        except ValueError:
            self._append_result("[ERROR] StatusMaskの形式が不正です")
            return
        self._run_in_thread(self._exec_read_dtc, subfn, mask)

    def _on_routine(self):
        _, subfn = RC_SUBFUNCTIONS[self.rc_subfn_combo.currentIndex()]
        try:
            routine_id = int(self.rc_id_input.text().strip(), 16)
        except ValueError:
            self._append_result("[ERROR] RoutineIDの形式が不正です")
            return
        self._run_in_thread(self._exec_routine, subfn, routine_id)

    def _on_clear(self):
        self.result_view.clear()

    # ------------------------------------------------------------------ #
    # UDS実行（DiagnosticServiceに委譲）
    # ------------------------------------------------------------------ #
    def _exec_rdbi(self, did: int) -> str:
        result = self._service.read_data_by_identifier(did=did)
        if result.success:
            return f"[OK]  DID={hex(did)}  Data={result.data.hex(' ').upper()}"
        return f"[NRC] DID={hex(did)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_wdbi(self, did: int, data: bytes) -> str:
        result = self._service.write_data_by_identifier(did=did, data=data)
        if result.success:
            return f"[OK]  WriteDataByIdentifier DID={hex(did)}"
        return f"[NRC] DID={hex(did)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_session(self, session_type: int) -> str:
        result = self._service.change_session(session_type=session_type)
        if result.success:
            return f"[OK]  Session={hex(result.session_type)}"
        return f"[NRC] Session={hex(session_type)}  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_tp(self, suppress: bool) -> str:
        result = self._service.tester_present(suppress_response=suppress)
        if result.success:
            return f"[OK]  TesterPresent" + (" (suppressed)" if suppress else "")
        return f"[NRC] TesterPresent  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_reset(self, reset_type: int) -> str:
        result = self._service.ecu_reset(reset_type=reset_type)
        if result.success:
            return f"[OK]  ECUReset type={hex(reset_type)}"
        return f"[NRC] ECUReset  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_clear_dtc(self, group: int) -> str:
        result = self._service.clear_dtc(group_of_dtc=group)
        if result.success:
            return f"[OK]  ClearDTC group={hex(group)}"
        return f"[NRC] ClearDTC  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

    def _exec_read_dtc(self, subfn: int, mask: int) -> str:
        result = self._service.read_dtc(subfunction=subfn, status_mask=mask)
        if not result.success:
            return f"[NRC] ReadDTC  NRC={hex(result.nrc_code)}  ({result.nrc_message})"
        if not result.dtc_records:
            return f"[OK]  ReadDTC subfn={hex(subfn)}  DTCなし"
        lines = [f"[OK]  ReadDTC subfn={hex(subfn)}  件数={len(result.dtc_records)}"]
        for rec in result.dtc_records:
            lines.append(f"      {rec}")
        return "\n".join(lines)

    def _exec_routine(self, subfn: int, routine_id: int) -> str:
        result = self._service.routine_control(subfunction=subfn, routine_id=routine_id)
        if result.success:
            status = result.routine_status_record.hex(' ').upper() if result.routine_status_record else "-"
            return f"[OK]  RoutineControl subfn={hex(subfn)}  ID={hex(routine_id)}  Status={status}"
        return f"[NRC] RoutineControl  NRC={hex(result.nrc_code)}  ({result.nrc_message})"

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
        self.sid_finished.emit()

    def _set_sid_buttons_enabled(self, enabled: bool):
        for btn in self._sid_buttons():
            btn.setEnabled(enabled)

    # ------------------------------------------------------------------ #
    # 結果表示
    # ------------------------------------------------------------------ #
    def _append_result(self, text: str):
        self.result_view.appendPlainText(text)
