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
    release: str
    output_dir: Path
    storage_url: Optional[str]
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

    The latest release of the benchmarking website is at
     <https://crfm.stanford.edu/helm/latest/#/runs>.
    The corresponding semver string is provided in 
      <https://crfm.stanford.edu/helm/latest/config.js>, which looks like:
        ```
        window.BENCHMARK_OUTPUT_BASE_URL = "https://storage.googleapis.com/crfm-helm-public/";
        window.RELEASE = "v0.4.0";
        window.SUITE = null;
        ```
    The list of all runs is available at
      <{BASE_URL}/benchmark_output/runs/{RELEASE}/run_specs.json>,
      where {RELEASE} is the semver string, e.g. v0.2.4.
    The data for each individual run is available at 
      <{BASE_URL}/benchmark_output/runs/{RELEASE}/{RUN_ID}/scenario_state.json>,
      where {RUN_ID} is a run id babi_qa:task=15,model=AlephAlpha_luminous-base,
      which is sourced from the run_specs.json.
    The latest mapping from run ids to run suites is available at 
      <{BASE_URL}/benchmark_output/runs/{RELEASE}/runs_to_run_suites.json>.

    A complete example of all instance results is this:
     https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/babi_qa:task=15,model=AlephAlpha_luminous-base/run_spec.json
    """
    # Get semver
    if args.release == "latest":
        try:
            # ```
            # window.BENCHMARK_OUTPUT_BASE_URL =
            #       "https://storage.googleapis.com/crfm-helm-public/";
            # window.RELEASE = "v0.4.0";
            # window.SUITE = null;
            # ```
            config_js = requests.get("https://crfm.stanford.edu/helm/latest/config.js")
            semver = re.search(r'window.RELEASE = "(v\d+\.\d+\.\d+)";',
                               config_js.text).group(1)  # type: ignore
            print(f"Using latest release, which is found to be '{semver}'.")
        except Exception:
            print("Could not find latest release automatically. Try setting it manually with e.g. `--release v0.2.4`.")
            sys.exit(1)
    else:
        semver = args.release

    # Get storage url
    if args.storage_url is None:
        try:
            config_js = requests.get("https://crfm.stanford.edu/helm/latest/config.js")
            storage_url = re.search(r'window.BENCHMARK_OUTPUT_BASE_URL =\s+"(.*)";',
                                    config_js.text).group(1)  # type: ignore
            print(f"Found storage URL '{storage_url}'.")
        except Exception:
            default = "https://storage.googleapis.com/crfm-helm-public/"
            print("Could not find storage URL automatically")
            print(f"Using default URL '{default}'")
            print("You can also try setting it manually with e.g. `--storage-url https://storage.googleapis.com/crfm-helm-public/`.")
            storage_url = default
    else:
        storage_url = args.storage_url
        print(f"Using manually provided storage URL '{storage_url}'.")

    # Normalise storage url
    storage_url = storage_url.rstrip("/")
    storage_url = f"{storage_url}/benchmark_output/releases"

    output_dir = args.output_dir or Path(f"./data/{semver}/")

    # Get run ids
    print(f"Getting run ids from {storage_url}/{semver}/run_specs.json")
    run_specs = requests.get(f"{storage_url}/{semver}/run_specs.json").json()
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
    parser.add_argument("--release", type=str, default="latest",
                        help="HELM release version to download data from. Example: v0.2.4. The default is 'latest'.")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory to store downloaded data. Default: ./data/{RELEASE}/")
    parser.add_argument("--storage-url", type=str, default=None,
                        help="The URL to download data from. Default behaviour is to search for it on the HELM website, " +
                             "and if not found, use default value <https://storage.googleapis.com/crfm-helm-public/>." +
                             "It can be changed to e.g. use local mirror with similar folder structure, " +
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
