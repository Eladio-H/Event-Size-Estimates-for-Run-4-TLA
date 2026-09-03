#!/usr/bin/env python3
import os, re, csv
import eformat

DATA_DIR = "data"
OUT_CSV = "event_counts.csv"

def classify(folder_name):
    if "jet_muon_Trig" in folder_name:
        return "jet_muon_Trig"
    if "jet_Trig" in folder_name:
        return "jet_Trig"
    if "muon_Trig" in folder_name:
        return "muon_Trig"
    return None

def get_run(folder_name, fname=None):
    # First try the folder-name AMI-tag style token (rNNNNN)
    for tok in folder_name.split('.'):
        if tok.startswith('r') and tok[1:].isdigit():
            return tok
    # Fall back to pulling the 8-digit run number straight out of the filename
    if fname is not None:
        m = re.search(r"\.(\d{8})\.", fname)
        if m:
            return m.group(1)
    return None

def count_events(path):
    try:
        r = eformat.istream([path])
        return sum(1 for _ in r)
    except Exception as e:
        print(f"  [WARN] could not read events from {path}: {e}")
        return None

rows = []
for folder in sorted(os.listdir(DATA_DIR)):
    folder_path = os.path.join(DATA_DIR, folder)
    if not os.path.isdir(folder_path):
        continue
    trig = classify(folder)
    if trig is None:
        continue
    for fname in sorted(os.listdir(folder_path)):
        fpath = os.path.join(folder_path, fname)
        if not os.path.isfile(fpath) or fname.endswith(".tgz"):
            continue
        run = get_run(folder, fname)
        size = os.path.getsize(fpath)
        nevents = count_events(fpath)
        if nevents is None:
            continue  # skip files eformat couldn't parse rather than crash
        rows.append([folder, run, trig, fpath, size, nevents])
        print(folder, fname, size, nevents)

with open(OUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["folder", "run", "trigger", "file", "size_bytes", "nevents"])
    writer.writerows(rows)

print(f"Wrote {OUT_CSV}")