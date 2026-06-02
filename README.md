# CV Manager

![PyPI version](https://img.shields.io/pypi/v/CV-Manager.svg)

Helps me manage all my job applications and specific cvs

* [GitHub](https://github.com/MikeStarr/CV-Manager/) | [PyPI](https://pypi.org/project/CV-Manager/) | [Documentation](https://MikeStarr.github.io/CV-Manager/)
* Created by [Michael Starr](none) | GitHub [@MikeStarr](https://github.com/MikeStarr) | PyPI [@MikeStarr](https://pypi.org/user/MikeStarr/)
* MIT License

## Features

* TODO

## Documentation

Documentation is built with [Zensical](https://zensical.org/) and deployed to GitHub Pages.

* **Live site:** https://MikeStarr.github.io/CV-Manager/
* **Preview locally:** `just docs-serve` (serves at http://localhost:8000)
* **Build:** `just docs-build`

API documentation is auto-generated from docstrings using [mkdocstrings](https://mkdocstrings.github.io/).

Docs deploy automatically on push to `main` via GitHub Actions. To enable this, go to your repo's Settings > Pages and set the source to **GitHub Actions**.

## Development

To set up for local development:

```bash
# Clone your fork
git clone git@github.com:your_username/CV-Manager.git
cd CV-Manager

# Install in editable mode with live updates
uv tool install --editable .
```

This installs the CLI globally but with live updates - any changes you make to the source code are immediately available when you run `cv_manager`.

Run tests:

```bash
uv run pytest
```

Run quality checks (format, lint, type check, test):

```bash
just qa
```

## Author

CV Manager was created in 2026 by Michael Starr.

Built with [Cookiecutter](https://github.com/cookiecutter/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.
