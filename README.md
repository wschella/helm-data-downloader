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

You might want the version of results to download. We currently hardcode v0.2.3, to avoid having to run selenium to fetch the actual latest version (since the HELM webpage is JS based).

To do that, you want to specify the `--storage-url` argument to replace the current default `https://storage.googleapis.com/crfm-helm-public/benchmark_output/runs/v0.2.3/`. You can find out by clicking on `Spec JSON` or `Full JSON` on a run info page (pick any from [here](https://crfm.stanford.edu/helm/latest/?runs=1)), and looking at the URL it goes to.
