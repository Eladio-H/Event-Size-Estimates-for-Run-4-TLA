This directory enables reprocessing RAW files out of the dataflow with athenaHLT using a customised EDM and a customised trigger menu, and in this way learn of the event size and the container multiplicities (muons and tracks) for these files.

The file-selecting algorithm selects files from 5 different run numbers:
- 507671: PU 40-65
- 507733: PU 40-65
- 507758: PU 40-65
- 508073: PU 130-150
- 509891: PU 130-150

As the pileup of the files inside these runs differ from each other, we can learn the muon and track multiplicity, as well as the event size, as a function of pileup, and therefore make an estimation of the event size at Run-4.

To process these files, first make sparse checkout of Athena 25.0.69, and build it into a folder called 'build'. Your sparse checkout should include:
- Trigger/TriggerCommon/TriggerEDMConfig
- Trigger/TriggerCommon/TriggerJobOpts
- Trigger/TriggerCommon/TriggerMenuMT

Then, in TriggerMenuMT/python/HLT/Menu, you should customise your own trigger menu by modifying the file ```Physics_pp_run3_v1.py```, which is the file set by default to be the trigger menu. For muon event size estimates, remove all the chains in this menu, and keep only one muon chain

submit the jobs to the grid by:
```
source setup.sh
cd gridSubmit
bash submit_grid_raw.sh \
  --version vXX \
  --input-version XX \
  --lumi-lookup lumi_lookup_combined.csv

```
