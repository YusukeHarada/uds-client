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
