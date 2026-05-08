"""
UDS通信ログ出力。

structlogを使用してJSON形式でファイルに記録する。
各エントリには timestamp / direction / sid / raw_hex が含まれ、
NRCがある場合は nrc / nrc_message も付与される。

structlogの利点：
- タイムスタンプ・ログレベルの自動付与
- コンテキストのキーワード引数で自然に構造化ログを書ける
- 出力先の変更（ファイル/stdout）が設定1か所で済む
"""
import structlog
from typing import Optional
from src.uds.nrc import NRCDecoder


def _configure_structlog(log_path: str, level: str) -> structlog.BoundLogger:
    """
    structlogをピュアJSON/ファイル出力で設定して返す。

    stdlib.LoggerFactoryを使うと標準loggingのフォーマッタが
    "INFO:uds:{...}" というプレフィックスを付加してしまう。
    PrintLoggerFactoryでファイルに直接書き込むことでピュアJSONを実現する。
    """
    log_file = open(log_path, "a", encoding="utf-8")  # noqa: WPS515

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(log_file),
    )

    return structlog.get_logger()


class UDSLogger:
    def __init__(self, path: str, level: str = "INFO"):
        self._logger = _configure_structlog(path, level)

    def log_tx(self, sid: int, raw: bytes) -> None:
        """送信フレームをログに記録する。"""
        self._logger.info(
            "uds_tx",
            direction="TX",
            sid=hex(sid),
            raw_hex=raw.hex(" ").upper(),
        )

    def log_rx(self, sid: int, raw: bytes, nrc: Optional[int] = None) -> None:
        """受信フレームをログに記録する。NRCがある場合は人間可読メッセージも付与する。"""
        kwargs: dict = dict(
            direction="RX",
            sid=hex(sid),
            raw_hex=raw.hex(" ").upper(),
        )
        if nrc is not None:
            kwargs["nrc"] = hex(nrc)
            kwargs["nrc_message"] = NRCDecoder.decode(nrc)

        self._logger.info("uds_rx", **kwargs)
