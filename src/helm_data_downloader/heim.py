import re
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from helm_data_downloader.shared import Args, RunInfo, get_arg_parser


def run(args: Args):
    """
    Download all runs from the HEIM benchmarking website.

    The latest release of the benchmarking website is at
     <https://crfm.stanford.edu/heim/latest/?runs>.
    The corresponding semver string is provided in
      <https://crfm.stanford.edu/heim/latest/json-urls-root.js>, which looks like:
        ```
        const BENCHMARK_OUTPUT_BASE_URL = "https://nlp.stanford.edu/helm/{RELEASE}/benchmark_output/";
        ```
    The list of all runs is available at
      <{BASE_URL}/runs/{RELEASE}/run_specs.json>,
      where {RELEASE} is the semver string, e.g. v0.2.4.
    The data for each individual run is available at
      <{BASE_URL}/runs/{RELEASE}/{RUN_ID}/scenario_state.json>,
      where {RUN_ID} is a run id babi_qa:task=15,model=AlephAlpha_luminous-base,
      which is sourced from the run_specs.json.

    A complete example of all instance results is this:
     https://nlp.stanford.edu/helm/v1.1.0/benchmark_output/runs/latest/common_syntactic_processes:phenomenon=ambiguity,model=AlephAlpha_m-vader,max_eval_instances=100/scenario_state.json
    """

    # Get semver
    if args.release == "latest":
        try:
            json_urls_root = requests.get(
                "https://crfm.stanford.edu/heim/latest/json-urls-root.js"
            )
            storage_url = re.search(
                r'const BENCHMARK_OUTPUT_BASE_URL =\s+"(.*)";',
                json_urls_root.text,
            ).group(1)  # type: ignore
            semver = re.search(r"(v\d+\.\d+\.\d+)", storage_url).group(1)  # type: ignore
            print(f"Using latest version, which is found to be '{semver}'.")
        except Exception:
            print("Could not find latest release automatically. ", end="")
            print("Try setting it manually with e.g. `--release v0.2.4`.")
            sys.exit(1)
    else:
        semver = args.release

    # Get storage url
    if args.storage_url is None:
        try:
            json_urls_root = requests.get("https://crfm.stanford.edu/heim/latest/json-urls-root.js")  # fmt: skip
            storage_url = re.search(
                r'const BENCHMARK_OUTPUT_BASE_URL =\s+"(.*)";',
                json_urls_root.text,
            ).group(1)  # type: ignore
            print(f"Found storage URL '{storage_url}'.")
        except Exception:
            default = f"https://nlp.stanford.edu/helm/{semver}/benchmark_output"
            print("Could not find storage URL automatically")
            print(f"Using default URL '{default}'")
            print("You can also try setting it manually with e.g. `--storage-url`.")
            storage_url = default
    else:
        storage_url = args.storage_url
        print(f"Using manually provided storage URL '{storage_url}'.")

    # Normalise storage url
    storage_url = storage_url.rstrip("/")
    # storage_url = f"{storage_url}/benchmark_output/"

    output_dir = args.output_dir or Path(f"./heim-data/{semver}/")

    # Get run ids
    print(f"Getting run ids from {storage_url}/runs/{semver}/run_specs.json")
    run_specs = requests.get(f"{storage_url}/runs/{semver}/run_specs.json").json()
    runs = [RunInfo(id=run_spec["name"], suite=semver) for run_spec in run_specs]

    # All the different files associated with a run
    run_files = [
        # "run_spec.json",
        # "scenario.json",
        # "scenario_state.json",
        # "stats.json",
        "instances.json",  # !Important! Has inputs
        "display_predictions.json",  # !Important! Has outputs and metrics
        # "display_requests.json",
    ]

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
        benchmark="HEIM",
        storage_url="https://nlp.stanford.edu/helm/{RELEASE}/benchmark_output/",
    )
    args = parser.parse_args()
    run(Args(**vars(args)))


if __name__ == "__main__":
    main()
