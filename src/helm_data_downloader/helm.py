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
            # ```
            # window.BENCHMARK_OUTPUT_BASE_URL =
            #       "https://storage.googleapis.com/crfm-helm-public/";
            # window.RELEASE = "v0.4.0";
            # window.SUITE = null;
            # ```
            config_js = requests.get("https://crfm.stanford.edu/helm/latest/config.js")
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
    storage_url = f"{storage_url}/benchmark_output"
    release_url = f"{storage_url}/releases/{release}"

    # Get run ids
    print(f"Getting run ids from {release_url}/run_specs.json")
    run_specs = requests.get(f"{release_url}/run_specs.json").json()
    run_ids = [run_spec["name"] for run_spec in run_specs]

    # Get run to suite mapping
    print(f"Getting run to suite mapping from {release_url}/runs_to_run_suites.json")  # fmt: skip
    runs_to_run_suites = requests.get(f"{release_url}/runs_to_run_suites.json").json()  # fmt: skip
    runs = [RunInfo(id=id, suite=runs_to_run_suites[id]) for id in run_ids]

    output_dir = args.output_dir or Path("./helm-data/") / release

    # Manage already downloaded runs
    def is_downloaded(run: RunInfo):
        run_dir = output_dir / run.path_safe_id()
        return (
            run_dir.exists()
            and (run_dir / "run_spec.json").exists()
            and (run_dir / "scenario_state.json").exists()
            and (run_dir / "scenario.json").exists()
        )

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

        run_url = f"{storage_url}/runs/{run.suite}/{run.id}"
        run_spec = requests.get(f"{run_url}/run_spec.json")
        scenario_state = requests.get(f"{run_url}/scenario_state.json")  # fmt: skip
        scenario = requests.get(f"{run_url}/scenario.json")

        assert run_spec.status_code == 200
        assert scenario_state.status_code == 200
        assert scenario.status_code == 200

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
