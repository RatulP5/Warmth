# Kolkata Heatwave ML

A starting point for building a heatwave prediction workflow from Kolkata geospatial data.

## Environment setup

The recommended Windows setup uses Miniconda or Anaconda because GeoPandas depends on compiled geospatial libraries.

```powershell
conda env create -f environment.yml
conda activate heatwave-ml
```

If Conda is not installed, use the available Python interpreter instead:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

To update the environment after changing dependencies:

```powershell
conda env update -f environment.yml --prune
```

In VS Code, select the `heatwave-ml` interpreter with **Python: Select Interpreter**.

## Earth Engine credentials

Never commit Google service-account JSON files, OAuth tokens, API keys, or `.env` files. The repository ignores local credential files and generated datasets. Earth Engine authentication is performed locally with:

```powershell
earthengine authenticate
$env:EE_PROJECT_ID = "your-registered-earth-engine-project"
```

The project ID is configuration, not a secret. Keep the service-account JSON outside this repository, preferably under a protected `.secrets/` directory or another location excluded from source control. If a key is ever exposed, revoke it in Google Cloud immediately and create a replacement; deleting it from Git is not enough.

## Git and large files

CSV, Excel, Parquet, model checkpoints, logs, and generated outputs are intentionally ignored because they can be large or contain derived data. Store a small, anonymized sample separately if the repository needs a reproducible example. Use Git LFS only for data that is approved for public distribution.

Before committing, inspect the staged file list:

```powershell
git status --short
git diff --cached --stat
git diff --cached --name-only
```

## Project layout

- `data/` - optional home for raw and cleaned tabular data; the existing GeoJSON files remain at the project root.
- `notebooks/` - exploratory analysis and feature discovery.
- `src/heatwave_ml/` - reusable Python code.
- `scripts/` - small command-line entry points.
- `models/` - saved model artifacts, ignored by Git.
- `reports/` - generated figures and evaluation outputs.
- `tests/` - automated checks.

## First check

After activating the environment, inspect the available GeoJSON layers:

```powershell
python scripts/inspect_data.py
```

## Modeling notes

A prediction target and time-indexed weather observations are still needed. The current GeoJSON files describe spatial boundaries/features; they are useful for spatial joins and mapping, but they do not by themselves provide the historical temperature, humidity, or heatwave labels required for supervised learning. Keep train/test splits chronological to avoid leakage.
