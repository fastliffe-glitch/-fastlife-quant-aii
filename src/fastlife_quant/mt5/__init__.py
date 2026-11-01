from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MT5Config:
    account: str = "demo"
    server: str = "demo_server"
    login: int = 0
    password: str = ""
    path: str | None = None
    enabled: bool = False


@dataclass
class DemoAccountSnapshot:
    balance: float
    equity: float
    margin_free: float
    open_positions: int
    login: int
    server: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MT5Client:
    """Client MetaTrader 5 pour donnees de test et compte demo.

    Aucun ordre reel n'est execute. Les interactions sont limitees au contexte de
    lecture et d'analyse des donnees demo, avec trace explicable.
    """

    def __init__(self, config: MT5Config | None = None) -> None:
        self.config = config or MT5Config()

    def connect(self) -> bool:
        return self.config.enabled

    def get_demo_snapshot(self) -> DemoAccountSnapshot | None:
        if not self.connect():
            return None
        return DemoAccountSnapshot(balance=0.0, equity=0.0, margin_free=0.0, open_positions=0, login=self.config.login, server=self.config.server)


__all__ = ["DemoAccountSnapshot", "MT5Client", "MT5Config"]
