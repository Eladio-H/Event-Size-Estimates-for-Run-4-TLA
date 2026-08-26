#!/usr/bin/env bash

# Get path to this very script
PATH2SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"; cd . >/dev/null 2>&1 && pwd )"
CURRENT_DIR="$(pwd)"

# Define bold formatting
BOLD="\e[1m"
RESET="\e[0m"
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

#===================================
#
# Configuration variables
#
#===================================

CONFIG_FILE="../TrigAna/run/ntup/share/emu.yaml"
BINARY_FILE="../TrigAna/run/ntup/bin/Muons"
SQUEAK_SRC_DIR="../TrigAna/source"
OUTDIR_DIR=${CURRENT_DIR}/out/job/$(date +"%Y%m%d_%H%M%S")

DEFAULT_SAMPLES=(
  "/data/tcritchl/SAMPLES/muons/jPsi/mc23_13p6TeV.800830.P8B_A14_CTEQ6L1_SPS_2Jpsi_2mu3p5mu2p5mu1p5.deriv.DAOD_JETM42.e8542_s4422_r17017_p7139"
)

#===================================
#
# Global variables
#
#===================================

# Configuration variables
NEVENTS=-1
PARALLEL=""
GRID_MODE=""
LOGLEVEL="INFO"
VERSION_PREFIX=""
CUSTOM_SAMPLES=()

#===================================
#
# Function to read commandlines
# and modify global variables
#
#===================================

function get_args {

  # Help message function
  usage() {
    echo "Usage: ${0} [options]"
    echo ""
    echo "Options:"
    echo "  --nevents <num>   Set the number of events (default: -1)"
    echo "  --version <str>   Set the version prefix"
    echo "  --samples <list>  Add a custom sample (can be repeated)"
    echo "  --grid            Enable grid mode"
    echo "  --parallel        Enable parallel execution (locally)"
    echo "  --outdir <path>   Specify output directory"
    echo "  --binary <file>   Specify binary file"
    echo "  --config <file>   Specify config file"
    echo "  --loglevel <lvl>  Set log level"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Example call:"
    echo "  ./run-binary.sh --grid --binary path/to/binary --config path/to/cfg.yaml --nevents -1 --version MyAnalysis.ANA00p00.v00p00"
    echo ""
  }

  # Parse arguments
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --nevents)
          NEVENTS="${2}"
          shift
          ;;
      --outdir)
          OUTDIR_DIR="${2}"
          shift
          ;;
      --binary)
          BINARY_FILE="${2}"
          shift
          ;;
      --config)
          CONFIG_FILE="${2}"
          shift
          ;;
      --version)
          VERSION_PREFIX="${2}"
          shift
          ;;
      --loglevel)
          LOGLEVEL="${2}"
          shift
          ;;
      --samples)
          CUSTOM_SAMPLES+=("${2}")
          shift
          ;;
      --grid)
          GRID_MODE=1
          ;;
      --parallel)
          PARALLEL=1
          ;;
      -h|--help)
          usage
          exit 0
          ;;
      *)
      echo "Unknown parameter passed: ${1}"
      usage
      exit 1
      ;;
    esac
    shift
  done

  # Use custom samples if provided, otherwise use default
  if [[ ${#CUSTOM_SAMPLES[@]} -ne 0 ]]; then
    SAMPLES=("${CUSTOM_SAMPLES[@]}")
  else
    SAMPLES=("${DEFAULT_SAMPLES[@]}")
  fi
}

#===================================
#
# Define main caller function to
# run stuff locally
#
#===================================

function run::locally {

  local _SAMPLE=${1}

  #===================================
  # Run configuration
  #===================================

  # Extract the part of the path after "samples/"
  RELATIVE_DIR=$(echo "${SAMPLE}" | sed 's|.*samples/||')
  # Extract the "PROCESS" from the first part of the relative path
  PROCESS=$(echo "${RELATIVE_DIR}" | cut -d'/' -f1)
  # This will be the name prefix
  PREFIX=${PROCESS}

  # Handle the case when "dihiggs" is the process
  if [[ "${PROCESS}" == "dihiggs" ]]; then
    SUBPROCESS=$(echo "${RELATIVE_DIR}" | cut -d'/' -f2)
    LAYOUT=$(echo "${RELATIVE_DIR}" | grep -o 'l1cvv[0-9]*cv[0-9]*' | head -n 1)
    PREFIX="${PREFIX}_${SUBPROCESS}_${LAYOUT}"
    DIR="${PROCESS}/${SUBPROCESS}/${LAYOUT}"
  else
    DIR="${PROCESS}"
  fi

  # Set the run dir
  RUNDIR_DIR=${OUTDIR_DIR}/${DIR} && mkdir -p "${RUNDIR_DIR}"

  # Get the base name
  DSID=$(echo $(basename "${_SAMPLE}") | cut -d'.' -f2)

  #===================================
  # Print config
  #===================================

  echo "###################################################"
  echo "################## Configuration ##################"
  echo "BINARY:"
  echo -e " - ${BOLD}${BINARY_FILE}${RESET}"
  echo "CONFIG:"
  echo -e " - ${BOLD}${CONFIG_FILE}${RESET}"
  echo "DSID:"
  echo -e " - ${BOLD}${DSID}${RESET}"
  echo "SAMPLES:"
  echo -e " - ${BOLD}${_SAMPLE}${RESET}"
  echo "PROCESS:"
  echo -e " - ${BOLD}${PROCESS}${RESET}"
  echo "PREFIX:"
  echo -e " - ${BOLD}${PREFIX}${RESET}"
  echo "RUNDIR:"
  echo -e " - ${BOLD}${RUNDIR_DIR}${RESET}"
  echo "IS_SIGNAL:"
  echo -e " - ${BOLD}${IS_SIGNAL}${RESET}"
  echo "NEVENTS:"
  echo -e " - ${BOLD}${NEVENTS}${RESET}"
  echo "###################################################"

  #===================================
  # Make sample files & run binary
  #===================================

  # Sample file
  FILELIST="${RUNDIR_DIR}/filelist_${DSID}.txt"

  # Find matching files and store them in the unique file
  find "${_SAMPLE}" -type f -name "*.root.1" > ${FILELIST}

  # Run the binary
  ${BINARY_FILE} ${FILELIST} \
    --run-dir ${RUNDIR_DIR} \
    --run-config ${CONFIG_FILE} \
    --loglevel ${LOGLEVEL} \
    --evtMax  -1\
    --isSignal ${IS_SIGNAL} \
    --outFile "${RUNDIR_DIR}/output.${DSID}.root" \
    > >(tee ${RUNDIR_DIR}/log_${DSID}.txt) 2>&1
}


function run::grid {

  local _CONTAINERS=${1}

  # Check if this is a path
  if [[ "${_CONTAINERS}" == *"/"* ]]; then
    _CONTAINERS=$(basename "${_CONTAINERS}")
  fi

  # Build the name of the output container
  GRID_NAME_PATTERN="user.${USER}.NGT2p7.${_CONTAINERS}.__VERSION__"

  # Update the grid name pattern
  GRID_NAME_PATTERN=${GRID_NAME_PATTERN/__VERSION__/${VERSION_PREFIX}}

  # Reduce size of grid name
  for PATTERN in _novhh_5fs .recon .AOD .DAOD _A14NNPDF23LO .e8557_s4422_r16130; do
    GRID_NAME_PATTERN=${GRID_NAME_PATTERN/${PATTERN}/}
  done

  # Print config
  echo "###################################################"
  echo "################## Configuration ##################"
  echo "GRID CONTAINER NAME:"
  echo -e " - ${BOLD}${GRID_NAME_PATTERN}${RESET}"
  echo "BINARY:"
  echo -e " - ${BOLD}${BINARY_FILE}${RESET}"
  echo "CONFIG:"
  echo -e " - ${BOLD}${CONFIG_FILE}${RESET}"
  echo "CONTAINER(S):"
  echo -e " - ${BOLD}${_CONTAINERS}${RESET}"
  echo "IS_SIGNAL:"
  echo -e " - ${BOLD}${IS_SIGNAL}${RESET}"
  echo "NEVENTS:"
  echo -e " - ${BOLD}${NEVENTS}${RESET}"
  echo "###################################################"

#  # Send to grid
#  echo "[INFO] Sending job to GRID"
#  pathena \
#       --trf "python ${BINARY_FILE} %%IN \
#       --evtMax ${NEVENTS} \
#       --isSignal ${IS_SIGNAL} \
#       --run-config ${CONFIG_FILE} \
#       --loglevel ${LOGLEVEL} \
#       --outFile %OUT.root" \
#    --extFile="bin/*,share/*" \
#    --inDS ${_CONTAINERS} \
#    --outDS ${GRID_NAME_PATTERN} \
#    --noEmail \
#    --mergeOutput
#}

  # Send to grid
  echo "[INFO] Sending job to GRID"
  pathena \
    --trf "bash -lc '
      echo \"[INFO] grid PWD=\$PWD\";
      echo \"[INFO] contents:\"; ls -la;

      # Make shipped python packages importable
      export PYTHONPATH=\$PWD/source:\$PYTHONPATH;

      # Fail fast if SQUEAK is missing
      python -c \"import SQUEAK; print(\\\"[INFO] SQUEAK=\\\", SQUEAK.__file__)\" || exit \$?;

      python ${BINARY_FILE} %IN \
        --evtMax ${NEVENTS} \
        --isSignal ${IS_SIGNAL} \
        --run-config ${CONFIG_FILE} \
        --loglevel ${LOGLEVEL} \
        --outFile %OUT.root
    '" \
    --extFile="bin/*,share/*,${SQUEAK_SRC_DIR}/SQUEAK/*" \
    --inDS ${_CONTAINERS} \
    --outDS ${GRID_NAME_PATTERN} \
    --noEmail \
    --mergeOutput
}
#===================================
#
# Define main caller function to
#
#===================================

# Get the commandline arguments
get_args $@

# Iterate over each sample
echo "[INFO] Running over samples"
for SAMPLE in "${SAMPLES[@]}"; do

  echo " - ${SAMPLE}"

  # Handle the case when "dihiggs" is the process
  if [[ "${SAMPLE}" == *"dijet"* ]]; then
    IS_SIGNAL=0
  else
    IS_SIGNAL=1
  fi

  # Run the binary locally or on the grid
  if [ -z "${GRID_MODE}" ]; then
    if [[ ! -z "${PARALLEL}" ]]; then
      run::locally "${SAMPLE}" &
    else
      run::locally "${SAMPLE}"
    fi
  else
    run::grid "${SAMPLE}"
  fi
done