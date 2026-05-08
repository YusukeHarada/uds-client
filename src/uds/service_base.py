"""
UDSサービス共通データモデル。

pydanticを使用することで以下を実現する：
- DID/NRCコードの範囲バリデーション自動化
- JSON直列化（ログ・GUI連携）
- 型安全なフィールドアクセス
"""
from typing import Optional
from pydantic import BaseModel, field_validator


class UDSResult(BaseModel):
    """全UDSサービスの共通レスポンスモデル。"""

    success: bool
    did: Optional[int] = None
    data: Optional[bytes] = None
    nrc_code: Optional[int] = None
    nrc_message: Optional[str] = None
    raw_request: Optional[bytes] = None
    raw_response: Optional[bytes] = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("did", "nrc_code", mode="before")
    @classmethod
    def must_be_uint16(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (0x0000 <= v <= 0xFFFF):
            raise ValueError(f"Value must be in 0x0000-0xFFFF, got {v}")
        return v
