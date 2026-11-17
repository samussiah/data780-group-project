- k-nearest neighbors vs k-means clustering
- if lightgbm doesn't work, what will we try?
- evaluate feasibility on 30 days and 90 days with lightGBM vs k-nearest neighbors
- see what kind of performance we're getting on the NSE outcome
- use the best data first to avoid missingness
- compare a complex model like lightGBM with a simple model like 
- median absolute deviation of a single/all rivers to understand variance across time/over years
- ridge regression vs k-nearest neighbors vs k-means clustering

from professor:
median absolute deviation
Calculate the median absolute deviation for each stream over each of the 15 years
You may find that certain years have a LOT of deviation in a subset of streams (torrential rains, droughts, etc.)  These years will lead to more error

GUIDING PRINCIPLE:
A) Prune the input dataset to the “cleanest”, easiest subset
B) Choose time intervals (30 days, 90 days) that will have less drastic variability or lack of predictive power
C) Choose streams with the most complete data

PART I. ENRICH FOR HIGH-QUALITY DATA
PART II. IMPLEMENT A SIMPLE MODEL (k-Nearest Neighbors) and LIGHTGBM
PART III. IF Parts I and II are successful, then gradually expand the scope of the data / time window.  => Interpret WHY the model “fails” once you expand scope

interpret why the model fails 

You can “probe” what the model is actually learning but explaining why it "breaks"
