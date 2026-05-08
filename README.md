# UDS診断ツール (DoIP対応)

TDD + ATDDで段階的に開発するUDS診断ツールです。

## 対応プロトコル
- DoIP (ISO 13400-2)

## 対応UDSサービス
- 0x10 DiagnosticSessionControl
- 0x22 ReadDataByIdentifier
- 0x3E TesterPresent

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

```bash
python main.py --ip 192.168.0.10 --did F190 --log DEBUG --logfile uds_log.json
```

### オプション

| オプション | 説明 | デフォルト |
|---|---|---|
| `--ip` | ECU IPアドレス | 必須 |
| `--port` | DoIPポート | 13400 |
| `--did` | DID (hex) 例: F190 | 必須 |
| `--log` | ログレベル DEBUG/INFO/WARNING | INFO |
| `--logfile` | ログ出力ファイル | uds_log.json |

## ECUシミュレータ（実ECU不要でのローカル確認）

```bash
# Terminal 1: シミュレータ起動
python ecu_simulator.py

# Terminal 2: CLIで接続
python main.py --ip 127.0.0.1 --did F190 --log DEBUG
python main.py --ip 127.0.0.1 --did 9999 --log DEBUG   # NRC確認
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

## テスト実行

```bash
# 全テスト実行
pytest tests/ -v

# ユニットテストのみ
pytest tests/unit/ -v

# ATDDのみ
pytest tests/atdd/ -v

# 結合テスト（シミュレータ自動起動）
pytest tests/integration/ -v
```

## アーキテクチャ

```
[CLI (click)]
    │
[DiagnosticService]   ← CLI/GUIが共有するアプリケーションロジック
    │
[ProtocolBase]        ← Strategyパターン（DoIP/UDSonCAN切替可能）
    │
[DoIPProtocol]        ← doipclientライブラリをラップ
```

## ディレクトリ構成

```
uds_tool/
├── main.py                              # CLIエントリポイント
├── ecu_simulator.py                     # ローカルテスト用ECUシミュレータ
├── requirements.txt
├── pytest.ini
├── src/
│   ├── application/
│   │   └── diagnostic_service.py        # CLI/GUI共有ロジック
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
    ├── atdd/
    │   ├── test_step1_read_did.py
    │   └── test_step2_session.py
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

## 開発ステップ

- [x] Step1: CLI + DoIP + ReadDataByIdentifier (0x22)
- [x] Step2: DiagnosticSessionControl (0x10) + TesterPresent (0x3E)
- [ ] Step3: PyQt GUI追加
- [ ] Step4: DoIP通信強化（再接続・タイムアウト）
- [ ] Step5: 追加SID (0x11, 0x14, 0x19, 0x2E, 0x31)
- [ ] Step6: SecurityAccess (0x27)
- [ ] Step7: UDSonCAN対応 (ISO-TP + python-can)

## ログ出力形式 (JSON Lines)

```json
{"direction": "TX", "sid": "0x10", "raw_hex": "10 03", "event": "uds_tx", "timestamp": "2026-05-09T..."}
{"direction": "RX", "sid": "0x10", "raw_hex": "50 03 ...", "event": "uds_rx", "timestamp": "2026-05-09T..."}
{"direction": "TX", "sid": "0x22", "raw_hex": "22 F1 90", "event": "uds_tx", "timestamp": "2026-05-09T..."}
{"direction": "RX", "sid": "0x22", "raw_hex": "62 F1 90 ...", "event": "uds_rx", "timestamp": "2026-05-09T..."}
```

## SID別テスト実行コマンド

### SID 0x22 ReadDataByIdentifier

```bash
# ユニットテスト
pytest tests/unit/test_read_data_by_identifier.py -v

# ATDDテスト
pytest tests/atdd/test_step1_read_did.py -v

# 結合テスト
pytest tests/integration/test_integration_doip.py -v
```

### SID 0x10 DiagnosticSessionControl

```bash
# ユニットテスト
pytest tests/unit/test_diagnostic_session_control.py -v

# ATDDテスト
pytest tests/atdd/test_step2_session.py -v -k "session"

# 結合テスト
pytest tests/integration/test_integration_step2.py::TestIntegrationSessionControl -v
```

### SID 0x3E TesterPresent

```bash
# ユニットテスト
pytest tests/unit/test_tester_present.py -v

# ATDDテスト
pytest tests/atdd/test_step2_session.py -v -k "tester_present"

# 結合テスト
pytest tests/integration/test_integration_step2.py::TestIntegrationTesterPresent -v
```

### シナリオ連結テスト（セッション遷移 → RDBI）

```bash
pytest tests/atdd/test_step2_session.py::TestStep2AcceptanceSession::test_session_then_rdbi -v
pytest tests/integration/test_integration_step2.py::TestIntegrationSessionThenRdbi -v
```

### その他

```bash
# キーワードでまとめて絞り込む
pytest tests/ -v -k "session"
pytest tests/ -v -k "tester"
pytest tests/ -v -k "rdbi or read_data"

# カバレッジをSIDファイル単位で確認
pytest tests/ --cov=src/uds/read_data_by_identifier --cov-report=term-missing
pytest tests/ --cov=src/uds/diagnostic_session_control --cov-report=term-missing
pytest tests/ --cov=src/uds/tester_present --cov-report=term-missing
```

## ECUシミュレータを使った手動テスト手順

### 1. シミュレータ起動

```bash
# ターミナル1
python ecu_simulator.py
```

起動すると以下が表示されます。

```
[SIM] Listening on 127.0.0.1:13400  logical_addr=0x1000
[SIM] DIDs: 0xf190, 0xf18c, 0xf186
[SIM] Sessions: 0x1, 0x2, 0x3
[SIM] Ctrl+C to stop
```

---

### 2. CLIから接続してSIDを実行

別ターミナルで以下を実行します。

```bash
# ターミナル2
```

#### SID 0x22 ReadDataByIdentifier

```bash
# VIN読み取り（正常応答）
python main.py --ip 127.0.0.1 --did F190 --log DEBUG
# → [OK]  DID=0xf190  Data=53 49 4D 56 49 4E 30 30 30 30 30 30 30 30 30 31

# ECU Serial Number
python main.py --ip 127.0.0.1 --did F18C --log DEBUG
# → [OK]  DID=0xf18c  Data=53 4E 2D 45 43 55 2D 30 30 34 32

# 存在しないDID（NRC確認）
python main.py --ip 127.0.0.1 --did 1234 --log DEBUG
# → [NRC] DID=0x1234  NRC=0x31  (Request Out Of Range)
```

---

### 3. シミュレータ側のログ確認

シミュレータのターミナルには通信内容がリアルタイムで表示されます。

```
[SIM] Connected: ('127.0.0.1', 52001)
[SIM] RX type=0x5 payload=0E 00 00 00 00 00 00     ← RoutingActivationRequest
[SIM] TX RoutingActivationResponse OK client=0xe00
[SIM] RX type=0x8001 payload=0E 00 10 00 22 F1 90  ← ReadDataByIdentifier
[SIM] TX DiagnosticResponse: 62 F1 90 53 49 4D ...
[SIM] Disconnected: ('127.0.0.1', 52001)
```

---

### 4. ログファイルの確認

```bash
# 通信ログをJSON Lines形式で確認
cat uds_log.json

# jqで整形表示（jqインストール済みの場合）
cat uds_log.json | jq .

# TXのみ抽出
cat uds_log.json | jq 'select(.direction=="TX")'

# NRCが発生したエントリのみ抽出
cat uds_log.json | jq 'select(.nrc != null)'
```

---

### 5. pytestによる自動テスト（シミュレータ自動起動）

手動でシミュレータを起動する必要はありません。  
pytest実行時にシミュレータがテスト内部で自動起動・停止します。

```bash
# 全テスト（シミュレータ自動起動）
pytest tests/ -v

# 結合テストのみ
pytest tests/integration/ -v

# シミュレータのログも表示したい場合
pytest tests/integration/ -v -s
```

---

### 6. シミュレータのポート変更

デフォルト（13400）が使用中の場合はポートを変更できます。

```bash
# シミュレータを別ポートで起動
python ecu_simulator.py --port 13401

# CLIも同じポートを指定
python main.py --ip 127.0.0.1 --port 13401 --did F190
```
