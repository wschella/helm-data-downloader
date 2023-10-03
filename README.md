# HELM Data Downloader

TODO: Remove todo's from download

Download evaluation data from the Stanford Holistic Evaluation of Language Models (HELM) project

At the time of writing, the HELM evaluation effort contains almost 7000 evaluation runs, totalling about 70GiB of prompts, model outputs, and meta data.

This script/tool allows you to download it all easily.

## Usage

Run the downloader:

```shell
$ helmdd --version latest
Found 6879 runs online. No runs already downloaded found. Downloading all.
  2%|██▋              | 171/6879 [07:05<4:56
  3%|██▋              | 172/6879 [07:07<4:53
  3%|██▋              | 173/6879 [07:10<4:45
  3%|██▊...
```

### Options

```shell
$ helmdd --help
usage: helmdd [-h] [--version VERSION] [--output-dir OUTPUT_DIR] [--storage-url STORAGE_URL] [--redownload] [--max-runs MAX_RUNS] [--dry-run]

HELM Data Downloader

options:
  -h, --help            show this help message and exit
  --version VERSION     HELM release version to download data from. Example: v0.2.4, default is 'latest'.
  --output-dir OUTPUT_DIR
                        Output directory to store downloaded data. Default: ./data/{VERSION}/
  --storage-url STORAGE_URL
                        The URL to download data from. Default: <https://storage.googleapis.com/crfm-helm-public/benchmark_output/>.Can be changed to a local mirror with similar
                        folder structure, or adapted when HELM changes their storage location and this tool has not been updated yet.
  --redownload          Redownload all data, even if present already.
  --max-runs MAX_RUNS   Maximum number of runs to download.
  --dry-run             Dry run. Do not download any runs.
```
