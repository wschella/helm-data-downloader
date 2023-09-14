from typing import *
from pathlib import Path
from dataclasses import dataclass
import urllib.parse

import requests
from tqdm import tqdm
from pyquery import PyQuery as pq

@dataclass
class Args:
    """CLI Arguments"""
    source_file: Path
    storage_url: str
    output_dir: Path
    redownload: bool
    max_runs: Optional[int]
    # https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/babi_qa:task=15,model=AlephAlpha_luminous-base/run_spec.json

@dataclass
class RunInfo():
    id: str
    href: str
    adaptation_method: str

    def path_safe_id(self):
        return urllib.parse.quote(self.id, safe="")

def run(args: Args):
    page = args.source_file.read_text()
    page = pq(page)

    # Find all runs in the page
    runs_raw = page("table.query-table tr") # Get all rows of the run table
    runs_raw = runs_raw[1:] # Ignore the heading
    runs: List[RunInfo] = [RunInfo(
        id=str(pq(run[0][0]).text()), # Get first column, first element (a link), and get the text
        href=str(pq(run[0][0]).attr('href')), # Get first column, first element (a link), and get the href
        adaptation_method=str(pq(run[1]).text()) # Get second column and get the text
    ) for run in runs_raw]

    # Manage already downloaded runs
    already_downloaded = set(run.id for run in runs if (
        (args.output_dir / run.path_safe_id()).exists() and
        (args.output_dir / run.path_safe_id() / "run_spec.json").exists() and
        (args.output_dir / run.path_safe_id() / "scenario_state.json").exists() and
        (args.output_dir / run.path_safe_id() / "scenario.json").exists()
    ))
    runs_to_download = [run for run in runs if run.id not in already_downloaded]
    if len(already_downloaded) > 0 and not args.redownload:
        print(f"Found {len(runs)} runs online, and {len(already_downloaded)} runs already downloaded.\n" + \
              f"Downloading remaining {len(runs_to_download)}.")
    else:
        if args.redownload:
            print(f"Found {len(runs)} runs online, and {len(already_downloaded)} runs already downloaded.\n" + \
                  f"Redownload flag set. Downloading all.")
        else:
            print(f"Found {len(runs)} runs online. No runs already downloaded found. Downloading all.")

    # Download runs
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for run in tqdm(runs_to_download[:args.max_runs]):
        run_dir_path = args.output_dir / run.path_safe_id()
        run_dir_path.mkdir(parents=True, exist_ok=True)
    
        run_spec = requests.get(f"{args.storage_url}{run.id}/run_spec.json")
        scenario_state = requests.get(f"{args.storage_url}{run.id}/scenario_state.json")
        scenario = requests.get(f"{args.storage_url}{run.id}/scenario.json")

        with open(run_dir_path / "run_spec.json", "wb") as f:
            f.write(run_spec.content)
        with open(run_dir_path / "scenario_state.json", "wb") as f:
            f.write(scenario_state.content)
        with open(run_dir_path / "scenario.json", "wb") as f:
            f.write(scenario.content)

def main():
    import argparse

    parser = argparse.ArgumentParser(description="HELM Data Downloader")
    parser.add_argument("source-file", type=Path, 
                        help="Path to already downloaded HELM /runs HTLM file that list all runs.")
    parser.add_argument("--storage-url", type=str, default="https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/", 
                        help="Storage URL to download run data from. Can be useful to download older versions.")
    parser.add_argument("--output-dir", type=Path, default="data", 
                        help="Output directory to store downloaded data.")
    parser.add_argument("--redownload", action="store_true", 
                        help="Redownload all data, even if present already.")
    parser.add_argument("--max-runs", type=int, default=None,
                         help="Maximum number of runs to download.")

    args = parser.parse_args()

    run(Args(**vars(args)))

if __name__ == "__main__":
    main()