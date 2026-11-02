# Réparation ICT/SMC — réalignement des modules (branche `fix/ict-smc-module-realignment`)

Rapport de diagnostic et de réparation, produit à partir de `main` @ `bde4680`.
Principe suivi : aucune logique ICT/SMC modifiée, aucune assertion modifiée, Risk Engine V2 intact,
aucune validation fabriquée. Tout ce qui est affirmé ci-dessous a été vérifié par une commande ;
ce qui ne l'a pas été est signalé comme tel.

## 1. Cause racine

Le commit Phase 3 (`34ad1f8`) a enregistré les contenus dans les **mauvais fichiers**, par décalage
circulaire, y compris pour les tests et la documentation. Le commit « Repair » (`657cdc8`) n'a corrigé
qu'une partie du problème.

| Fichier (état `main`)  | Contenait en réalité            | Destination |
|------------------------|---------------------------------|-------------|
| `ict_smc/context.py`   | Order blocks, mitigation, breaker | `order_blocks.py` |
| `ict_smc/order_blocks.py` | FVG, inverse FVG, displacement | `imbalance.py` |
| `ict_smc/imbalance.py` | BSL/SSL, equal highs/lows, sweep, inducement | `liquidity.py` |
| `ict_smc/liquidity.py` | Structure de marché (swings, BOS, CHoCH…) | `market_structure.py` (voir §3) |
| `quant/__init__.py` @ `34ad1f8` | premium, discount, equilibrium, OTE, `multi_timeframe_analysis` | `context.py` |
| `tests/test_market_structure.py` | Documentation Phase 3 (Markdown) | `docs/PHASE3_ICT_SMC.md` |
| `ict_smc/market_structure.py` @ `34ad1f8` | Le test des métriques quant | `tests/test_quant_metrics.py` |

Les cinq fonctions de contexte avaient été retirées de `quant/__init__.py` par `657cdc8` sans jamais être
remises dans `context.py` : d'où `ImportError: cannot import name 'detect_discount'`.

## 2. Ce que fait cette branche (4 commits, hors rapport initial)

1. `d12c19e` — quatre modules restaurés **octet pour octet** depuis leur blob d'origine :
   `order_blocks.py == 34ad1f8:ict_smc/context.py`, `imbalance.py == 34ad1f8:ict_smc/order_blocks.py`,
   `liquidity.py == 34ad1f8:ict_smc/imbalance.py`, `context.py == 34ad1f8:quant/__init__.py`.
   Vérifiable : `cmp <fichier> <(git show 34ad1f8:<chemin source>)`.
2. `666e0aa` — le Markdown de la Phase 3 retourne dans `docs/PHASE3_ICT_SMC.md` (identique octet pour octet
   à l'ancien contenu de `tests/test_market_structure.py`). Rien d'utile perdu : le Python qui occupait ce
   doc (`win_rate`, `expectancy`, `profit_factor`, `average_win_loss`) existe dans `quant/metrics.py`
   (3 fonctions identiques à l'AST, `expectancy` différente seulement par la forme, 0 écart sur 32
   comparaisons à l'exécution) et reste dans l'historique à `34ad1f8:docs/PHASE3_ICT_SMC.md`.
3. `ed781af` — six fichiers de test renommés d'après leur vrai sujet, contenu inchangé
   (hash de chaque cible = hash de sa source ; 98 tests collectés avant comme après) :
   `test_context→test_order_blocks`, `test_order_blocks→test_imbalance`, `test_imbalance→test_liquidity`,
   `test_liquidity→test_market_structure`, `test_ict_smc_engine→test_context`,
   `test_quant_metrics→test_ict_smc_engine`.
4. `f054332` — le vrai test des métriques quant, écrasé en `34ad1f8`, est restauré tel quel
   (`tests/test_quant_metrics.py == blob 34ad1f8`), sans assertion modifiée.

`git diff --stat main -- src/fastlife_quant/risk tests/test_risk_v2.py` est vide : Risk Engine V2 intact.
`main` n'est pas modifié ; la PR #1 reste en brouillon, non fusionnée.

## 3. Décision laissée ouverte : `market_structure.py`

Deux implémentations de la structure de marché coexistent : celle de `34ad1f8` (dans l'ancien `liquidity.py`)
et celle réécrite par `657cdc8`/`926f776` (`market_structure.py`). Elles diffèrent réellement
(ex. `idx < 3` contre `idx < 2`, `trigger_conditions` et `parameters` différents).
`market_structure.py` est **laissé tel quel** (comportement identique à `main`).
Dans une copie jetable, les deux variantes donnent exactement les mêmes 8 échecs : le choix n'est donc
pas guidé par la couleur des tests. L'autre variante reste récupérable
(`git show bde4680:src/fastlife_quant/ict_smc/liquidity.py`).

## 4. État réel des tests (local et CI, commit `f054332`)

| Mesure | Résultat |
|---|---|
| CI, étape « focused RiskEngineV2 tests » | **33 réussis** |
| CI, étape « full test suite » | **interrompue** par 1 erreur de collecte (`tests/test_quant_metrics.py`) : aucun autre test n'est exécuté |
| Local, suite complète avec `--continue-on-collection-errors` | **90 réussis, 8 échoués, 1 erreur de collecte** |

### Erreur de collecte

`tests/test_quant_metrics.py` : `ImportError: cannot import name 'compute_expectancy'`.
`quant/__init__.py` importe `compute_expectancy`, `compute_win_rate`, `compute_profit_factor`,
`compute_max_drawdown`, absents de `quant/metrics.py` (qui définit `win_rate`, `expectancy`,
`profit_factor`, `max_drawdown`). `orchestrator.py` dépend du même paquet et ne s'importe pas non plus.

Au-delà de l'import, ce test échouerait de lui-même (vérifié sur une copie jetable chargeant `metrics.py`
par son chemin, assertions inchangées) : `expectancy` vaut `0.44000000000000006` (égalité flottante exacte
avec `0.44`), `average_win_loss` idem, et le `profit_factor` attendu (`1.5 / 0.3 = 5.0`) contredit
l'arithmétique des données du test elle-même (gains 2,5 ; pertes 0,3 ; soit 8,33).

### Les 8 échecs (noms de tests après renommage)

| Test | Constat |
|---|---|
| `test_context::test_premium_discount_equilibrium_and_ote` | **Vérifié** : exige premium, discount et equilibrium sur la même bougie (plage 95→109, clôture 107, position 0,86). États mutuellement exclusifs : aucun détecteur correct ne peut satisfaire ce test. |
| `test_imbalance::test_bullish_and_bearish_fvg` | **Vérifié (FVG haussier)** : à l'idx 2, `low` (98) doit dépasser le `high` de la bougie 0 (101) ; faux dans la fixture. Détecteur conforme à la définition ICT. Cas baissier non examiné séparément. |
| `test_imbalance::test_prefix_invariance_imbalance` | Même fixture et même appel (`detect_bullish_fvg(df, 2)`) que le test ci-dessus : même cause. |
| `test_imbalance::test_inverse_fvg_and_displacement_detected` | `None` avec ATR(14) comme avec `atr_period=3` : l'ATR n'est pas la cause. **Non tranché.** |
| `test_order_blocks::test_order_blocks_and_mitigation_detected` | `detect_bullish_order_block` : bloqué seulement par l'ATR(14) = `NaN` ; tire avec `atr_period=3` (essai diagnostique). `bearish_order_block` et `mitigation` restent `None` même ainsi ; `breaker_block` tire. |
| `test_liquidity::test_bsl_and_ssl_detected` | `detect_bsl` tire, `detect_ssl` renvoie `None` (ATR non en cause). **Non tranché.** |
| `test_liquidity::test_liquidity_sweep_and_inducement` | `None` quel que soit l'ATR. **Non tranché.** |
| `test_market_structure::test_choch_detects_trend_change` | `None` avec les deux variantes de `market_structure.py`. **Non tranché.** |

Constat transversal : `compute_atr` renvoie `NaN` quand il y a moins de `period` bougies, et les détecteurs
comparent avec `NaN` (toujours faux) : échec **silencieux**. C'est un choix de conception à décider, pas à
contourner. Le message du commit `fbf7d40` précise qu'il a été produit « without … running tests » ;
je n'ai pas vérifié si les tests ICT/SMC ont été exécutés à un autre moment.

## 5. Décisions requises avant toute modification de logique ou de tests

(a) variante de `market_structure.py` ; (b) pour chacun des 8 échecs, corriger la fixture, corriger le
détecteur, ou retirer le test contradictoire — après analyse individuelle ; (c) politique à adopter quand
l'ATR n'est pas calculable ; (d) exports de `quant/__init__.py` (noms `compute_*` contre noms réels) ;
(e) les trois assertions du test quant restauré (flottants exacts, valeur attendue de `profit_factor`).
