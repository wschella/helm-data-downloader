# HELM Data Downloader

Download evaluation data from the Stanford HELM project

At the time of writing, the HELM evaluation effort contains almost 7000 evaluation runs, totalling about 70GiB of prompts, model outputs, and meta data.

This script/tool allows you to download it all easily.

## Usage

Go to [https://crfm.stanford.edu/helm/latest/?runs=1](https://crfm.stanford.edu/helm/latest/?runs=1) and download the HTLM, which contains the list off all runs.

Run the downloader:

```shell
$ helm-data-downloader --source-file helm.html
Found 6879 runs online. No runs already downloaded found. Downloading all.
  2%|██▋              | 171/6879 [07:05<4:56
  3%|██▋              | 172/6879 [07:07<4:53
  3%|██▋              | 173/6879 [07:10<4:45
  3%|██▊...
```

You might need to specify the storage API to get the latest results,
we currently hardcode `https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/` to avoid having to run selenium. Find out by clicking on e.g. `Full JSON` on a run info page like [this one](https://crfm.stanford.edu/helm/latest/?runs=1&runSpec=babi_qa%3Atask%3D15%2Cmodel%3Dtogether_glm%2Cstop%3Dhash), and set the correct storage URL with `--storage-url`.

### Options

```shell
$ helm-data-downloader --help
usage: download [-h] [--storage-url STORAGE_URL] [--output-dir OUTPUT_DIR] [--redownload] [--max-runs MAX_RUNS] source-file

HELM Data Downloader

positional arguments:
  source-file           Path to already downloaded HELM /runs HTLM file that list all runs.

options:
  -h, --help            show this help message and exit
  --storage-url STORAGE_URL
                        Storage URL to download run data from. Can be useful to download older versions.
  --output-dir OUTPUT_DIR
                        Output directory to store downloaded data.
  --redownload          Redownload all data, even if present already.
  --max-runs MAX_RUNS   Maximum number of runs to download.
```
