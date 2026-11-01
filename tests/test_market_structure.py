# Phase 3 - ICT/SMC Engine

## Objectif

Le moteur ICT/SMC fournit des evenements explicables pour XAUUSD en respectant strictement les regles de la donnee et l'absence de look-ahead.

## Parametres

- `swing_left_bars`: 3 bougies de gauche
- `swing_right_bars`: 3 bougies de droite
- `confirmation_only_closed`: confirmation uniquement sur des bougies closes
- `atr_period`: periode ATR par defaut 14
- `fvg_atr_filter`: filtre optionnel sur l'ATR
- `order_block_atr_threshold`: seuil de deplacement mesure en ATR
- `structural_confirmation_bars`: nombre de bougies de confirmation structurelle

## Principes

- Le moteur n'utilise que des donnees disponibles jusqu'a l'index courant.
- Les evenements contiennent: type, direction, timeframe, timestamp, prix, bougies de reference, conditions, parametres, confirmation, invalidation.
- Les donnees synthétiques de tests sont clairement identifiees.

## Detecteurs implementes

- Market structure: swing high, swing low, BOS, CHoCH, MSS, internal/external structure
- Liquidity: BSL, SSL, equal highs/lows, liquidity sweep, inducement
- Imbalance: bullish/bearish FVG, inverse FVG, displacement
- Order blocks: bullish/bearish order block, mitigation, breaker block
- Contexte: premium, discount, equilibrium, OTE et analyse multi-timeframe

## Validation

Les tests Pytest couvrent les cas positifs, negatifs, donnees invalides et invariance de prefixe.
