# Introduction

We intend to build a machine learning model that predicts water flow in water basins without sensor data. The inputs to the model include land, soil and climate attributes, which will be evaluated against water flow measurements from water basins with sensor data. Most water basins have no sensor data yet water managers need flow estimates for flood and drought planning. An inexpensive, interpretable method that can be easily deployed where we have confidence in its predictive power is useful, and understanding where the method fails improves our understanding of hydrologic processes.

Today, hydrologists tune a physical model for each river with historical measure water flow. For rivers without sensor data, they compare with nearby, similar "donor" rivers, which has proven to be failure-prone. Deep learning models trained on hundreds of rivers now do better [@kratzert2019], but they're computationally intensive and suffer from interpretability.

Our approach will test whether the standard practice that "similar rivers behave alike" improves with unsupervised water basin clustering and predictive models accounting for spatial proximity, weather patterns, and ecological attributes. We will compare models with minimal inputs, a basin's cluster, and its full attributes to determine the most accurate approach. We want to understand the most predictive characteristics, in particular whether basin clustering is an informative exercise.

Clustering may discard important information from the raw attributes of the water basins in the training data and predefined weather windows may need additional context to account for slow snowmelt and groundwater levels. However, clustering may help when training basins are scarce, where informatively characterizing a water basin from its raw attributes is impractical. Therefore, our main focus will be to evaluate whether clustering helps when training basins are scarce.

We will assess our model on its predictive accuracy of water flow, as measured with the Nash-Sutcliffe Efficiency metric:

$$
\mathrm{NSE} = 1 - \frac{\sum_{t} \left(Q_{\mathrm{obs},t} - Q_{\mathrm{pred},t}\right)^2}{\sum_{t} \left(Q_{\mathrm{obs},t} - \bar{Q}_{\mathrm{obs}}\right)^2}
$$

 We will train separate neural networks for each cluster. New and test observations will be assigned to the nearest cluster centroid and then routed to the corresponding neural network for prediction. To avoid leakage we will split by basin using spatially-blocked folds; refit scalers PCA and clustering inside each fold; and train on earlier years to avoid temporal correlation.
