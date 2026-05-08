# UDS診断ツール (DoIP対応)

TDD + ATDDで段階的に開発するUDS診断ツールです。

## 対応プロトコル
- DoIP (ISO 13400-2) ※ Step1

## 対応UDSサービス
- 0x22 ReadDataByIdentifier ※ Step1

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

## テスト実行

```bash
pytest tests/ -v
```

## アーキテクチャ

```
[CLI (click)]
    │
[DiagnosticService]   ← CLI/GUIが共有するアプリケーションロジック
    │
[ProtocolBase]        ← Strategyパターン（DoIP/J1939切替可能）
    │
[DoIPProtocol]        ← doipclientライブラリをラップ
```

## ディレクトリ構成

```
uds_tool/
├── src/
│   ├── application/
│   │   └── diagnostic_service.py
│   ├── uds/
│   │   ├── service_base.py
│   │   ├── read_data_by_identifier.py
│   │   └── nrc.py
│   ├── protocol/
│   │   ├── protocol_base.py
│   │   └── doip.py
│   └── logger/
│       └── uds_logger.py
├── tests/
│   ├── atdd/
│   │   └── test_step1_read_did.py
│   └── unit/
│       ├── test_nrc.py
│       ├── test_read_data_by_identifier.py
│       ├── test_uds_logger.py
│       └── test_service_base.py
├── main.py
├── requirements.txt
├── pytest.ini
└── README.md
```

## 開発ステップ

- [x] Step1: CLI + DoIP + ReadDataByIdentifier (0x22)
- [ ] Step2: Session制御 (0x10) + TesterPresent (0x3E)
- [ ] Step3: PyQt GUI追加
- [ ] Step4: DoIP通信強化（再接続・タイムアウト）
- [ ] Step5: 追加SID (0x11, 0x14, 0x19, 0x2E, 0x31)
- [ ] Step6: SecurityAccess (0x27)
- [ ] Step7: J1939対応
