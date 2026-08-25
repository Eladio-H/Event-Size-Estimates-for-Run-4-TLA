# script for running reprocessing of the trigger
# if trigger running over not in menu, you need a local checkout of athena and add said trigger to the menu you are running over
#!/usr/bin/env python3

import argparse
import subprocess
import sys
import json

parser = argparse.ArgumentParser()

parser.add_argument("rawfile")
parser.add_argument(
    "--trigger",
)

parser.add_argument(
    "--menu",
    default="Physics_pp_run3_v1",
)

parser.add_argument(
    "--output",
    default="rerun.RAW",
)

parser.add_argument(
    "--threads",
    type=int,
    default=8,
)

args = parser.parse_args()


# TO DO: Integrate trigbs_extractStream.py
cmd = [
    "athenaHLT.py",
    "--threads", str(args.threads),
    "--concurrent-events", str(args.threads),
    "--filesInput", args.rawfile,
    "--save-output", args.output,
    "--number-of-events", "100",
    "--log-level", "DEBUG",
    "TriggerJobOpts.runHLT",
    f'Trigger.triggerMenuSetup="{args.menu}"',
    "Trigger.doLVL1=True",
    #f'Trigger.selectChains={select_chains}', # either args.trigger/select_chains
]
if args.trigger:
    chains = [c.strip() for c in args.trigger.split(",") if c.strip()]
    cmd.append(f"Trigger.selectChains={json.dumps(chains)}")

print("Running:")
#print(" ".join(cmd))

subprocess.run(
    cmd,
    #shell=True,
    check=True,
)
