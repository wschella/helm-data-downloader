from pathlib import Path
import re
import sys

import requests
from tqdm import tqdm

from helm_data_downloader.shared import Args, RunInfo, get_arg_parser


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
            semver = re.search(
                r'window.RELEASE = "(v\d+\.\d+\.\d+)";',
                config_js.text,
            ).group(1)  # type: ignore
            print(f"Using latest release, which is found to be '{semver}'.")
        except Exception:
            print("Could not find latest release automatically. ", end="")
            print("Try setting it manually with e.g. `--release v0.2.4`.")
            sys.exit(1)
    else:
        semver = args.release

    # Get storage url
    if args.storage_url is None:
        try:
            config_js = requests.get("https://crfm.stanford.edu/helm/latest/config.js")
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
    storage_url = f"{storage_url}/benchmark_output/releases"

    output_dir = args.output_dir or Path(f"./helm-data/{semver}/")

    # Get run ids
    print(f"Getting run ids from {storage_url}/{semver}/run_specs.json")
    run_specs = requests.get(f"{storage_url}/{semver}/run_specs.json").json()
    runs = [RunInfo(id=run_spec["name"]) for run_spec in run_specs]

    # Manage already downloaded runs
    already_downloaded = set(
        run.id
        for run in runs
        if (
            (output_dir / run.path_safe_id()).exists()
            and (output_dir / run.path_safe_id() / "run_spec.json").exists()
            and (output_dir / run.path_safe_id() / "scenario_state.json").exists()
            and (output_dir / run.path_safe_id() / "scenario.json").exists()
        )
    )
    runs_to_download = [run for run in runs if run.id not in already_downloaded]
    runs_to_download = sorted(runs_to_download, key=lambda run: run.id)
    print(f"Found {len(runs)} runs online.", end=" ")
    print(f"Found {len(already_downloaded)} runs already downloaded.")
    if args.redownload:
        print(f"Redownload flag set. Downloading all {len(runs_to_download)} runs.")
    else:
        print(f"Downloading remaining {len(runs_to_download)} runs.")
    if args.max_runs is not None:
        print(f"NOTE: Capped at {args.max_runs} runs, by --max-runs.")
    if args.dry_run:
        print("NOTE: Dry run. Not downloading any runs.")

    # Download runs
    output_dir.mkdir(parents=True, exist_ok=True)
    for run in tqdm(runs_to_download[: args.max_runs]):
        if args.dry_run:
            continue

        run_dir_path = output_dir / run.path_safe_id()
        run_dir_path.mkdir(parents=True, exist_ok=True)

        run_spec = requests.get(f"{storage_url}/runs/{run.id}/run_spec.json")
        scenario_state = requests.get(f"{storage_url}/runs/{run.id}/scenario_state.json")  # fmt: skip
        scenario = requests.get(f"{storage_url}/runs/{run.id}/scenario.json")

        with open(run_dir_path / "run_spec.json", "wb") as f:
            f.write(run_spec.content)
        with open(run_dir_path / "scenario_state.json", "wb") as f:
            f.write(scenario_state.content)
        with open(run_dir_path / "scenario.json", "wb") as f:
            f.write(scenario.content)


def main():
    parser = get_arg_parser(
        benchmark="HELM",
        storage_url="https://storage.googleapis.com/crfm-helm-public/",
    )
    args = parser.parse_args()
    run(Args(**vars(args)))


if __name__ == "__main__":
    main()