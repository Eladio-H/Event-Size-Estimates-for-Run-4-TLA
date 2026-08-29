## Plots setup
In order to generate your plots, you first need to download the results of the jobs you submitted to the grid. First, create the folders which the results will sit in. From this directory, run
```
mkdir data
cd data
mkdir compressed_RAW
mkdir csv
cd ..
mkdir mc
```

Wonderful. Now let's download the data relating to the jobs you submitted processing the RAW files. You want to check the name of the rucio directory the output files are held in. You can check this through
```
rucio list-dids user.YOUR_USER:*
```
If you have not changed the source code, the directories should be start with ```user.YOUR_USER.CompressedRAW_and_ByContainer_MuonEventSize_TLA.VERSION_TAG_YOU_USED```, but the above command is a way to check for sure.

Notice how there exist two output directories relating to this job: one ends in ```EXT0```, and one in ```EXT1```, e.g.
```user.ehossein.CompressedRAW_and_ByContainer_MuonEventSize_TLA.v1_EXT0```
```user.ehossein.CompressedRAW_and_ByContainer_MuonEventSize_TLA.v1_EXT1```

Crucially, the ```EXT0``` directory holds the reprocessed (with athenaHLT and then extracting the TLA stream from it) RAW files, and the ```EXT1``` directory holds the csv files in which we dump the contents of the reprocessed RAW files to learn the container multiplicities.

As such, to download the job results to the correct directory, run
```
cd compressed_RAW
rucio download user.[USER_TAG].CompressedRAW_and_ByContainer_MuonEventSize_TLA.v[VERSION_TAG]_EXT0
cd ../csv
rucio download user.[USER_TAG].CompressedRAW_and_ByContainer_MuonEventSize_TLA.[VERSION_TAG]_EXT1
```

Fantabulous. Now do the same to download the job you submitted to process the MC samples, but in the MC folder obviously. There is only one rucio directory this time, and you have checked its name, so now just run
```
cd ../../mc
rucio download user.ehossein:user.[USER_TAG].NGT2p7.mc21_14TeV.801165.Py8EG_jj_JZ0.deriv_JETM42.e8557_s4422_r17017_p7139.[VERSION_TAG]
```
(this is if you have not changed the source code to change the container name, and are using the same MC samples... otherwise just check your rucio DIDs and find the name there)

## Generate plots

Congratulations!! You have now downloaded the data you need to estimate event size for Run-4. Now, just open the notebook and run the cells one by one. Enjoy the ride :)
