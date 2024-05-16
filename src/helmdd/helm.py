from typing import Callable, Optional, TypedDict, Dict
from pathlib import Path
from dataclasses import dataclass
import re
import sys
import json
import urllib.parse
import argparse

import requests
from tqdm import tqdm

FILES = [
    "run_spec.json",
    "scenario.json",
    "scenario_state.json",
    "stats.json",
    "instances.json",
    "display_predictions.json",
    "display_requests.json",
]
PROJECTS = ["classic", "heim", "lite", "instruct"]


class ProjectInfo(TypedDict):
    name: str
    release_regex: str
    get_release_url: Callable[[str, str], str]


PROJECT_INFO: Dict[str, ProjectInfo] = {
    "classic": {
        "name": "Classic",
        "release_regex": r'window.RELEASE = "(.+)";',
        "get_release_url": lambda storage_url, release: f"{storage_url}/releases/{release}",
    },
    "heim": {
        "name": "HEIM",
        "release_regex": r'window.SUITE = "(.+)";',
        "get_release_url": lambda storage_url, release: f"{storage_url}/runs/{release}",
    },
    "lite": {
        "name": "Lite",
        "release_regex": r'window.RELEASE = "(.+)";',
        "get_release_url": lambda storage_url, release: f"{storage_url}/releases/{release}",
    },
    "instruct": {
        "name": "Instruct",
        "release_regex": r'window.RELEASE = "(.+)";',
        "get_release_url": lambda storage_url, release: f"{storage_url}/releases/{release}",
    },
}


@dataclass
class Args:
    """CLI Arguments"""

    project_id: str
    release: str
    output_dir: Path
    storage_url: Optional[str]
    redownload: bool
    max_runs: Optional[int]
    dry_run: bool
    files: list[str]


@dataclass
class RunInfo:
    id: str
    suite: str

    def path_safe_id(self):
        return urllib.parse.quote(self.id, safe="")


def run(args: Args):
    projects = PROJECTS if args.project_id == "all" else [args.project_id]
    for project_id in projects:
        download_project(project_id, args)


def download_project(project: str, args: Args):
    """
    Download all runs from the HELM benchmarking website.

    The latest release of the benchmarking website is e.g. at
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
    if project not in PROJECTS:
        raise ValueError(f"Unknown HELM project: {project}.")

    print(f"# Downloading data for HELM {PROJECT_INFO[project]['name']} project.")
    project_info = PROJECT_INFO[project]
    config_url = f"https://crfm.stanford.edu/helm/{project}/latest/config.js"

    # Get version
    if args.release == "latest":
        try:
            config_js = requests.get(config_url)
            release_re = re.search(project_info["release_regex"], config_js.text)
            release = release_re.group(1)  # type: ignore
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
            config_js = requests.get(config_url)
            storage_url_re = re.search(
                r'window.BENCHMARK_OUTPUT_BASE_URL =\s+"(.*)";',
                config_js.text,
            )
            storage_url = storage_url_re.group(1)  # type: ignore
            print(f"Found storage URL '{storage_url}'.")
        except Exception:
            print("Could not find storage URL automatically. ", end="")
            print("Try setting it manually with e.g. `--storage-url https://example.com`.")
    else:
        storage_url = args.storage_url

    # Normalise storage url
    storage_url = storage_url.rstrip("/")
    storage_url = f"{storage_url}"
    release_url = project_info["get_release_url"](storage_url, release)

    # Get run ids
    print(f"Getting run ids from '{release_url}/run_specs.json")
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
    if project != "heim":
        print(f"Getting run to suite mapping from {release_url}/runs_to_run_suites.json")  # fmt: skip
        runs_to_run_suites = requests.get(f"{release_url}/runs_to_run_suites.json").json()  # fmt: skip
        runs = [RunInfo(id=id, suite=runs_to_run_suites[id]) for id in run_ids]
    else:
        runs = [RunInfo(id=id, suite=release) for id in run_ids]

    # Configure outputs
    output_dir = args.output_dir or Path(f"./helm-data/{project}/{release}/")
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.files == ["all"]:
        run_files = FILES
    else:
        assert all(file in FILES for file in args.files), f"Unknown file in {args.files}."  # fmt: skip
        run_files = args.files

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


def get_parser():
    parser = argparse.ArgumentParser(description="HELM Data Downloader")

    parser.add_argument(
        "-p",
        "--project",
        dest="project_id",
        type=str,
        default="classic",
        help=f"Project to download data from. Options: {', '.join(PROJECTS)}, all. Default: lite.",
    )

    parser.add_argument(
        "-r",
        "--release",
        type=str,
        default="latest",
        help="Release version to download data from. Example: v0.2.4. The default is 'latest', which will search for the latest release.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory to store downloaded data. Default: ./helm-data/<PROJECT>/<RELEASE>/",
    )
    parser.add_argument(
        "--storage-url",
        type=str,
        default=None,
        help="The URL to download data from. Default behaviour is to search for it on the HELM website. "
        + "It can be changed to e.g. use local mirror with similar folder structure, "
        + "or adapted when HELM changes their storage location and this tool has not been updated yet.",
    )
    parser.add_argument(
        "--redownload",
        action="store_true",
        help="Redownload all data, even if present already.",
    )
    parser.add_argument(
        "--max-runs", type=int, default=None, help="Maximum number of runs to download."
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run. Do not download any runs.")

    default_files = [
        "scenario_state.json",
        "instances.json",
        "display_predictions.json",
    ]
    parser.add_argument(
        "--files",
        type=str,
        nargs="+",
        default=default_files,
        help="Files to download for each run. "
        + f"Default: [{', '.join(default_files)}]. "
        + f"Available: [{', '.join(FILES)}]."
        + "You can also put 'all' to download all files.",
    )
    return parser


def main():
    parser = get_parser()
    args_raw = parser.parse_args()
    args = Args(**vars(args_raw))
    run(args)


if __name__ == "__main__":
    main()
