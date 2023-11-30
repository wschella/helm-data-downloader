from typing import Optional
from pathlib import Path
from dataclasses import dataclass
import urllib.parse
import re
import sys

import requests
from tqdm import tqdm


@dataclass
class Args:
    """CLI Arguments"""
    version: str
    output_dir: Path
    storage_url: str
    redownload: bool
    max_runs: Optional[int]
    dry_run: bool


@dataclass
class RunInfo():
    id: str

    def path_safe_id(self):
        return urllib.parse.quote(self.id, safe="")


def run(args: Args):
    """
    Download all runs from the HELM benchmarking website.

    The latest version of the benchmarking website is at <https://crfm.stanford.edu/helm/latest/?runs=1/>.
    The corresponding semver string is provided in <https://crfm.stanford.edu/helm/latest/benchmarking.js>,
      in a piece of code that looks like this: `version = "release" in urlParams ? urlParams.release : "v0.2.4";`.
    The list of all runs is available at <https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/{VERSION}/run_specs.json>,
      where {VERSION} is the semver string, e.g. v0.2.4.
    The data for each individual run is available at <https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/{VERSION}/{RUN_ID}/scenario_state.json>,
      where {RUN_ID} is a run id babi_qa:task=15,model=AlephAlpha_luminous-base, which is sourced from the run_specs.json.

    A complete example of all instance results is this:
     https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/babi_qa:task=15,model=AlephAlpha_luminous-base/run_spec.json
    """
    # Normalise storage url
    if args.storage_url[-1] == "/":
        storage_url = args.storage_url[:-1]
    else:
        storage_url = args.storage_url

    # Get semver
    if args.version == "latest":
        try:
            benchmarking_js = requests.get("https://crfm.stanford.edu/helm/latest/benchmarking.js")
            # The JS currently looks like `version = "release" in urlParams ? urlParams.release : "v0.2.4";`
            semver = re.search(r'version = "release" in urlParams \? urlParams\.release ?: ?"(v\d+\.\d+\.\d+)";',
                               benchmarking_js.text).group(1)  # type: ignore
            print(f"Using latest version, which is found to be '{semver}'.")
        except Exception:
            print("Could not find latest version automatically. Try setting it manually with e.g. `--version v0.2.4`.")
            sys.exit(1)
    else:
        semver = args.version

    output_dir = args.output_dir or Path(f"./data/{semver}/")

    # Get run ids
    print(f"Getting run ids from {storage_url}/runs/{semver}/run_specs.json")
    run_specs = requests.get(f"{storage_url}/runs/{semver}/run_specs.json").json()
    runs = [RunInfo(id=run_spec["name"]) for run_spec in run_specs]

    # Manage already downloaded runs
    already_downloaded = set(run.id for run in runs if (
        (output_dir / run.path_safe_id()).exists() and
        (output_dir / run.path_safe_id() / "run_spec.json").exists() and
        (output_dir / run.path_safe_id() / "scenario_state.json").exists() and
        (output_dir / run.path_safe_id() / "scenario.json").exists()
    ))
    runs_to_download = [run for run in runs if run.id not in already_downloaded]
    dry_run_note = " Note: dry run." if args.dry_run else ""
    if len(already_downloaded) > 0 and not args.redownload:
        print(f"Found {len(runs)} runs online, and {len(already_downloaded)} runs already downloaded.\n" +
              f"Downloading remaining {len(runs_to_download)}.{dry_run_note}")
    else:
        if args.redownload:
            print(f"Found {len(runs)} runs online, and {len(already_downloaded)} runs already downloaded.\n" +
                  f"Redownload flag set. Downloading all.{dry_run_note}")
        else:
            print(f"Found {len(runs)} runs online. No runs already downloaded found. " +
                  f"Downloading all.{dry_run_note}")

    # Download runs
    output_dir.mkdir(parents=True, exist_ok=True)
    for run in tqdm(runs_to_download[:args.max_runs]):
        if args.dry_run:
            continue

        run_dir_path = output_dir / run.path_safe_id()
        run_dir_path.mkdir(parents=True, exist_ok=True)

        run_spec = requests.get(f"{storage_url}/runs/{run.id}/run_spec.json")
        scenario_state = requests.get(f"{storage_url}/runs/{run.id}/scenario_state.json")
        scenario = requests.get(f"{storage_url}/runs/{run.id}/scenario.json")

        with open(run_dir_path / "run_spec.json", "wb") as f:
            f.write(run_spec.content)
        with open(run_dir_path / "scenario_state.json", "wb") as f:
            f.write(scenario_state.content)
        with open(run_dir_path / "scenario.json", "wb") as f:
            f.write(scenario.content)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="HELM Data Downloader")
    parser.add_argument("--version", type=str, default="latest",
                        help="HELM release version to download data from. Example: v0.2.4, default is 'latest'.")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory to store downloaded data. Default: ./data/{VERSION}/")
    parser.add_argument("--storage-url", type=str, default="https://storage.googleapis.com/crfm-helm-public/benchmark_output/",
                        help="The URL to download data from. Default: <https://storage.googleapis.com/crfm-helm-public/benchmark_output/>." +
                             "Can be changed to a local mirror with similar folder structure, " +
                             "or adapted when HELM changes their storage location and this tool has not been updated yet.")
    parser.add_argument("--redownload", action="store_true",
                        help="Redownload all data, even if present already.")
    parser.add_argument("--max-runs", type=int, default=None,
                        help="Maximum number of runs to download.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run. Do not download any runs.")

    args = parser.parse_args()

    run(Args(**vars(args)))


if __name__ == "__main__":
    main()
