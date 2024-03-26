from pathlib import Path
import re
import sys
import json

import requests
from tqdm import tqdm

from helm_data_downloader.shared import Args, RunInfo, get_arg_parser


def run(args: Args):
    """
    Download all runs from the HELM benchmarking website.

    The latest release of the benchmarking website is at
     <https://crfm.stanford.edu/helm/classic/latest/#/runs>.
    The corresponding semver string is provided in
      <https://crfm.stanford.edu/helm/classic/latest/config.js>, which looks like:
        ```
        window.BENCHMARK_OUTPUT_BASE_URL = "https://storage.googleapis.com/crfm-helm-public/benchmark_output/";
        window.SUITE = null;
        window.RELEASE = "v0.4.0";
        window.HELM_TYPE = "Classic";
        window.PROJECT_ID = "classic";
        ```
    The list of all runs is available at
      <{BASE_URL}/benchmark_output/runs/{RELEASE}/run_specs.json>,
      where {RELEASE} is the semver string, e.g. v0.2.4.
    The latest mapping from run ids to run suites (i.e. releases) is available at
      <{BASE_URL}/benchmark_output/runs/{RELEASE}/runs_to_run_suites.json>.
    The data for each individual run is available at
      <{BASE_URL}/benchmark_output/runs/{SPECIFIC-RELEASE}/{RUN_ID}/scenario_state.json>,
      where {RUN_ID} is a run id babi_qa:task=15,model=AlephAlpha_luminous-base,
      which is sourced from the run_specs.json, and
      {SPECIFIC-RELEASE} is the specific release that the run was run on,
      defined in runs_to_run_suites.json.

    A complete example of all instance results is this:
     https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/babi_qa:task=15,model=AlephAlpha_luminous-base/run_spec.json
    """
    # Get semver
    if args.release == "latest":
        try:
            # See docstring for more info.
            config_js = requests.get("https://crfm.stanford.edu/helm/classic/latest/config.js")  # fmt: skip
            release = re.search(
                r'window.RELEASE = "(v\d+\.\d+\.\d+)";',
                config_js.text,
            ).group(1)  # type: ignore
            print(f"Using latest release, which is found to be '{release}'.")
        except Exception:
            print("Could not find latest release automatically. ", end="")
            print("Try setting it manually with e.g. `--release v0.2.4`.")
            sys.exit(1)
    else:
        release = args.release

    # Get storage url
    if args.storage_url is None:
        try:
            config_js = requests.get("https://crfm.stanford.edu/helm/classic/latest/config.js")  # fmt: skip
            storage_url = re.search(
                r'window.BENCHMARK_OUTPUT_BASE_URL =\s+"(.*)";',
                config_js.text,
            ).group(1)  # type: ignore
            print(f"Found storage URL '{storage_url}'.")
        except Exception:
            default = "https://storage.googleapis.com/crfm-helm-public/"
            print("Could not find storage URL automatically")
            print(f"Using default URL '{default}'")
            print("You can also try setting it manually with e.g. `--storage-url`.")
            storage_url = default
    else:
        storage_url = args.storage_url
        print(f"Using manually provided storage URL '{storage_url}'.")

    # Normalise storage url
    storage_url = storage_url.rstrip("/")
    storage_url = f"{storage_url}"
    release_url = f"{storage_url}/releases/{release}"

    # Get run ids
    print(f"Getting run ids from {release_url}/run_specs.json")
    try:
        run_specs = requests.get(f"{release_url}/run_specs.json").json()
    except json.JSONDecodeError as e:
        print(f"Could not find run specs for release '{release}'.")
        print("-------------- BEGIN HTML --------------")
        print(e.doc)
        print("-------------- END HTML --------------")
        print("You'll have to fix the code yourself.")
        sys.exit(1)
    run_ids = [run_spec["name"] for run_spec in run_specs]

    # Get run to suite mapping
    print(f"Getting run to suite mapping from {release_url}/runs_to_run_suites.json")  # fmt: skip
    runs_to_run_suites = requests.get(f"{release_url}/runs_to_run_suites.json").json()  # fmt: skip
    runs = [RunInfo(id=id, suite=runs_to_run_suites[id]) for id in run_ids]

    output_dir = args.output_dir or Path("./helm-data/") / release

    # All the different files associated with a run
    # Options:
    # "run_spec.json",
    # "scenario.json",
    # "scenario_state.json",
    # "stats.json",
    # "instances.json",  # !Important! Has inputs
    # "display_predictions.json",  # !Important! Has outputs and metrics
    # "display_requests.json",
    run_files = args.get_files()

    # Manage already downloaded runs
    def is_downloaded(run: RunInfo):
        run_dir = output_dir / run.path_safe_id()
        return all((run_dir / f"{file}").exists() for file in run_files)

    already_downloaded = set(run.id for run in runs if is_downloaded(run))
    runs_to_download = [run for run in runs if run.id not in already_downloaded]
    runs_to_download = sorted(runs_to_download, key=lambda run: run.id)
    print(f"Found {len(runs)} runs online.", end=" ")
    print(f"Found {len(already_downloaded)} runs already downloaded.")
    if args.redownload:
        print(f"Redownload flag set. Downloading all {len(runs_to_download)} runs.")
    else:
        print(f"Downloading remaining {len(runs_to_download)} runs.")
    if args.max_runs is not None:
        print(f"NOTE: Capped at {args.max_runs} runs by --max-runs.")
    if args.dry_run:
        print("NOTE: Dry run. Not downloading any runs.")

    # Download runs
    output_dir.mkdir(parents=True, exist_ok=True)
    for run in tqdm(runs_to_download[: args.max_runs]):
        if args.dry_run:
            continue

        run_dir_path = output_dir / run.path_safe_id()
        run_dir_path.mkdir(parents=True, exist_ok=True)

        run_url = f"{storage_url}/runs/{run.suite}/{run.id}"
        for file_name in run_files:
            file_url = f"{run_url}/{file_name}"
            file = requests.get(file_url)
            if file.status_code == 200:
                with open(run_dir_path / file_name, "wb") as f:
                    f.write(file.content)
            else:
                with open(run_dir_path / f"{file_name}.error", "wb") as f:
                    f.write(file.content)
                raise Exception(f"Could not download {file_name} from {file_url}.")


def main():
    parser = get_arg_parser(
        benchmark="HELM",
        storage_url="https://storage.googleapis.com/crfm-helm-public/",
    )
    args = parser.parse_args()
    run(Args(**vars(args)))


if __name__ == "__main__":
    main()
