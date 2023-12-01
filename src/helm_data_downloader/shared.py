from typing import Optional, Union, Literal
from pathlib import Path
from dataclasses import dataclass
import urllib.parse

import argparse


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
class RunInfo:
    id: str

    def path_safe_id(self):
        return urllib.parse.quote(self.id, safe="")


def get_arg_parser(
    benchmark: Union[Literal["HELM"], Literal["HEIM"]],
    storage_url: str,
):
    H = benchmark
    h = H.lower()

    parser = argparse.ArgumentParser(description=f"{H} Data Downloader")
    parser.add_argument(
        "--release",
        type=str,
        default="latest",
        help=f"{H} release version to download data from. Example: v0.2.4. The default is 'latest'.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Output directory to store downloaded data. Default: ./{h}-data/<RELEASE>/",
    )
    parser.add_argument(
        "--storage-url",
        type=str,
        default=None,
        help=f"The URL to download data from. Default behaviour is to search for it on the {H} website, "
        + f"and if not found, use default value <{storage_url}>."
        + "It can be changed to e.g. use local mirror with similar folder structure, "
        + f"or adapted when {H} changes their storage location and this tool has not been updated yet.",
    )
    parser.add_argument(
        "--redownload",
        action="store_true",
        help="Redownload all data, even if present already.",
    )
    parser.add_argument(
        "--max-runs", type=int, default=None, help="Maximum number of runs to download."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run. Do not download any runs."
    )
    return parser
