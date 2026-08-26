#!/usr/bin/env bash
#
# Grid version of the rerunHLT + trigbs_extractStream workflow (no
# dumpRAW.py, no CSV output). This submits a SINGLE pathena job against
# the consolidated raw_selection dataset built by
# select_files_and_make_datasets.py (which now mixes physics_Main and
# EnhancedBias RAW files across all 5 runs into one Rucio dataset),
# using rerun_and_extract.py as the transformation script -- the same
# script used for the local download_and_extract.sh workflow, since it
# only needs itself + rerunHLT.py staged in the job sandbox (extFile
# handles that here, just like it did for run_analysis.py before).
#
# Output is whatever *.data file(s) survive rerun_and_extract.py -- i.e.
# the extracted, compressed-size TLA RAW files -- registered into the
# output dataset instead of CSVs.
#
# Usage:
#   ./submit_grid_raw.sh --version v1 --input-version 3 --trigger HLT_2mu4_PhysicsTLA_L12MU8F
#
set -euo pipefail

VERSION=""
INPUT_VERSION=""
TRIGGER=""
CATEGORY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --input-version)
            INPUT_VERSION="$2"
            shift 2
            ;;
        --trigger)
            TRIGGER="$2"
            shift 2
            ;;
        --lumi-lookup)
            LUMI_LOOKUP="$2"
            shift 2
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

if [[ -z "${VERSION}" || -z "${INPUT_VERSION}" ]]; then
    echo "Usage: $0 --version <VERSION> --input-version <INPUT_DATASET_VERSION> [--trigger <TRIGGER_NAME(S)>]"
    exit 1
fi

if [[ -z "${LUMI_LOOKUP}" ]]; then
    echo "Usage: $0 ... --lumi-lookup <file>"
    exit 1
fi


# This is the single consolidated dataset produced by
# select_files_and_make_datasets.py <INPUT_VERSION> -- e.g. v6 holds all
# 5 runs (physics_Main + EnhancedBias) together, no per-run split.
python select_lb.py ${INPUT_VERSION}
INDS="user.${USER}:user.${USER}.raw_selection.v${INPUT_VERSION}"
#INDS="user.ehossein:user.ehossein.raw_selection.v6"

echo "=================================================="
echo "Version       : ${VERSION}"
echo "Input dataset : ${INDS}"
echo "Trigger       : ${TRIGGER}"
echo "=================================================="

TRF_CMD="python rerun_and_extract.py %IN --lumi-lookup ${LUMI_LOOKUP}"
if [[ -n "${TRIGGER}" ]]; then
    TRF_CMD="${TRF_CMD} --trigger ${TRIGGER}"
fi

pathena \
  --trf "${TRF_CMD}" \
  --extFile="rerun_and_extract.py,rerunHLT.py,dumpRAW.py,lumi_lookup_combined.csv" \
  --inDS "${INDS}" \
  --outDS "user.${USER}.CompressedRAW_and_ByContainer_MuonEventSize_TLA.${VERSION}" \
  --extOutFile="*.data,*.csv" \
  --noEmail \
  --nFilesPerJob 5 \
  --nThreads 8