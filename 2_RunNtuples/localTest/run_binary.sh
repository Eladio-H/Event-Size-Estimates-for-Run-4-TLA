# Get path to this very script
PATH2SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"; cd ./out/ >/dev/null 2>&1 && pwd )"

# Name of the binary , for example the name of the example ntuple binary
BIN_NAME=Muons
CONFIG_FILE="../TrigAna/run/ntup/share/emu.yaml"

# Output directories
OUT_NAME=${BIN_NAME//-/_}
OUTPUT_DIR=out
mkdir -p ${OUTPUT_DIR}

# Make a clear run
if [ -d ${OUTPUT_DIR} ]; then
  rm ${OUTPUT_DIR}/* 2>/dev/null
fi

#===================================
#
# The samples we want to run over
#
#===================================

SAMPLES=/mc21_14TeV/DAOD_JETM42.48089457._000061.pool.root.1

#===================================
#
# Run the binary
#
#===================================

# Run the analysis, -1 for all events in the sample
\../TrigAna/run/ntup/bin/${BIN_NAME} \
  ${SAMPLES} \
  --run-dir ${OUTPUT_DIR} \
  --run-config ${CONFIG_FILE} \
  --outFile output21.root \
  -l DEBUG \
 2>&1 | tee ${OUTPUT_DIR}/log_${OUT_NAME}.txt
