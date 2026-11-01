from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Application API de lecture et de supervision.

    Aucun ordre n'est execute via cette API; elle sert de couche d'exposition pour
    les analyses, le contexte macro, les statistiques et les metriques de risque.
    """
    app = FastAPI(title="FASTLIFE QUANT AI API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "analysis_only"}

    @app.get("/status")
    def status() -> dict[str, str]:
        return {"project": "fastlife-quant-aii", "phase": "scaffolding"}

    return app


__all__ = ["create_app"]
