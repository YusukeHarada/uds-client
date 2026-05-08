"""
DoIPプロトコル実装 (ISO 13400-2)。

doipclientライブラリをProtocolBaseインターフェースでラップする。
外部からはProtocolBaseとして扱われるため差し替え可能性を維持する。
TCP接続管理はdoipclientに委ねる（自前TCPソケット管理を排除）。

doipclient APIメモ:
  DoIPClient(ecu_ip, ecu_logical_address, tcp_port=13400, client_logical_address=0x0E00)
  .send_diagnostic(payload)   : UDSペイロード送信
  .receive_diagnostic()       : UDSペイロード受信
  .close()                    : 切断
"""
from doipclient import DoIPClient
from src.protocol.protocol_base import ProtocolBase

DEFAULT_PORT           = 13400
DEFAULT_SOURCE_ADDRESS = 0x0E00   # Tester (client) logical address
DEFAULT_TARGET_ADDRESS = 0x1000   # ECU logical address


class DoIPProtocol(ProtocolBase):

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        source_address: int = DEFAULT_SOURCE_ADDRESS,
        target_address: int = DEFAULT_TARGET_ADDRESS,
    ):
        self._host = host
        self._port = port
        self._source = source_address
        self._target = target_address
        self._client: DoIPClient | None = None

    def connect(self) -> None:
        """DoIPクライアントを生成してECUに接続する。"""
        self._client = DoIPClient(
            ecu_ip_address=self._host,
            ecu_logical_address=self._target,
            tcp_port=self._port,
            client_logical_address=self._source,
        )
        # DoIPClientはコンストラクタ内でTCP接続まで行う

    def disconnect(self) -> None:
        """接続を閉じてクライアントを破棄する。"""
        if self._client:
            self._client.close()
            self._client = None

    def send(self, uds_payload: bytes, **kwargs) -> None:
        """UDSペイロードをDoIP DiagnosticMessageとして送信する。"""
        if not self._client:
            raise RuntimeError("Not connected. Call connect() first.")
        self._client.send_diagnostic(uds_payload)

    def receive(self) -> bytes:
        """DoIP DiagnosticMessageを受信してUDSペイロードを返す。"""
        if not self._client:
            raise RuntimeError("Not connected.")
        return self._client.receive_diagnostic()
