python ../gridSubmit/rerun_and_extract.py data25_13p6TeV.00507758.physics_Main.daq.RAW._lb0838._SFO-20._0001.data --lumi-lookup ../gridSubmit/lumi_lookup_combined.csv > run_test.log 2>&1
rm athenaHLT:01.err
rm athenaHLT:01.out
rm BunchGroupSet_Physics_pp_run3_v1_25.0.69.json
rm expert-monitoring.root
rm hashes2string.txt
rm HLTJobOptions.db.json
rm HLTJobOptions.json
rm HLTJobOptions.pkl
rm HLTMenu_Physics_pp_run3_v1_25.0.69.json
rm HLTMonitoring_Physics_pp_run3_v1_25.0.69.json
rm HLTPrescalesSet_Physics_pp_run3_v1_25.0.69.json
rm L1Menu_Physics_pp_run3_v1_25.0.69.json
rm L1PrescalesSet_Physics_pp_run3_v1_25.0.69.json
rm -rf athenaHLT_workers
