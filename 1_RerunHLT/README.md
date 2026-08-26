## Project setup
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

Then, in TriggerMenuMT/python/HLT/Menu, you should customise your own trigger menu by modifying the file ```Physics_pp_run3_v1.py```, which is the file set by default to be the trigger menu. For muon event size estimates, remove all the chains in this menu, and keep only one muon chain:

```
chains['Muon'] += [
    ChainProp(name='HLT_2mu4_PhysicsTLA_L12MU8F', l1SeedThresholds=['MU8F'], stream=['TLA'], groups=PrimaryL1MuGroup+MultiMuonGroup),
]
```

Additionally, add the TLA muons and their tracks to the EDM for the TLA stream by modifying, in TriggerEDMConfig/python/TriggerEDMRun3.py, the TLA muons to add 'PhysicsTLA' to the tags alongside BS and ESD. This applies to the following containers at the minimum:
- xAOD::MuonContainer#HLT_MuonsCB_RoI_TLA
- xAOD::MuonAuxContainer#HLT_MuonsCB_RoI_TLAAux.
- xAOD::TrackParticleContainer#HLT_IDTrack_Muon_IDTrig
- xAOD::TrackParticleAuxContainer#HLT_IDTrack_Muon_IDTrigAux.

If you want more containers in your EDM for the TLA stream, you can always search for them in this file and add them.

Once you have customised your trigger menu and EDM, you can test locally by downloading a file from rucio into localTest:
```
source setup.sh
cd localTest
rucio download data25_13p6TeV:data25_13p6TeV.00507758.physics_Main.daq.RAW._lb0838._SFO-20._0001.data
bash run_test.sh
```

If everything works, feel free to submit the job to the grid which processes all the files. Bear in mind that the file selection algorithm calls the files on the grid for you, but if you wish to implement your own file selector or would like to change the parameters (e.g. number of files saved), feel free to modify gridSubmit/select_lb.py. The moment you run the grid submission, a rucio dataset is created for you under the ```--input-version``` input version, unless it already exists because it is not your first time running this code. In this event, it reuses the rucio dataset made previously. If you have modified the file selection process and wish to create a new, changed rucio dataset, just change the ```--input-version``` tag. In any case, it makes sense to just start with ```--input-version 1```, and keep that unless you want to change the file selection process.
```
source setup.sh
cd gridSubmit
bash submit_grid_raw.sh \
  --version vXX \
  --input-version XX \
  --lumi-lookup lumi_lookup_combined.csv
```
Note that there is no ```--trigger``` tag here because we have our own custom trigger menu with only one trigger, so specifying a trigger here is unnecessary.

## Workflow description
The process starts with fetching an input dataset. As explained above, this is either done by default for the first time, or if it is not your first time running, it reuses the rucio dataset created previously. These files are directed between the python files in ```gridSubmit/``` by ```gridSubmit/rerun_and_extract.py```. This file directs each input RAW file through the following workflow:
1. Reprocess file with athenaHLT.py (this is done by ```gridSubmit/rerunHLT.py```).
2. Extract the TLA stream out of the reprocessed file (this is done within ```gridSubmit/rerun_and_extract.py``` which calls ```trigbs_extractStream.py```.
3. Run ```gridSubmit/dumpRAW.py``` on this new file to dump all its contents into a csv file, and in this way be able to see container multiplicity.
4. Save the TLA-extracted-reprocessed RAW file (to be able to know event size) and the csv file (to be able to know container multiplicities)
   
