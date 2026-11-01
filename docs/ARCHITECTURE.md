# Architecture FASTLIFE QUANT AI

Package : `src/fastlife_quant/`

| Module | Phase | Etat |
|---|---|---|
| `data` (modeles + validation OHLCV) | 1 | implemente, teste |
| `market` | 2 | non implemente |
| `ict_smc` | 3 | non implemente |
| `quant` | 4 | non implemente |
| `risk` | 5 | non implemente |
| `backtesting` | 6 | non implemente |
| `macro` | 7 | non implemente |
| `mt5` (demo uniquement) | 8 | non implemente |
| `api`, `dashboard` | 9 | non implemente |

## Principes

- Chaque bougie porte source, horodatage UTC, timeframe, statut de validation et nature (`real` / `simulated` / `unavailable`).
- Le validateur detecte et rapporte, il ne corrige et n'invente jamais (pas de forward-fill, pas d'interpolation). Il ne modifie pas ses entrees.
- Les trous de donnees : weekends = attendus (vendredi -> dimanche/lundi, <= 72 h) ; tout autre trou = avertissement, jamais comble. Les jours feries sont donc signales en avertissement.
- Les series de tests sont des fixtures deterministes marquees `test_fixture` / `simulated`, jamais des donnees de marche.
- Aucune execution d'ordre reel. `ALLOW_LIVE_EXECUTION=false` dans `.env.example`.

## Lancer les tests

```
pip install -e ".[dev]"
pytest
```
