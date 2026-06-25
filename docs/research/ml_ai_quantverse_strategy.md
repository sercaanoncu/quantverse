# ML And AI Strategy For QuantVerse

## 1. Current Downside-Risk ML Layer

The current ML layer is a downside-risk diagnostic. It evaluates whether market
and return-derived features contain information about downside-risk periods. It
is not used as an autonomous allocation engine and it is not marketed as a model
that predicts the market.

## 2. Why It Should Remain Diagnostic For Now

The available evidence is not enough to promote ML outputs into direct
portfolio weights. A diagnostic layer can still be useful because it helps
explain risk conditions, feature behavior and possible overlay designs without
creating false precision.

## 3. Why Daily Return Prediction Is Hard

Daily returns have low signal-to-noise ratio. Relationships can break across
regimes, and small predicted edges can disappear after turnover and transaction
costs. A model with acceptable prediction metrics can still produce poor
portfolio decisions if the signal is unstable or too expensive to trade.

## 4. Why LSTM, Transformer And RL Are Not First-Line Models

LSTM, Transformer and reinforcement-learning allocation are not production
allocation engines in QuantVerse. They require strict chronological validation,
purged/embargoed splits where labels overlap, careful transaction-cost modeling,
model-risk approval and evidence that they improve over simple rules such as
Equal Weight and risk-controlled momentum.

In short: LSTM, Transformer, RL and LLM allocation agents are not production allocation engines in this project.

They are deliberately excluded from the current sprint to avoid adding advanced
names without defensible portfolio evidence.

## 5. Recommended Next ML Step

The next defensible ML step is an overlay, not raw return prediction:

- Meta-labeling: predict when an already-defined momentum or rotation signal is
  more likely to work.
- Rebalance veto: block or reduce a rebalance when downside-risk probability is
  too high.
- Risk overlay: reduce exposure or raise defensive allocation when risk
  conditions deteriorate.
- Uncertainty-aware model: require confidence thresholds before changing
  allocation.
- Regularized models before deep learning: Ridge, LASSO, Elastic Net or simple
  tree baselines should be tested before sequence models.

## 6. LLM Role

LLMs can help with:

- Research assistance.
- Text, sentiment and event feature extraction.
- Stress scenario generation.
- Report drafting and governance documentation.
- RAG-style research notebooks.

LLMs are not autonomous portfolio managers in this project. They should not set
weights without a validated quantitative signal, data provenance, model-risk
controls and human review.

## 7. Future Roadmap

Future ML/AI extensions should follow this order:

1. FinBERT or comparable news sentiment feature extraction.
2. Macro event extraction.
3. Text-based risk overlay.
4. LLM-RAG research notebook for evidence retrieval and governance.
5. Deep learning only after strict validation and after simpler baselines fail
   to explain the same effect.

Any future ML allocation layer must report net performance after costs, turnover,
subperiod behavior, bootstrap uncertainty and overfit diagnostics.
