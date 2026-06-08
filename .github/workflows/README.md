# GitHub Actions workflows

- **`quick_test.yml`** — Fast checks on every push/PR (all branches): editable install on Ubuntu with Python 3.13, pytest and doctests excluding slow and extension tests, with a coverage floor.
- **`test_core.yml`** — Full CI on `main`: editable install across OS and Python versions, coverage matrix, combined report, and Coveralls upload; also runs on a monthly schedule.
- **`test_extensions.yml`** — Extension-only tests on every push/PR (all branches): Ubuntu matrix over supported Python versions.
- **`build_test_wheels.yml`** — Builds platform wheels and an sdist, then runs pytest against installed wheels; runs on push to `main`, monthly schedule, and when called from `publish_pypi.yml`.
- **`publish_pypi.yml`** — Release workflow on version tags: calls `build_test_wheels.yml`, then uploads wheels and sdist to PyPI.
- **`publish_conda.yml`** — Manual release step after PyPI: Grayskull metadata, patch feedstock `meta.yaml`, push branch, and open a conda-forge PR.
- **`build_deploy_pages.yml`** — Builds Sphinx documentation and deploys to GitHub Pages on push to `main` (PRs build only).

## Helper script

- **`condaforge_meta_patch.py`** — Copies version, sha256, PyPI source URL, and build number from Grayskull output into a feedstock `recipe/meta.yaml` (used from the feedstock repo as `recipe/patch_meta.py` in `publish_conda.yml`).
