"""
ProtocolレイヤStrategyインターフェース。

DoIP/J1939など通信プロトコルをこのインターフェースで抽象化する。
DiagnosticServiceはこのインターフェースのみに依存するため、
プロトコル実装を差し替えてもアプリケーションロジックは変更不要。
"""
from abc import ABC, abstractmethod


class ProtocolBase(ABC):

    @abstractmethod
    def connect(self) -> None:
        """ECUへの接続を確立する。"""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """接続を切断する。"""
        ...

    @abstractmethod
    def send(self, uds_payload: bytes, **kwargs) -> None:
        """UDSペイロードを送信する。"""
        ...

    @abstractmethod
    def receive(self) -> bytes:
        """UDSペイロードを受信して返す。"""
        ...
