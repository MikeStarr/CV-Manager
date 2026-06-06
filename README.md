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

## Cloud LLM Configuration

CV Manager supports local LLM execution (default) as well as cloud providers: OpenAI (ChatGPT), DeepSeek, and Grok.

### 1. Configure API Keys
To use a cloud provider, create a `.env` file at the root of the project (you can copy `.env.example` as a template) and add your API keys:

```env
# OpenAI (ChatGPT) API Key (from https://platform.openai.com/)
OPENAI_API_KEY=your_openai_api_key_here

# DeepSeek API Key (from https://platform.deepseek.com/)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Grok API Key (from https://console.x.ai/)
XAI_API_KEY=your_grok_api_key_here

# Local LLM Configuration (LM Studio)
LM_STUDIO_MODEL=llama-3.1-8b-instruct
```

### 2. Using Cloud LLMs in the UI
1. Launch the Streamlit application.
2. In the left-hand configuration sidebar, locate the **LLM Provider & Settings** section.
3. Use the **Select LLM Provider** dropdown to select from:
   - **Local** - Run locally with LM Studio (default)
   - **ChatGPT** - Use OpenAI's GPT-4o model
   - **DeepSeek** - Use DeepSeek's deepseek-chat model
   - **Grok** - Use xAI's Grok-4.3 model
4. The application will automatically configure the appropriate API endpoint, model, and safely load the corresponding API key from your `.env` file. You can also customize the request timeout limit.

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
