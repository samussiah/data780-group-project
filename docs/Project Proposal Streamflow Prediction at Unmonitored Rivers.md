# Project Proposal: Streamflow Prediction at Unmonitored Rivers

Oct 3, 2026 · @Spencer

**Does Grouping Similar Watersheds Help Predict River Flow Where There Are No Gauges?**

**Team:** Spencer Childress, \[Teammate 2\], \[Teammate 3\] · **Course:** DATA 780: Machine Learning

## Heilmeier Criteria

**What are we trying to do?** Estimate how much water flows in a river each day at places with no measuring equipment, using only descriptions of the land and local weather.

**How is it done today, and what are the limits?** Hydrologists tune a physical model for each river using years of measured flow. For unmeasured rivers, they borrow settings from nearby or similar "donor" rivers, which often fails across climates. Deep learning models (LSTMs) trained on hundreds of rivers now do better: median NSE 0.69 on 531 unmeasured US basins ([Kratzert et al., 2019](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2019WR026065)). They are costly to train and hard to interpret.

**What is new, and why will it succeed?** We test whether the old "similar rivers behave alike" idea, done with unsupervised ML, helps simple tabular models. We cluster basins on land, soil and climate attributes, then compare telling a model nothing, the basin's cluster, or its full attributes. A synthetic benchmark shows when clustering *should* help, so the real-data results are interpretable whichever way they fall.

**Who cares?** Most of the world's rivers have no gauge, yet water managers need flow estimates for flood and drought planning. A cheap, interpretable method, or clear evidence of when it fails, is useful either way.

**Risks and payoffs.** Clusters may discard information that raw attributes keep. Fixed weather windows may miss slow snowmelt and groundwater. Climate differences may break US-to-Great Britain transfer. Each risk is an explicit comparison in our design, not an assumption. The payoff is evidence-backed best practices for predicting flow in unmeasured basins with simple models.

## Methods, Data and Evaluation

**Methods.** *Baselines:* Ridge regression on lagged weather; nearest-gauge transfer. *Unsupervised:* PCA, then k-means vs. agglomerative clustering, varying k. *Supervised:* LightGBM and RBF kernel regression (Nyström approximation; exact SVR on a subsample). *Basin information given to the model:* none; cluster ID; one model per cluster; PCA or raw attributes. *Preprocessing compared:* weather windows (7/30 vs. adding 90/365 days), raw vs. log flow, PCA on vs. off. *Hyperparameters:* k, tree depth and learning rate, kernel bandwidth.

**Data.** *Real:* two [Caravan](https://github.com/kratzert/Caravan) subsets in the same format: CAMELS-US (150–300 basins) and CAMELS-GB, with daily weather, daily flow and static basin attributes. We exclude any attribute derived from observed or modeled flow (e.g., mean flow, runoff ratio), which would leak the answer. *Synthetic:* a one-bucket water-balance simulator generates populations of basins whose storage parameters depend on synthetic attributes:

```latex
S_{t+1} = S_t + P_t - ET_t - Q_t
```

In one scenario basins come in three discrete types, so clustering should help and should recover them. In the other, parameters vary smoothly, so raw attributes should win.

**Evaluation.** Median Nash–Sutcliffe Efficiency (NSE), Kling–Gupta Efficiency (KGE) and RMSE on held-out basins, using 5–10-fold GroupKFold by basin plus a held-out time period. Scaling, PCA and clustering are fit inside each fold. We also train on US basins and test on British ones. On synthetic data we score cluster recovery (adjusted Rand index) and fit to the true flow. SHAP values on LightGBM check that models rely on physically sensible drivers.

**Success.** We answer the central question with bootstrap confidence intervals across basins: does cluster information improve held-out median NSE over full attributes? Secondary targets: held-out median NSE above 0.40, and a positive absolute NSE gain over nearest-gauge transfer.

**Tools.** Python (pandas, scikit-learn, LightGBM, SHAP, matplotlib); NeurIPS LaTeX template; public GitHub repository.

## Timeline and Progress

**Done so far:** chose CAMELS/Caravan, reviewed the data structure and prior work, and drafted the experimental design.

| Weeks | Milestones |
| --- | --- |
| 1–2 | Download US and GB subsets; build weather-window features; write bucket simulator; set up repo and NeurIPS template |
| 3–4 | PCA and clustering; Ridge and nearest-gauge baselines; synthetic experiments |
| 5–6 | LightGBM and kernel models across all basin-information arms; preprocessing and hyperparameter sweeps; US-to-GB test. Experiments frozen end of week 6 |
| 7 | SHAP analysis; best-practices list; full paper draft (methods written as we go) |
| 8 | Revise paper; spotlight presentation; buffer for slippage |
