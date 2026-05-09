# UDS診断ツール (DoIP対応)

TDD + ATDDで段階的に開発するUDS診断ツールです。

## 対応プロトコル

- DoIP (ISO 13400-2)

## 対応UDSサービス

| SID | サービス名 | 備考 |
|---|---|---|
| 0x10 | DiagnosticSessionControl | Default / Programming / Extended |
| 0x11 | ECUReset | Hard Reset / Soft Reset |
| 0x14 | ClearDiagnosticInformation | 全DTC消去 / グループ指定 |
| 0x19 | ReadDTCInformation | 0x02 reportDTCByStatusMask / 0x0A reportSupportedDTC |
| 0x22 | ReadDataByIdentifier | |
| 0x2E | WriteDataByIdentifier | |
| 0x31 | RoutineControl | start / stop / requestResults |
| 0x3E | TesterPresent | suppress response対応 |

---

## セットアップ

```bash
pip install -r requirements.txt
```

---

## 起動方法

### GUI

```bash
python gui_main.py
```

接続設定画面でログファイルパスとログレベルを指定できます。ログはJSON Lines形式で出力されます。

### CLI

サブコマンド方式でSIDを指定して実行します。

```bash
# 書式
python main.py --ip <IP> [--port <PORT>] [--log LEVEL] [--logfile FILE] <サブコマンド> [引数]
```

#### 共通オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--ip` | ECU IPアドレス | 必須 |
| `--port` | DoIPポート | 13400 |
| `--log` | ログレベル DEBUG/INFO/WARNING | INFO |
| `--logfile` | ログ出力ファイル | uds_log.json |

#### サブコマンド一覧

```bash
# 0x22 ReadDataByIdentifier
python main.py --ip 192.168.0.10 rdbi F190

# 0x2E WriteDataByIdentifier
python main.py --ip 192.168.0.10 wdbi F190 --data 4E455756494E30303030303030303031

# 0x10 DiagnosticSessionControl
python main.py --ip 192.168.0.10 session 03

# 0x3E TesterPresent
python main.py --ip 192.168.0.10 tester-present
python main.py --ip 192.168.0.10 tester-present --suppress

# 0x11 ECUReset
python main.py --ip 192.168.0.10 reset hard
python main.py --ip 192.168.0.10 reset soft

# 0x14 ClearDiagnosticInformation
python main.py --ip 192.168.0.10 clear-dtc                   # 全DTC消去
python main.py --ip 192.168.0.10 clear-dtc --group 012345    # グループ指定

# 0x19 ReadDTCInformation
python main.py --ip 192.168.0.10 read-dtc --subfn 02 --mask FF
python main.py --ip 192.168.0.10 read-dtc --subfn 0a

# 0x31 RoutineControl
python main.py --ip 192.168.0.10 routine 01 0201   # start
python main.py --ip 192.168.0.10 routine 02 0201   # stop
python main.py --ip 192.168.0.10 routine 03 0201   # requestResults
```

#### ヘルプ

```bash
python main.py --help
python main.py rdbi --help
python main.py read-dtc --help
```

#### 終了コード

| コード | 意味 |
|---|---|
| 0 | 成功 |
| 1 | 接続エラー / 引数エラー |
| 2 | NRC応答（ECUがエラーを返した） |

---

## ECUシミュレータ（実ECU不要）

実ECUなしでローカル確認ができます。

### 手動確認（ターミナル2つ）

```bash
# ターミナル1: シミュレータ起動
python ecu_simulator.py
```

```bash
# ターミナル2: GUIまたはCLIで接続
python gui_main.py

# CLIで確認する場合
python main.py --ip 127.0.0.1 rdbi F190
# → [OK]  DID=0xf190  Data=53 49 4D 56 49 4E ...

python main.py --ip 127.0.0.1 read-dtc --subfn 02
# → [OK]  ReadDTC subfn=0x2  件数=2
#         DTC=0x12345  status=0x8
#         DTC=0xabcd   status=0x9
```

### シミュレータ対応データ

| DID | 内容 | 書き込み |
|---|---|---|
| F190 | VIN | ○ |
| F18C | ECU Serial Number | × |
| F186 | Active Diagnostic Session | × |

| セッションタイプ | 内容 |
|---|---|
| 0x01 | Default Session |
| 0x02 | Programming Session |
| 0x03 | Extended Diagnostic Session |

| リセットタイプ | 内容 |
|---|---|
| 0x01 | Hard Reset |
| 0x03 | Soft Reset |

| RoutineID | 内容 |
|---|---|
| 0x0201 | テスト用ルーティン |
| 0xFF00 | テスト用ルーティン |

ダミーDTCデータ: `0x012345 (status=0x08)` / `0x00ABCD (status=0x09)`

### ポート変更

```bash
python ecu_simulator.py --port 13401
python main.py --ip 127.0.0.1 --port 13401 rdbi F190
```

---

## テスト実行

```bash
# 全テスト（シミュレータ自動起動）
pytest tests/ -v

# 種別ごと
pytest tests/unit/ -v
pytest tests/atdd/ -v
pytest tests/integration/ -v -s    # -s でシミュレータログも表示
```

### SID別テスト

```bash
# 0x10 DiagnosticSessionControl
pytest tests/unit/test_diagnostic_session_control.py -v
pytest tests/atdd/test_step2_session.py -v -k "session"
pytest tests/integration/test_integration_step2.py::TestIntegrationSessionControl -v

# 0x11 ECUReset
pytest tests/unit/test_ecu_reset.py -v
pytest tests/atdd/test_step5_sids.py::TestStep5ECUReset -v
pytest tests/integration/test_integration_step5.py::TestIntegrationECUReset -v

# 0x14 ClearDTC
pytest tests/unit/test_clear_dtc.py -v
pytest tests/atdd/test_step5_sids.py::TestStep5ClearDTC -v
pytest tests/integration/test_integration_step5.py::TestIntegrationClearDTC -v

# 0x19 ReadDTCInformation
pytest tests/unit/test_read_dtc_information.py -v
pytest tests/atdd/test_step5_sids.py::TestStep5ReadDTC -v
pytest tests/integration/test_integration_step5.py::TestIntegrationReadDTC -v

# 0x22 ReadDataByIdentifier
pytest tests/unit/test_read_data_by_identifier.py -v
pytest tests/atdd/test_step1_read_did.py -v
pytest tests/integration/test_integration_doip.py -v

# 0x2E WriteDataByIdentifier
pytest tests/unit/test_write_data_by_identifier.py -v
pytest tests/atdd/test_step5_sids.py::TestStep5WriteDataByIdentifier -v
pytest tests/integration/test_integration_step5.py::TestIntegrationWriteDataByIdentifier -v

# 0x31 RoutineControl
pytest tests/unit/test_routine_control.py -v
pytest tests/atdd/test_step5_sids.py::TestStep5RoutineControl -v
pytest tests/integration/test_integration_step5.py::TestIntegrationRoutineControl -v

# 0x3E TesterPresent
pytest tests/unit/test_tester_present.py -v
pytest tests/atdd/test_step2_session.py -v -k "tester_present"
pytest tests/integration/test_integration_step2.py::TestIntegrationTesterPresent -v

# CLI
pytest tests/unit/test_cli.py -v

# GUI
pytest tests/atdd/test_step3_gui.py -v
```

---

## ログ出力形式 (JSON Lines)

```bash
cat uds_log.json | jq .                              # 整形表示
cat uds_log.json | jq 'select(.direction=="TX")'     # TXのみ
cat uds_log.json | jq 'select(.nrc != null)'         # NRC発生分のみ
```

出力例：

```json
{"direction": "TX", "sid": "0x22", "raw_hex": "22 F1 90", "event": "uds_tx", "timestamp": "2026-05-09T12:00:00Z"}
{"direction": "RX", "sid": "0x22", "raw_hex": "62 F1 90 ...", "event": "uds_rx", "timestamp": "2026-05-09T12:00:00Z"}
{"direction": "RX", "sid": "0x22", "raw_hex": "7F 22 31", "nrc": "0x31", "nrc_message": "Request Out Of Range", "event": "uds_rx", "timestamp": "2026-05-09T12:00:00Z"}
```

---

## アーキテクチャ

```
[GUI (PySide6)]    [CLI (click)]
       │                │
       └────────┬────────┘
                │
     [DiagnosticService]      ← GUI/CLI共有ロジック
                │
         [ProtocolBase]       ← Strategyパターン（DoIP/UDSonCAN切替可能）
                │
         [DoIPProtocol]       ← doipclientライブラリをラップ
```

---

## ディレクトリ構成

```
uds_tool/
├── gui_main.py                              # GUIエントリポイント
├── main.py                                  # CLIエントリポイント（サブコマンド方式）
├── ecu_simulator.py                         # ローカルテスト用ECUシミュレータ
├── requirements.txt
├── pytest.ini
├── src/
│   ├── application/
│   │   └── diagnostic_service.py            # GUI/CLI共有ロジック
│   ├── gui/
│   │   └── main_window.py                   # PySide6メインウィンドウ
│   ├── uds/
│   │   ├── service_base.py                  # 共通データモデル (pydantic)
│   │   ├── nrc.py                           # NRCコード定義・変換
│   │   ├── read_data_by_identifier.py       # SID 0x22
│   │   ├── write_data_by_identifier.py      # SID 0x2E
│   │   ├── diagnostic_session_control.py    # SID 0x10
│   │   ├── tester_present.py                # SID 0x3E
│   │   ├── ecu_reset.py                     # SID 0x11
│   │   ├── clear_dtc.py                     # SID 0x14
│   │   ├── read_dtc_information.py          # SID 0x19
│   │   └── routine_control.py               # SID 0x31
│   ├── protocol/
│   │   ├── protocol_base.py                 # Strategyインターフェース
│   │   └── doip.py                          # DoIPプロトコル実装
│   └── logger/
│       └── uds_logger.py                    # JSON Lines形式ログ出力
└── tests/
    ├── conftest.py                          # テスト共通設定（ヘッドレスGUI）
    ├── atdd/
    │   ├── test_step1_read_did.py
    │   ├── test_step2_session.py
    │   ├── test_step3_gui.py
    │   └── test_step5_sids.py
    ├── unit/
    │   ├── test_cli.py
    │   ├── test_nrc.py
    │   ├── test_service_base.py
    │   ├── test_read_data_by_identifier.py
    │   ├── test_write_data_by_identifier.py
    │   ├── test_diagnostic_session_control.py
    │   ├── test_tester_present.py
    │   ├── test_ecu_reset.py
    │   ├── test_clear_dtc.py
    │   ├── test_read_dtc_information.py
    │   ├── test_routine_control.py
    │   └── test_uds_logger.py
    └── integration/
        ├── test_integration_doip.py         # Step1結合テスト
        ├── test_integration_step2.py        # Step2結合テスト
        └── test_integration_step5.py        # Step5結合テスト
```

---

## 開発ステップ

- [x] Step1: CLI + DoIP + ReadDataByIdentifier (0x22)
- [x] Step2: DiagnosticSessionControl (0x10) + TesterPresent (0x3E)
- [x] Step3: PySide6 GUI（ログ出力対応）
- [ ] Step4: DoIP通信強化（再接続・タイムアウト）
- [x] Step5: 追加SID (0x11, 0x14, 0x19, 0x2E, 0x31)
- [x] CLI: 全SIDをサブコマンドで実行可能
- [ ] Step6: SecurityAccess (0x27)
- [ ] Step7: UDSonCAN対応 (ISO-TP + python-can)
