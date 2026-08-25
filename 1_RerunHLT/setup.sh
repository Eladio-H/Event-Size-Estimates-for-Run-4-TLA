setupATLAS
asetup Athena,25.0.69,here
source build/x86_64-el9-gcc15-opt/setup.sh
voms-proxy-init -voms atlas
lsetup rucio panda
