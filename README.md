# HELM and HEIM Data Downloader

Download evaluation data from the Stanford _Holistic Evaluation of Language Models (HELM)_ project, including _HELM Lite_, _HELM Instruct_, and _HEIM_.

At the time of writing, the HELM evaluation effort is at release v0.4.0 and contains more than almost 8500 evaluation runs, totalling more than 800GiB of prompts, model outputs, and meta data.

This script/tool allows you to download it all easily.

## Install

```shell
pip install git+https://github.com/wschella/helm-data-downloader
```

## Usage

Run the downloader:

```shell
$ helmdd --release latest
Found 8526 runs online. No runs already downloaded found. Downloading all.
  2%|██▋              | 171/8526 [07:05<4:56
  3%|██▋              | 172/8526 [07:07<4:53
  3%|██▋              | 173/8526 [07:10<4:45
  3%|██▊...
```

To download _HELM Lite_ data, just use `--project lite`, same goes for `heim` and `instruct`.

### Options

```shell
$ helmdd --help
usage: helmdd [-h] [--project PROJECT_ID] [--release RELEASE] [--output-dir OUTPUT_DIR]
              [--storage-url STORAGE_URL] [--redownload] [--max-runs MAX_RUNS]
              [--dry-run] [--files FILES [FILES ...]]

HELM Data Downloader

options:
  -h, --help            show this help message and exit
  --project PROJECT_ID  Project to download data from. Options: classic, heim, lite,
                        instruct, all. Default: lite.
  --release RELEASE     Release version to download data from. Example: v0.2.4. The
                        default is 'latest', which will search for the latest release.
  --output-dir OUTPUT_DIR
                        Output directory to store downloaded data. Default: ./helm-
                        data/<PROJECT>/<RELEASE>/
  --storage-url STORAGE_URL
                        The URL to download data from. Default behaviour is to search
                        for it on the HELM website.It can be changed to e.g. use local
                        mirror with similar folder structure, or adapted when HELM
                        changes their storage location and this tool has not been
                        updated yet.
  --redownload          Redownload all data, even if present already.
  --max-runs MAX_RUNS   Maximum number of runs to download.
  --dry-run             Dry run. Do not download any runs.
  --files FILES [FILES ...]
                        Files to download for each run. Default: [scenario_state.json,
                        instances.json, display_predictions.json]. Available:
                        [run_spec.json, scenario.json, scenario_state.json, stats.json,
                        instances.json, display_predictions.json,
                        display_requests.json].You can also put 'all' to download all
                        files.
```

### Further notes

Currently still not possible yet:

- filter runs to download (as on the HELM/HEIM web pages)
- select which data to download (prompts, model outputs, meta data)

All of this should be easy to add yourself if needed. Feel free to open a PR.

Other interesting files are e.g. the schema.json, e.g. <https://storage.googleapis.com/crfm-helm-public/benchmark_output/releases/v0.4.0/schema.json>, which contains all the models, metrics, adapters, etc...
