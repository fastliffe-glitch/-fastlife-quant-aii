from __future__ import annotations

from fastapi import FastAPI

from fastlife_quant.api.routes import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="FASTLIFE QUANT AI API", version="0.1.0")
    app.include_router(api_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "analysis_only"}

    @app.get("/status")
    def status() -> dict[str, str]:
        return {"project": "fastlife-quant-aii", "phase": "implementation"}

    return app


__all__ = ["create_app"]
