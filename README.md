# UDS診断ツール (DoIP対応)

TDD + ATDDで段階的に開発するUDS診断ツールです。

## 対応プロトコル

- DoIP (ISO 13400-2)

## 対応UDSサービス

| SID | サービス名 |
|---|---|
| 0x10 | DiagnosticSessionControl |
| 0x22 | ReadDataByIdentifier |
| 0x3E | TesterPresent |

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

### CLI

```bash
python main.py --ip 192.168.0.10 --did F190 --log DEBUG
```

| オプション | 説明 | デフォルト |
|---|---|---|
| `--ip` | ECU IPアドレス | 必須 |
| `--port` | DoIPポート | 13400 |
| `--did` | DID (hex) 例: F190 | 必須 |
| `--log` | ログレベル DEBUG/INFO/WARNING | INFO |
| `--logfile` | ログ出力ファイル | uds_log.json |

---

## ECUシミュレータ（実ECU不要）

実ECUなしでローカル確認ができます。

### 手動確認（ターミナル2つ）

```bash
# ターミナル1: シミュレータ起動
python ecu_simulator.py
```

```bash
# ターミナル2: GUI または CLI で接続
python gui_main.py

python main.py --ip 127.0.0.1 --did F190 --log DEBUG
# → [OK]  DID=0xf190  Data=53 49 4D 56 49 4E ...

python main.py --ip 127.0.0.1 --did 1234 --log DEBUG
# → [NRC] DID=0x1234  NRC=0x31  (Request Out Of Range)
```

### シミュレータ対応DID

| DID | 内容 |
|---|---|
| F190 | VIN |
| F18C | ECU Serial Number |
| F186 | Active Diagnostic Session |

### シミュレータ対応セッション

| セッションタイプ | 内容 |
|---|---|
| 0x01 | Default Session |
| 0x02 | Programming Session |
| 0x03 | Extended Diagnostic Session |

### ポート変更

```bash
python ecu_simulator.py --port 13401
python main.py --ip 127.0.0.1 --port 13401 --did F190
```

---

## テスト実行

```bash
# 全テスト（シミュレータ自動起動）
pytest tests/ -v

# 種別ごと
pytest tests/unit/ -v
pytest tests/atdd/ -v
pytest tests/integration/ -v -s   # -s でシミュレータログも表示
```

### SID別テスト

```bash
# SID 0x22 ReadDataByIdentifier
pytest tests/unit/test_read_data_by_identifier.py -v
pytest tests/atdd/test_step1_read_did.py -v
pytest tests/integration/test_integration_doip.py -v

# SID 0x10 DiagnosticSessionControl
pytest tests/unit/test_diagnostic_session_control.py -v
pytest tests/atdd/test_step2_session.py -v -k "session"
pytest tests/integration/test_integration_step2.py::TestIntegrationSessionControl -v

# SID 0x3E TesterPresent
pytest tests/unit/test_tester_present.py -v
pytest tests/atdd/test_step2_session.py -v -k "tester_present"
pytest tests/integration/test_integration_step2.py::TestIntegrationTesterPresent -v

# GUI
pytest tests/atdd/test_step3_gui.py -v

# キーワード絞り込み
pytest tests/ -v -k "session"
pytest tests/ -v -k "rdbi or read_data"

# カバレッジをファイル単位で確認
pytest tests/ --cov=src/uds/read_data_by_identifier --cov-report=term-missing
```

---

## ログ出力形式 (JSON Lines)

```bash
cat uds_log.json | jq .          # 整形表示
cat uds_log.json | jq 'select(.direction=="TX")'       # TXのみ
cat uds_log.json | jq 'select(.nrc != null)'           # NRC発生分のみ
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
├── gui_main.py                          # GUIエントリポイント
├── main.py                              # CLIエントリポイント
├── ecu_simulator.py                     # ローカルテスト用ECUシミュレータ
├── requirements.txt
├── pytest.ini
├── src/
│   ├── application/
│   │   └── diagnostic_service.py        # GUI/CLI共有ロジック
│   ├── gui/
│   │   └── main_window.py               # PySide6メインウィンドウ
│   ├── uds/
│   │   ├── service_base.py              # 共通データモデル (pydantic)
│   │   ├── nrc.py                       # NRCコード定義・変換
│   │   ├── read_data_by_identifier.py   # SID 0x22
│   │   ├── diagnostic_session_control.py # SID 0x10
│   │   └── tester_present.py            # SID 0x3E
│   ├── protocol/
│   │   ├── protocol_base.py             # Strategyインターフェース
│   │   └── doip.py                      # DoIPプロトコル実装
│   └── logger/
│       └── uds_logger.py                # JSON Lines形式ログ出力
└── tests/
    ├── conftest.py                      # テスト共通設定（ヘッドレスGUI）
    ├── atdd/
    │   ├── test_step1_read_did.py
    │   ├── test_step2_session.py
    │   └── test_step3_gui.py
    ├── unit/
    │   ├── test_nrc.py
    │   ├── test_service_base.py
    │   ├── test_read_data_by_identifier.py
    │   ├── test_diagnostic_session_control.py
    │   ├── test_tester_present.py
    │   └── test_uds_logger.py
    └── integration/
        ├── test_integration_doip.py     # Step1結合テスト
        └── test_integration_step2.py    # Step2結合テスト
```

---

## 開発ステップ

- [x] Step1: CLI + DoIP + ReadDataByIdentifier (0x22)
- [x] Step2: DiagnosticSessionControl (0x10) + TesterPresent (0x3E)
- [x] Step3: PySide6 GUI
- [ ] Step4: DoIP通信強化（再接続・タイムアウト）
- [ ] Step5: 追加SID (0x11, 0x14, 0x19, 0x2E, 0x31)
- [ ] Step6: SecurityAccess (0x27)
- [ ] Step7: UDSonCAN対応 (ISO-TP + python-can)
