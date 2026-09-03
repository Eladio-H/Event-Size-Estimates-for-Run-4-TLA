## How to gather the data to produce this specific plot

First you require your data, whose workflow we agreed not to include for the sake of simplicity. Save your rucio datasets from the jobs to a folder in here called ```data```. All you need is 
1. the jobs where you reprocessed only the dimuon trigger and
2. the jobs where you reprocessed the dimuon trigger as well as all the TLA jet triggers but with their multiplicity ramped up to 100 so that these triggers are forced to fail.

To obtain these datasets, all you need to do is the steps detailed in ```gridSubmit```, but customising your trigger menu in the case of item 2. in these instructions (whereas item 1. you can already obtain from the unchanged code in ```gridSubmit```).

## Final touches and produce plots

To finally produce plots, first run (from this directory)

```
source ../setup.sh
python 1_counts.py
```

to set up your environment and count all the events inside the RAW files you retrieved from your jobs (now presumably in a folder called ```data```). Then, just run the cells in the jupyter notebook.
