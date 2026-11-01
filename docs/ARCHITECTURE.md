# Architecture FASTLIFE QUANT AI

Package : `src/fastlife_quant/`

| Module | Phase | Etat |
|---|---|---|
| `data` (modeles + validation OHLCV) | 1 | implemente, teste |
| `market` (import, nettoyage, timeframes, sessions, pipeline) | 2 | implemente, teste sur fixtures ; aucune donnee reelle importee a ce jour |
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
- Fuseaux : les exports MT5 sont en heure serveur du broker. Le fuseau IANA est un parametre obligatoire (aucun defaut silencieux) ; tout est converti en UTC. Heures ambigues (changement d'heure) : erreur explicite, ou `ambiguous="infer"` si les deux occurrences sont dans le fichier.
- Donnees brutes : le fichier d'origine est copie tel quel dans `data/raw/` (prefixe SHA-256, idempotent) et jamais modifie. La sortie nettoyee va dans `data/processed/` avec un `.meta.json` de provenance (source, nature real/simulated, fuseau, compteurs, statut).
- Nettoyage : doublons exacts supprimes (logges) ; doublons conflictuels et lignes invalides mis en quarantaine (fichier `.quarantine.csv`), jamais choisis ni corriges ; aucun comblement de trou.
- Timeframes superieurs : agregation depuis un timeframe inferieur avec `n_bars` et `coverage` par bougie ; buckets sous `min_coverage` ecartes et comptes. Alignement H4/D1 ancre sur minuit UTC par defaut (parametre `anchor`) : pour coller exactement au broker, preferer l'import natif H4/D1 de MT5. La pause quotidienne de l'or donne une couverture < 1 en D1 : `min_coverage` doit etre regle explicitement.
- Sessions : fenetres UTC fixes et configurables, sans suivi des changements d'heure.
- Aucune execution d'ordre reel. `ALLOW_LIVE_EXECUTION=false` dans `.env.example`.

## Lancer les tests

```
pip install -e ".[dev]"
pytest
```
