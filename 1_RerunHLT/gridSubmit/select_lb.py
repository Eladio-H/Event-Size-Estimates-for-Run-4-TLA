import sys
import subprocess
import re
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

RUCIO_ACCOUNT = os.environ["USER"]
RUCIO_SCOPE = f"user.{RUCIO_ACCOUNT}"

# Version tag for the dataset/filelist, e.g. `python thisscript.py 3` -> v3.
# Defaults to v2 if not given.
VERSION = sys.argv[1] if len(sys.argv) > 1 else "2"

files = [
    "lumi_lookup_507671.csv",
    "lumi_lookup_507733.csv",
    "lumi_lookup_507758.csv",
    "lumi_lookup_508073.csv",
    "lumi_lookup_509891.csv",
]

CATALOG_CACHE_DIR = "rucio_catalog_cache"
os.makedirs(CATALOG_CACHE_DIR, exist_ok=True)

# Runs with a special Enhanced Bias run to use instead of physics_Main.
HIGH_MU_RUNS = {508073, 509891}

# How many LBs (files) to pull per run. High-mu runs get 300, everything
# else gets the default of 20.
LBS_PER_RUN = {508073: 300, 509891: 300}
DEFAULT_LBS_PER_RUN = 20

# Per-run mu cut overrides. Runs not listed here use the default (mu > 20).
MU_CUT_OVERRIDES = {
    509891: 0,
    508073: 0,
}
DEFAULT_MU_CUT = 0

# Per-run LB ranges to exclude entirely (e.g. beam shutoff / dip regions),
# as a list of (low, high) tuples, inclusive. Runs not listed here have no
# exclusions applied.
LB_EXCLUDE_RANGES = {}

# Runs where, instead of down-selecting to n bins via mu-histogram binning,
# we just take every surviving LB (post mu-cut, post exclusion, post Rucio
# validation) as-is. Use this for runs where the mu cut already leaves few
# LBs and there's no point discarding any of them.
KEEP_ALL_LBS_RUNS = {509891}

# Single custom rucio dataset that holds everything (both streams), tagged
# with VERSION (e.g. .v2, .v3, ...).
DATASET = f"{RUCIO_SCOPE}:{RUCIO_SCOPE}.raw_selection.v{VERSION}"


def stream_for_run(run):
    """EnhancedBias for the two special high-mu runs, physics_Main otherwise."""
    return "physics_EnhancedBias" if run in HIGH_MU_RUNS else "physics_Main"


def raw_tag_for_run(run):
    """physics_Main files are tagged 'daq', EnhancedBias files are tagged 'merge'."""
    return "merge" if run in HIGH_MU_RUNS else "daq"


def file_suffix_for_run(run):
    """physics_Main files end in '.data', EnhancedBias (merge) files end in '.1'."""
    return "1" if run in HIGH_MU_RUNS else "data"


def exclude_lb_ranges(df, run):
    """Drop rows whose lb falls inside any excluded range for this run."""
    ranges = LB_EXCLUDE_RANGES.get(run)
    if not ranges:
        return df
    mask = pd.Series(False, index=df.index)
    for low, high in ranges:
        mask |= df["lb"].between(low, high)
    n_excluded = df["lb"][mask].nunique()
    if n_excluded:
        print(f"[INFO] Run {run}: excluding {n_excluded} LB(s) in ranges {ranges} "
              f"(e.g. beam shutoff)")
    return df[~mask]


def query_catalog_lines(run, force_refresh=False):
    """
    Query Rucio (or read from cache) for the raw `rucio list-dids` output
    lines for this run's RAW files, in whichever stream/tag applies to it.
    Caches to disk so repeated runs of this script don't re-hit Rucio.
    Returns None if the query fails and no cache is available.
    """
    stream = stream_for_run(run)
    raw_tag = raw_tag_for_run(run)
    # Keyed on stream *and* raw_tag so a change from daq->merge (or vice versa)
    # can't silently reuse a stale/empty catalog dump from before the change.
    cache_file = os.path.join(CATALOG_CACHE_DIR, f"catalog_{run}_{stream}_{raw_tag}.txt")

    if os.path.exists(cache_file) and not force_refresh:
        with open(cache_file) as fh:
            return fh.read().splitlines()

    print(f"[INFO] Querying Rucio catalog for run {run} ({stream})...")
    pattern = f"data25_13p6TeV:data25_13p6TeV.{run:08d}.{stream}.{raw_tag}.RAW.*"
    try:
        result = subprocess.run(
            ["rucio", "list-dids", "--filter", "type=file", pattern],
            capture_output=True, text=True, check=True, timeout=300,
        )
        with open(cache_file, "w") as fh:
            fh.write(result.stdout)
        return result.stdout.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[WARNING] Could not query Rucio for run {run} ({e}). "
              f"Proceeding WITHOUT catalog validation for this run — "
              f"selected files may not actually exist yet.")
        return None


def get_valid_lbs(run, force_refresh=False):
    """
    Which LBs actually have a registered _SFO-20._0001.<suffix> OR a
    _SFO-ALL._0001.<suffix> RAW file for this run. _SFO-ALL shows up for
    some LBs instead of the per-unit _SFO-20 file, so either one counts
    as "this LB has a usable file" for the normal (binned) selection path.
    Returns dict: lb (int) -> which SFO tag ("20" or "ALL") was found,
    preferring "20" if both exist for that LB. None if catalog unavailable.
    """
    suffix = file_suffix_for_run(run)
    lines = query_catalog_lines(run, force_refresh=force_refresh)
    if lines is None:
        return None

    valid_lbs = {}
    lb_pattern = re.compile(rf"_lb(\d+)\._SFO-(20|ALL)\._0001\.{re.escape(suffix)}\b")
    for line in lines:
        m = lb_pattern.search(line)
        if m:
            lb = int(m.group(1))
            tag = m.group(2)
            # Prefer SFO-20 over SFO-ALL if an LB happens to have both.
            if lb not in valid_lbs or tag == "20":
                valid_lbs[lb] = tag

    print(f"[INFO] Run {run}: {len(valid_lbs)} LBs have a valid "
          f"_SFO-20._0001.{suffix} or _SFO-ALL._0001.{suffix} file")
    return valid_lbs


def get_all_files_by_lb(run, force_refresh=False):
    """
    Every registered RAW file DID for this run, grouped by LB, regardless
    of which SFO subdetector unit or sequence number it's tagged with
    (e.g. _SFO-11._0001, _SFO-14._0003, _SFO-ALL._0001, ...). Used when we
    want extra files per LB for statistics rather than just one canonical
    file per LB.
    Returns dict: lb (int) -> list of full DIDs (scope:name), or None if
    the catalog query is unavailable.
    """
    suffix = file_suffix_for_run(run)
    lines = query_catalog_lines(run, force_refresh=force_refresh)
    if lines is None:
        return None

    files_by_lb = {}
    lb_pattern = re.compile(rf"_lb(\d+)\._SFO-(?:\d+|ALL)\._\d+\.{re.escape(suffix)}\b")
    for line in lines:
        m = lb_pattern.search(line)
        if not m:
            continue
        # First "|"-delimited cell in the table row is the DID itself.
        did = line.split("|")[1].strip() if "|" in line else line.strip()
        if not did:
            continue
        lb = int(m.group(1))
        files_by_lb.setdefault(lb, []).append(did)

    total_files = sum(len(v) for v in files_by_lb.values())
    print(f"[INFO] Run {run}: {len(files_by_lb)} LBs have {total_files} total registered "
          f"RAW file(s) across all SFO units/sequences")
    return files_by_lb


def round_robin_select(files_by_lb, n):
    """
    Pick up to n (lb, file_did) pairs from files_by_lb, cycling through
    LBs so that distinct LBs get covered first before any LB contributes
    a second (extra-statistics) file.
    """
    selected = []
    lbs = list(files_by_lb.keys())
    idx = {lb: 0 for lb in lbs}
    while len(selected) < n:
        progressed = False
        for lb in lbs:
            lst = files_by_lb[lb]
            i = idx[lb]
            if i < len(lst):
                selected.append((lb, lst[i]))
                idx[lb] += 1
                progressed = True
                if len(selected) >= n:
                    break
        if not progressed:
            break  # every available file across every LB has been used
    return selected


def ensure_rucio_dataset(dataset_did):
    """Create the rucio dataset if it doesn't already exist. Safe to call repeatedly."""
    try:
        subprocess.run(
            ["rucio", "add-dataset", dataset_did],
            capture_output=True, text=True, check=True, timeout=120,
        )
        print(f"[INFO] Created dataset {dataset_did}")
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "")
        if "already exists" in stderr.lower():
            print(f"[INFO] Dataset {dataset_did} already exists, reusing it")
        else:
            print(f"[WARNING] Could not create dataset {dataset_did}: {stderr.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[WARNING] Could not create dataset {dataset_did} ({e})")


def attach_files_to_dataset(dataset_did, file_dids):
    """Attach a batch of file DIDs to a rucio dataset."""
    if not file_dids:
        print(f"[INFO] No files to attach to {dataset_did}, skipping attach")
        return
    try:
        subprocess.run(
            ["rucio", "attach", dataset_did, *file_dids],
            capture_output=True, text=True, check=True, timeout=300,
        )
        print(f"[INFO] Attached {len(file_dids)} file(s) to {dataset_did}")
    except subprocess.CalledProcessError as e:
        print(f"[WARNING] Could not attach files to {dataset_did}: {(e.stderr or '').strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[WARNING] Could not attach files to {dataset_did} ({e})")


all_bin_centers = []
all_bin_counts = []
filelist_lines = []  # all selected files (both streams), goes into the single DATASET
skipped_lb_report = []  # track what we dropped, for a sanity check at the end

for f in files:
    run = int(f.split("_")[-1].replace(".csv", ""))
    stream = stream_for_run(run)
    raw_tag = raw_tag_for_run(run)
    suffix = file_suffix_for_run(run)
    n = LBS_PER_RUN.get(run, DEFAULT_LBS_PER_RUN)

    df = pd.read_csv(f)
    df["source"] = f

    df = exclude_lb_ranges(df, run)

    mu_cut = MU_CUT_OVERRIDES.get(run, DEFAULT_MU_CUT)
    print(f"[INFO] Run {run}: applying mu > {mu_cut} cut, requesting {n} LBs from {stream}")
    df = df[df["mu"] > mu_cut]

    valid_lbs = get_valid_lbs(run)

    if valid_lbs is not None:
        n_before = df["lb"].nunique()
        df = df[df["lb"].isin(valid_lbs)]
        n_after = df["lb"].nunique()
        if n_after < n_before:
            dropped = n_before - n_after
            print(f"[INFO] {f}: dropped {dropped} LB(s) with mu>{mu_cut} but no "
                  f"registered RAW file in Rucio")
            skipped_lb_report.append((run, dropped, n_before, n_after))

    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    if len(df) == 0:
        print(f"WARNING: no rows with mu > {mu_cut} (and a valid RAW file) in {f}, skipping")
        continue

    if run in KEEP_ALL_LBS_RUNS:
        kept_lbs = sorted(df["lb"].unique())
        all_files_by_lb = get_all_files_by_lb(run)

        if all_files_by_lb is None:
            # No catalog access at all: fall back to one canonical file per LB.
            files_by_lb = {
                lb: [f"data25_13p6TeV:data25_13p6TeV.{run:08d}.{stream}.{raw_tag}.RAW."
                     f"_lb{lb:04d}._SFO-20._0001.{suffix}"]
                for lb in kept_lbs
            }
        else:
            # Restrict to LBs that survived the mu cut/exclusion/validation,
            # and pull ALL registered files (any SFO unit, any sequence) for
            # those LBs so we can use extras as additional statistics.
            files_by_lb = {lb: all_files_by_lb[lb] for lb in kept_lbs if lb in all_files_by_lb}

        n_distinct_lbs = len(files_by_lb)
        n_total_files = sum(len(v) for v in files_by_lb.values())
        print(f"[INFO] Run {run}: {n_distinct_lbs} distinct LBs available with "
              f"{n_total_files} total files; requesting {n}")

        selected = round_robin_select(files_by_lb, n)
        if len(selected) < n:
            print(f"[WARNING] Run {run}: only {len(selected)}/{n} files available "
                  f"even after using every SFO/sequence variant per LB")

        for lb, did in selected:
            mu_val = df.loc[df["lb"] == lb, "mu"].iloc[0]
            all_bin_centers.append(mu_val)
            all_bin_counts.append(1)
            filelist_lines.append(did)

        print(f"Run {run}: added {len(selected)} file(s) "
              f"({n_distinct_lbs} distinct LBs, extras used for additional statistics)")
        continue

    # Increase total bins until we get exactly n non-empty ones (within this run)
    test_bins = n
    while True:
        counts, edges = np.histogram(df["mu"], bins=test_bins)
        if np.sum(counts > 0) >= n:
            break
        test_bins += 1
        if test_bins > 10_000:  # safety valve in case a run has < n distinct mu values
            print(f"WARNING: {f} cannot supply {n} non-empty bins "
                  f"(only {np.sum(counts > 0)} available); using what's there")
            break

    nonempty_mask = counts > 0
    nonempty_left = edges[:-1][nonempty_mask][:n]
    nonempty_right = edges[1:][nonempty_mask][:n]
    n_actual = len(nonempty_left)
    if n_actual < n:
        print(f"WARNING: {f} only yielded {n_actual}/{n} bins")

    df["bin"] = -1
    for i, (left, right) in enumerate(zip(nonempty_left, nonempty_right)):
        mask = (df["mu"] >= left) & (df["mu"] < right)
        df.loc[mask, "bin"] = i

    bin_centers = 0.5 * (nonempty_left + nonempty_right)
    bin_counts = [len(df[df["bin"] == i]) for i in range(n_actual)]
    all_bin_centers.extend(bin_centers)
    all_bin_counts.extend(bin_counts)

    for i in range(n_actual):
        bin_df = df[df["bin"] == i][["source", "lb", "mu"]]
        contents = bin_df.values.tolist()
        if contents:
            source, lb, mu = contents[0]
            sfo_tag = valid_lbs.get(lb, "20") if valid_lbs is not None else "20"
            filename = (
                f"data25_13p6TeV:data25_13p6TeV."
                f"{run:08d}."
                f"{stream}.{raw_tag}.RAW."
                f"_lb{lb:04d}."
                f"_SFO-{sfo_tag}._0001.{suffix}"
            )
            filelist_lines.append(filename)
            print(f"Run {run}, bin {i} first entry: {contents[0]}")

# Plot (pooled across runs just for visualization)
plt.plot(all_bin_centers, all_bin_counts, 'o', markersize=4)
plt.xlabel("mu")
plt.ylabel("Count")
plt.title("mu distribution (per-run binning)")
plt.tight_layout()
plt.savefig("mu_histogram.png", dpi=150)
plt.show()

# Write filelist
filelist_name = f"filelist_v{VERSION}.txt"
with open(filelist_name, "w") as out:
    for line in filelist_lines:
        out.write(line + "\n")

print(f"\nWritten {len(filelist_lines)} filenames to {filelist_name} "
      f"(runs {sorted(HIGH_MU_RUNS)} @ {max(LBS_PER_RUN.values())} LBs each from EnhancedBias, "
      f"remaining runs @ {DEFAULT_LBS_PER_RUN} LBs each from physics_Main)")

# --- Create/populate the single custom rucio dataset (*.vN) ---
print("\n=== Creating/populating rucio dataset ===")
ensure_rucio_dataset(DATASET)
attach_files_to_dataset(DATASET, filelist_lines)

if skipped_lb_report:
    print("\n=== LB validation summary (dropped due to missing Rucio files) ===")
    for run, dropped, before, after in skipped_lb_report:
        print(f"  Run {run}: {before} -> {after} LBs available (dropped {dropped})")
else:
    print("\nNo LBs were dropped due to missing catalog entries.")