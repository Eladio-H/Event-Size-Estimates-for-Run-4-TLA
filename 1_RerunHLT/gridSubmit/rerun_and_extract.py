#!/usr/bin/env python3
"""
rerun_and_extract.py

Per RAW file:
  1. rerunHLT.py  <raw> --trigger <TRIGGER> --output <TAG>   -> HLT output
  2. trigbs_extractStream.py -s TLA <hlt_output>              -> extracted RAW
  3. dumpRAW.py <extracted_file> --lumi-lookup <csv> [--filter <regex>]
     -> CSV dump of container sizes/multiplicities for the extracted RAW.
  4. Delete the ORIGINAL input RAW file (once the HLT rerun has produced
     its output -- happens regardless of what trigbs_extractStream.py
     does downstream).
  5. Delete the intermediate HLT output file (whether trigbs_extractStream.py
     succeeds or finds zero events for the stream).
  6. Keep BOTH the extracted TLA RAW file and its CSV dump, under whatever
     filename trigbs_extractStream.py/dumpRAW.py give them, renamed with
     a FINAL_TAG/CSV_TAG suffix.

This mirrors the rerunHLT/trigbs/dumpRAW block in run_analysis.py, with
the input RAW and intermediate HLT output both actually deleted (not just
renamed) instead of kept around. Both the RAW and CSV outputs are kept
since condor can output both.

IMPORTANT: derived filenames (hlt_output, extracted_file, final_kept)
now encode the input file's SFO tag and sequence number, in addition to
project/run/LB. Multiple input RAW files can share the same run+LB but
differ only in SFO unit (e.g. _SFO-11 vs _SFO-12) or sequence number
(e.g. _0001 vs _0002) -- if the derived names only used project/run/LB,
those files would silently overwrite each other's outputs.

NOTE on raw_extracted_file: trigbs_extractStream.py's own output naming
is not fully predictable from the input filename (it drops/rewrites parts
of hlt_output's tag in ways that have changed run to run). Rather than
guess, we parse the actual filename it reports from its own log output
(a line like "Output file = ./foo.data"). That line is emitted via
Python's `logging` module, which defaults to stderr, so we search both
stdout and stderr.

Usage:
    python rerun_and_extract.py <raw1>,<raw2>,... --lumi-lookup <csv> [--trigger <chain>] [--filter <regex>]
"""

import argparse
import os
import re
import subprocess

# rerunHLT.py lives next to this script, not necessarily in the current
# working directory (we cd into each dataset's own processing folder
# before running this, so a bare relative name won't resolve).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RERUN_HLT = os.path.join(SCRIPT_DIR, "rerunHLT.py")
DUMP_RAW = os.path.join(SCRIPT_DIR, "dumpRAW.py")

OUTPUT_TAG = "rerun.RAW"
HLT_TAG = "athenaHLT"
FINAL_TAG = f"{HLT_TAG}_TLAextracted"
CSV_TAG = "AOD_container_sizes"

# Captures project_tag, run_number, lb_number, sfo_tag (e.g. "11", "ALL"),
# and sequence number (e.g. "0001", "0002"). The SFO tag and sequence are
# what previously got dropped -- carrying them through into the derived
# filenames is what prevents same-LB-different-SFO/sequence files from
# colliding.
INPUT_PATTERN = re.compile(r"^(.+?)\.00(\d+)\..*?_lb(\d+)\._SFO-(\w+)\._(\d+)\.")

OUTPUT_FILE_RE = re.compile(r"Output file\s*=\s*(\S+)")


def parse_input_filename(input_file):
    """Extract project_tag, run_number, lb_number, sfo_tag, seq_number."""
    input_basename = os.path.basename(input_file)
    m = INPUT_PATTERN.match(input_basename)
    if not m:
        raise RuntimeError(f"Could not parse project/run/lb/sfo/sequence from input filename: {input_basename}")
    return m.groups()


def remove_if_exists(path, label):
    if os.path.isfile(path):
        os.remove(path)
        print(f"[INFO] {label}: {path}")


def process_one_file(input_file, args):
    print(f"[INFO] ---- Processing: {input_file} ----")

    project_tag, run_number, lb_number, sfo_tag, seq_number = parse_input_filename(input_file)

    # Unique tag for this specific input file's LB/SFO-unit/sequence
    # combination, folded into extracted_file below so that two inputs
    # differing only in SFO unit or sequence don't collide in the final
    # kept output.
    unit_tag = f"_SFO-{sfo_tag}._{seq_number}"

    # Raw athenaHLT output (input to extraction). rerunHLT.py names this
    # file itself, from project/run/LB only -- it does NOT know about SFO
    # unit or sequence number, so unit_tag must NOT appear here. This
    # intermediate file is deleted before the next input is processed, so
    # a same-named collision across inputs in one job is harmless -- only
    # extracted_file (below) needs to stay unique.
    hlt_output = (
        f"{project_tag}.00{run_number}.unknown_SingleStream.daq.RAW."
        f"_lb{lb_number}._HLTMPPy_{OUTPUT_TAG}._0001.data"
    )

    # Extracted TLA stream file -- this is the one we keep, renamed with
    # unit_tag so two inputs sharing the same run+LB but differing only in
    # SFO unit or sequence don't collide in the final kept output.
    extracted_file = (
        f"{project_tag}.00{run_number}.physics_TLA.daq.RAW."
        f"_lb{lb_number}.{unit_tag}._athenaHLT._0001.data"
    )

    # Clear any stale outputs from a previous/failed run so both
    # rerunHLT.py and trigbs_extractStream.py always write to _0001.
    remove_if_exists(hlt_output, "Removed stale file before rerun")
    remove_if_exists(extracted_file, "Removed stale file before rerun")

    if not os.path.isfile(RERUN_HLT):
        raise RuntimeError(f"rerunHLT.py not found next to this script: {RERUN_HLT}")

    cmd = ["python", RERUN_HLT, input_file, "--output", OUTPUT_TAG]
    if args.trigger:
        cmd += ["--trigger", args.trigger]

    subprocess.run(cmd, check=True)

    if not os.path.isfile(hlt_output):
        raise RuntimeError(f"Expected HLT output file not found: {hlt_output}")

    # Input RAW is no longer needed once the HLT rerun has produced its
    # output, regardless of what happens downstream.
    os.remove(input_file)
    print(f"[INFO] Deleted original input RAW file: {input_file}")

    try:
        result = subprocess.run(
            ["trigbs_extractStream.py", "-s", "TLA", hlt_output],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[WARN] trigbs_extractStream.py returned exit code {e.returncode} "
              f"for {hlt_output} -- likely zero events selected for this stream. "
              f"Skipping {input_file}.")
        print(e.stdout)
        print(e.stderr)
        remove_if_exists(hlt_output, "Deleted intermediate HLT output file")
        return

    # trigbs_extractStream.py logs via Python's `logging` module, which
    # defaults to stderr -- so search both streams for the actual output
    # filename rather than assuming which stream it lands on.
    combined_output = (result.stdout or "") + (result.stderr or "")
    m_out = OUTPUT_FILE_RE.search(combined_output)
    if not m_out:
        print(f"[DEBUG] trigbs_extractStream.py stdout+stderr for {hlt_output}:\n---\n{combined_output}\n---")
        raise RuntimeError(
            f"Could not find 'Output file = ...' line in trigbs_extractStream.py output for {hlt_output}"
        )

    raw_extracted_file = m_out.group(1)
    if raw_extracted_file.startswith("./"):
        raw_extracted_file = raw_extracted_file[2:]

    if not os.path.isfile(raw_extracted_file):
        raise RuntimeError(f"Expected extracted TLA file not found: {raw_extracted_file}")

    # Rename to the unit-tagged name immediately -- this is what actually
    # prevents same-LB-different-SFO/sequence inputs from colliding.
    os.rename(raw_extracted_file, extracted_file)
    print(f"[INFO] Renamed extracted TLA file: {raw_extracted_file} -> {extracted_file}")

    # Intermediate HLT output is no longer needed once extraction has
    # succeeded -- only the extracted TLA RAW file gets kept.
    remove_if_exists(hlt_output, "Deleted intermediate HLT output file")

    dump_cmd = ["python", DUMP_RAW, extracted_file, "--lumi-lookup", args.lumi_lookup]
    if args.filter:
        dump_cmd += ["--filter", args.filter]

    subprocess.run(dump_cmd, check=True)

    output_csv = extracted_file + ".csv"
    if not os.path.isfile(output_csv):
        raise RuntimeError(f"Expected CSV output not found: {output_csv}")

    print(f"[INFO] Wrote container CSV: {output_csv}")
    print(f"[INFO] Kept extracted RAW file: {extracted_file}")

    # Final RAW: tag goes BEFORE .data so it still matches "*.data" on the grid.
    base, ext = extracted_file.rsplit(".", 1)  # ext == "data"
    final_kept = f"{base}.{FINAL_TAG}.{ext}"
    os.rename(extracted_file, final_kept)
    print(f"[INFO] Renamed final extracted RAW: {extracted_file} -> {final_kept}")

    # CSV: same idea, tag before .csv so "*.csv" still matches.
    base, ext = output_csv.rsplit(".", 1)  # ext == "csv"
    csv_kept = f"{base}.{CSV_TAG}.{ext}"
    os.rename(output_csv, csv_kept)
    print(f"[INFO] Renamed CSV: {output_csv} -> {csv_kept}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rawfiles", help="Comma-separated list of input RAW files")
    parser.add_argument("--trigger", default=None)
    parser.add_argument("--filter", default=None, help="Regex filter on container names, passed to dumpRAW.py")
    parser.add_argument("--lumi-lookup", required=True, help="Lumi lookup CSV, passed to dumpRAW.py")
    args = parser.parse_args()

    input_files = [f.strip() for f in args.rawfiles.split(",") if f.strip()]

    for input_file in input_files:
        process_one_file(input_file, args)

    print("[INFO] All files processed.")


if __name__ == "__main__":
    main()