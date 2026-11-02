# Réparation ICT/SMC — réalignement des modules (branche `fix/ict-smc-module-realignment`)

Rapport de diagnostic et de réparation, produit à partir de `main` @ `bde4680`.
Principe suivi : aucune logique ICT/SMC modifiée, aucun test modifié, Risk Engine V2 intact,
aucune validation fabriquée. Tout ce qui est affirmé ci-dessous a été vérifié par une commande ;
ce qui ne l'a pas été est signalé comme tel.

## 1. Cause racine

Le commit Phase 3 (`34ad1f8`) a enregistré les contenus dans les **mauvais fichiers**, par décalage
circulaire. Le commit « Repair » (`657cdc8`) n'a corrigé qu'une partie du problème.

| Fichier (état `main`)  | Contenait en réalité            | Contenu attendu / destination |
|------------------------|---------------------------------|-------------------------------|
| `ict_smc/context.py`   | Order blocks, mitigation, breaker | `order_blocks.py`           |
| `ict_smc/order_blocks.py` | FVG, inverse FVG, displacement | `imbalance.py`              |
| `ict_smc/imbalance.py` | BSL/SSL, equal highs/lows, sweep, inducement | `liquidity.py`  |
| `ict_smc/liquidity.py` | Structure de marché (swings, BOS, CHoCH…) | `market_structure.py` (voir §3) |
| `quant/__init__.py` @ `34ad1f8` | premium, discount, equilibrium, OTE, `multi_timeframe_analysis` | `context.py` |

Les cinq fonctions de contexte avaient été retirées de `quant/__init__.py` par `657cdc8` sans jamais être
remises dans `context.py` : d'où `ImportError: cannot import name 'detect_discount'`.

## 2. Ce que fait cette branche

Quatre fichiers remplacés par le contenu **d'origine**, octet pour octet :

```
order_blocks.py == 34ad1f8:ict_smc/context.py
imbalance.py    == 34ad1f8:ict_smc/order_blocks.py
liquidity.py    == 34ad1f8:ict_smc/imbalance.py
context.py      == 34ad1f8:quant/__init__.py
```

Vérifiable : `cmp <fichier> <(git show 34ad1f8:<chemin source>)`.
Rien d'autre n'est modifié : `git diff --stat main -- src/fastlife_quant/risk tests` est vide.

## 3. Décision laissée ouverte : `market_structure.py`

Deux implémentations de la structure de marché coexistent : celle de `34ad1f8` (dans l'ancien `liquidity.py`)
et celle réécrite par `657cdc8`/`926f776` (`market_structure.py`). Elles diffèrent réellement
(ex. `idx < 3` contre `idx < 2`, `trigger_conditions` et `parameters` différents).
`market_structure.py` est **laissé tel quel** (comportement identique à `main`).
Dans une copie jetable, les deux variantes donnent exactement les mêmes 8 échecs : le choix n'est donc
pas guidé par la couleur des tests. L'autre variante reste récupérable (`git show bde4680:src/fastlife_quant/ict_smc/liquidity.py`).

## 4. État des tests après réalignement

`pytest` hors `tests/test_market_structure.py` (voir §5) : **8 failed, 90 passed**.
Risk Engine V2 : 33 tests, tous verts, fichiers non touchés.

Les imports sont réparés ; les 8 échecs restants sont de **vraies assertions** (détecteur qui renvoie `None`).
Le message du commit `fbf7d40` précise qu'il a été produit « without … running tests » ; je n'ai pas vérifié si les tests ICT/SMC ont été exécutés à un autre moment.

| Test en échec | Constat vérifié |
|---|---|
| `test_ict_smc_engine::test_premium_discount_equilibrium_and_ote` | Exige premium **et** discount **et** equilibrium sur la même bougie. Fixture : plage 95→109, clôture 107, position 0,86 : premium oui, discount/equilibrium non. États mutuellement exclusifs : aucun détecteur correct ne peut satisfaire ce test. |
| `test_order_blocks::test_bullish_and_bearish_fvg` | FVG haussier à l'idx 2 : `low`(98) doit dépasser `high` de la bougie 0 (101). Faux dans la fixture. Détecteur conforme à la définition ICT. |
| `test_context::test_order_blocks_and_mitigation_detected` | `detect_bullish_order_block` : bloqué uniquement par l'ATR(14) = `NaN` (fixture < 14 bougies) ; tire avec `atr_period=3` (essai diagnostique, rien modifié). `bearish_order_block` et `mitigation` restent `None` même ainsi. |
| `test_imbalance` (2 tests), `test_liquidity::test_choch…`, `test_order_blocks` (2 autres tests) | `None` avec ATR(14) comme avec `atr_period=3` : l'ATR n'est pas la cause. Cause (détecteur ou fixture) **non tranchée**, à examiner détecteur par détecteur. |

Constat transversal : `compute_atr` renvoie `NaN` quand il y a moins de `period` bougies, et les détecteurs
comparent avec `NaN` (toujours faux) : échec **silencieux**. C'est un choix de conception à décider, pas à contourner.

## 5. Autres anomalies constatées (hors périmètre, non corrigées)

1. `tests/test_market_structure.py` contient le texte Markdown de la doc Phase 3 (échec de collecte :
   `SyntaxError`), et `docs/PHASE3_ICT_SMC.md` contient du code Python de métriques : les deux sont échangés.
   Tant que ce fichier est en place, `pytest -q` complet ne peut pas se collecter.
2. Le vrai test des métriques quant (`win_rate == 0.6`, etc.) a été écrasé ; il n'existe plus que dans
   `git show 34ad1f8:src/fastlife_quant/ict_smc/market_structure.py`.
3. `fastlife_quant.quant` ne s'importe pas : `quant/__init__.py` importe `compute_expectancy`,
   `compute_win_rate`, `compute_profit_factor`, `compute_max_drawdown`, absents de `quant/metrics.py`
   (qui définit `win_rate`, `expectancy`, `profit_factor`, `max_drawdown`). `orchestrator.py` en dépend.
4. Les fichiers de test sont nommés d'après le mauvais sujet (ex. `test_context.py` teste les order blocks,
   `test_liquidity.py` la structure de marché, `test_quant_metrics.py` le moteur ICT/SMC).
   Sans effet fonctionnel (les tests importent depuis `fastlife_quant.ict_smc`), laissé en l'état.

## 6. Pour valider réellement la Mission 1

Décisions requises avant toute modification de logique ou de tests : (a) variante de `market_structure.py` ;
(b) pour chaque test en échec, corriger la fixture, corriger le détecteur, ou supprimer le test contradictoire ;
(c) politique ATR insuffisant ; (d) fichier Markdown/`.py` échangé ; (e) exports de `quant`.
