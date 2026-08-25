#!/usr/bin/env python3

import argparse
import csv
import os
import re
import subprocess
import sys

parser = argparse.ArgumentParser(
    description="Extract container sizes and multiplicities from RAW files"
)

parser.add_argument(
    "rawfile",
    help="RAW file"
)

parser.add_argument(
    "-n",
    "--events",
    type=int,
    default=-1,
    help="Number of events to process (-1 = all)"
)

parser.add_argument(
    "--filter",
    default=None,
    help="Regex filter on container names (e.g. Muon)"
)

parser.add_argument(
    "--lumi-lookup",
    default=None,
    help="CSV file with run_number, lb, inst_lumi_ub_s, collbunches, mu columns"
)

args = parser.parse_args()

fname = os.path.basename(args.rawfile)

m_lb = re.search(r"_lb(\d+)", fname)
lb = m_lb.group(1) if m_lb else "unknown"

output_csv = fname + ".csv"

print(f"[INFO] Input file  : {fname}")
print(f"[INFO] LB          : {lb}")
print(f"[INFO] Output CSV  : {output_csv}")

# Here I am getting the run number from the filename using it's specific format.
# Strip the zeros because th combined lumi lookup file uses the run number without leading zeros.
m_run = re.search(r"\.00(\d+)\.", fname)
run = m_run.group(1) if m_run else "unknown"

lumi_map = {}
if args.lumi_lookup and os.path.exists(args.lumi_lookup):
    with open(args.lumi_lookup) as f:
        for row in csv.DictReader(f):
            lumi_map[(int(row["run"]), int(row["lb"]))] = {
                "inst_lumi_ub_s": float(row["inst_lumi_ub_s"]),
                "collbunches":    int(row["collbunches"]),
                "mu":             float(row["mu"]),
            }
    print(f"[INFO] Loaded lumi for {len(lumi_map)} LBs")
else:
    print("[WARN] No lumi lookup file provided or file not found, lumi columns will be -1")

# Changed this to look up run number as well
run_int = int(run) if run != "unknown" else -1
lb_int = int(lb) if lb != "unknown" else -1
lb_info = lumi_map.get((run_int, lb_int), {
    "inst_lumi_ub_s": -1.0,
    "collbunches":    -1,
    "mu":             -1.0,
})

print(f"[INFO] inst_lumi   : {lb_info['inst_lumi_ub_s']}")
print(f"[INFO] collbunches : {lb_info['collbunches']}")
print(f"[INFO] mu          : {lb_info['mu']:.2f}" if lb_info['mu'] != -1.0 else "[INFO] mu          : n/a")

cmd = [
    "trigbs_dumpHLTContentInBS_run3.py",
    "--hltres",
    "--deserialize",
]

if args.events > 0:
    cmd.extend(["-n", str(args.events)])

cmd.append(args.rawfile)

print("[INFO] Running:")
print("       " + " ".join(cmd))

try:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
except subprocess.CalledProcessError as e:
    print("[ERROR] Command failed")
    print(e.stdout)
    sys.exit(1)

event_re = re.compile(
    r"=== Event:\s*(\d+)"
)

container_re = re.compile(
    r"----\s+(?P<container>.+?),\s+Size:\s+(?P<size>\d+)\s+bytes\s+\((?P<elements>\d+)\s+element"
)

name_filter = re.compile(args.filter) if args.filter else None

current_event = None
nrows = 0

with open(output_csv, "w", newline="") as fout:

    writer = csv.writer(fout)

    writer.writerow([
        "run_number",
        "lb",
        "file",
        "event",
        "container",
        "size_bytes",
        "elements",
        "inst_lumi_ub_s",
        "collbunches",
        "mu",
    ])

    for line in proc.stdout.splitlines():

        m_evt = event_re.search(line)
        if m_evt:
            current_event = int(m_evt.group(1))
            continue

        m = container_re.match(line)
        if not m:
            continue

        
        container = m.group("container")
        if name_filter and not name_filter.search(container):
            continue
        

        writer.writerow([
            run,
            lb,
            fname,
            current_event,
            container,
            int(m.group("size")),
            int(m.group("elements")),
            lb_info["inst_lumi_ub_s"],
            lb_info["collbunches"],
            lb_info["mu"],
        ])

        nrows += 1

print(f"[INFO] Wrote {nrows} rows to {output_csv}")
