## Project setup

From this directory, run the following command to download and execute the script to build SQUEAK:

```bash
wget -qO- https://cernbox.cern.ch/remote.php/dav/public-files/cLIRGuSkfSxCR0n/build.sh | bash -s -- --tutorial
```

This directory uses SQUEAK to take MC samples, emulate the HLT on them, and dump the events that pass into nTuples.

Once the above command has finished running, you should move the folder ```ntup``` into ```TrigAna/run```. ```ntup``` contains
- a bin file, ```Muons```, that describes the muon attributes that get saved to the nTuple, and
- a ```share``` folder that contains the emulated trigger chain that we are interested in (```HLT_2mu4_PhysicsTLA_L12MU8F```, same as when we reprocess our data with the HLT) in ```emu.yaml``` along with the configuration of the chain in ```chains.yaml```, which determines which containers the trigger emulation uses to place cuts on transverse momentum, in our case ```HLT_MuonL2SAInfo``` for L1 and ```HLT_MuonsCB_RoI``` for the HLT.

# Run nTuples
Once everything is set up, test it locally:
```
source setup.sh
cd localTest
rucio download mc21_14TeV:DAOD_JETM42.48089457._000061.pool.root.1
bash run_binary.sh
```

If this works, submit the jobs to the grid:
```
source setup.sh
cd submitGrid
./run_grid.sh --grid   --version vPU140_XX   --samples mc21_14TeV.801165.Py8EG_A14NNPDF23LO_jj_JZ0.deriv.DAOD_JETM42.e8557_s4422_r17017_p7139   --nevents -1
```
