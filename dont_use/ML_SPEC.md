# Machine Learning Specification

## Problem formulation
At time T, predict health impact at:
```text
T+1, T+2, T+3, T+4, T+5 days
```
using only information that would be available at T.

## Inputs
### Static ward features
- population density
- elderly percentage
- outdoor-worker density
- slum/vulnerability variables
- vegetation/tree cover
- built-up density
- construction density
- healthcare accessibility

### Historical time-varying features
- temperature
- humidity
- wind
- radiation
- WBGT/UTCI/Heat Index
- health history
- anomalies and rolling features

### Known future covariates
Use weather **forecasts** for future dates, not future observed weather.

## Target types
Preferred count targets:
```text
future mortality count
future hospitalization count
```
Classification risk can be derived from counts or directly modeled if an explicitly defined label exists.

## Baseline
Use LightGBM first.

Purpose:
- benchmark performance
- detect data problems
- inspect feature importance
- establish a strong non-neural baseline

## Main model
Temporal Fusion Transformer implemented with PyTorch or a mature compatible library.

The model should support:
- static covariates
- historical time-varying covariates
- known future covariates
- multi-horizon outputs

Default:
```text
lookback = 14 days
horizon = 5 days
```
Make both configurable.

## Alternatives
Evaluate only where useful:
- LSTM
- GRU
- TCN

## Spatial model
Optional ST-GNN:
```text
ward = node
neighboring wards = edges
node features = weather + thermal + demographic + environment
```
Do not add this before the ward-level baseline works.

## Count modeling
Consider Poisson or negative-binomial objectives when appropriate. Inspect overdispersion before selecting a count distribution.

## Splitting
Primary evaluation:
- chronological split
- walk-forward validation
- rolling-origin evaluation

Never use random split as the main forecasting evaluation.

## Leakage checklist
For each feature ask:
1. Was it known at prediction time?
2. Is it derived from future observations?
3. Was it computed using the full dataset before splitting?
4. Does it include future target information through rolling windows?

If yes, redesign the feature.

## Metrics
Count:
- MAE
- RMSE
- Poisson deviance
- negative-binomial deviance where appropriate

Risk:
- precision
- recall
- F1
- ROC-AUC
- PR-AUC

Probabilistic:
- Brier score
- CRPS where applicable
- calibration error
- interval coverage

Operational:
- false alarm rate
- missed-event rate
- warning lead time

## Model artifacts
Save:
```text
model weights
feature list
config
training period
validation period
test period
metrics
random seed
package/environment information
data version/hash
```

## Explainability
Use SHAP for tree models. For deep models, use appropriate temporal attribution methods where reliable. Explain model contributions, not causality.
