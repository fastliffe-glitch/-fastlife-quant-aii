# -fastlife-quant-aii

**FASTLIFE QUANT AI** - laboratoire quantitatif ICT/SMC pour XAUUSD.

Question centrale : les configurations ICT/SMC ont-elles un avantage statistique mesurable ?

> La donnee avant l'opinion. La statistique avant la conviction. La protection du capital avant la performance.

## Etat

Phase 1 en cours : fondations (modeles de donnees, validation OHLCV, tests). Les autres modules sont des
emplacements vides, voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Aucun resultat de performance n'est affiche tant qu'il n'est pas calcule sur des donnees reelles verifiees.
Un backtest profitable n'est jamais une preuve de rentabilite future. Aucune execution d'ordre reel.

## Demarrage

```
pip install -e ".[dev]"
cp .env.example .env   # puis remplir (ne jamais commiter .env)
pytest
```
