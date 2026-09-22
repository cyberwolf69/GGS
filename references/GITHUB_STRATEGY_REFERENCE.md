# GitHub strategy reference used by GGS

Public source: https://github.com/Novals83/5min-btc-polymarket

Observed strategy/profile points used as context in the GGS momentum engine:

- style: momentum follow-through into close
- target entry timing around 120 seconds remaining
- BTC move reference about $70-$100
- prefer the direction supported by market skew
- current canonical runner trigger is CLOB best ask and stronger side over threshold
- threshold in current profiles: 0.70
- current repo notes explicitly say the canonical 5m runner uses threshold/side-strength logic and the impulse filter can be extended at the strategy layer

GGS does not retain 0.70 as a hard entry threshold because its hard payout objective is >=1.50x, which requires entry <=0.6666667. Instead, the repo's direction/skew/move/timing concepts contribute to a confirmation score.
