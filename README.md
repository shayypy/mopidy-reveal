# mopidy-reveal

[![Latest PyPI version](https://img.shields.io/pypi/v/mopidy-reveal)](https://pypi.org/p/mopidy-reveal)
[![CI build status](https://img.shields.io/github/actions/workflow/status/shayypy/mopidy-reveal/ci.yml)](https://github.com/shayypy/mopidy-reveal/actions/workflows/ci.yml)
[![Test coverage](https://img.shields.io/codecov/c/gh/shayypy/mopidy-reveal)](https://codecov.io/gh/shayypy/mopidy-reveal)

Mopidy extension to reveal some inner Mopidy functions via HTTP to third-party applications. This is basically a fancy way I came up with to get Tidal URIs without having to maintain a separate Python-Tidal application, since I will be running Mopidy with Mopidy-Tidal anyway. It should work with any Mopidy backend's URIs.

As such, only [`backend.playback.translate_uri`](#post-revealplaybacktranslate_uri) is currently implemented. If you would like to implement another method, feel free to submit an issue or PR.

## Installation

Install by running:

```sh
python3 -m pip install mopidy-reveal
```

See https://mopidy.com/ext/reveal/ for alternative installation methods.


## Configuration

Before starting Mopidy, you must add configuration for
mopidy-reveal to your Mopidy configuration file:

```ini
[reveal]
enabled = true
token =
backend.playback.translate_uri.enabled = true
```

- `token`: optionally secure the endpoint per-method by requiring a token (any random string can be used). Provide in an authorization header as `Bearer <token>`.
- `backend.playback.translate_uri.enabled`: enable this method

### `POST /reveal/rpc`

This is the only endpoint exposed by the extension, available on Mopidy's HTTP port (e.g. `http://localhost:6680/reveal/rpc`). It is designed to resemble Mopidy's JSON-RPC endpoint (& websocket), but I don't think it's fully compliant with the spec since it does not handle batch requests.

Methods below:

**reveal.core.get_enabled_methods**

This method cannot be disabled. Returns a map of methods to a boolean indicating whether they are enabled according to the config. Takes no params, but an empty dict (`{}`) must be provided.

Result example:

```json
{ "methods": { "backend.playback.translate_uris": true }}
```

**backend.playback.translate_uri**

Enable/disable with `backend.playback.translate_uri.enabled`

> Resolve a Mopidy URI to the "real" URI returned by the backend's [`PlaybackProvider.translate_uri`](https://docs.mopidy.com/stable/reference/backend/#mopidy.backend.PlaybackProvider.translate_uri) implementation.

Params example:

```json
{ "uri": "tidal:track:21600906:519451842:519451850" }
```

Result example:

```json
{ "uri": "tidal:track:21600906:519451842:519451850", "translated": "https://amz-pr-fa.audio.tidal.com/..." }
```

If no backend handles the URI's scheme, you will receive an HTTP 404 response (RPC code -32010). If the backend fails or declines to translate, you should usually get a 404 or 500 status code (RPC code -32011) along with a specific error message, if one was raised.

## Project resources

- [Source code](https://github.com/shayypy/mopidy-reveal)
- [Issues](https://github.com/shayypy/mopidy-reveal/issues)
- [Releases](https://github.com/shayypy/mopidy-reveal/releases)


## Development

### Set up development environment

Clone the repo using, e.g. using [gh](https://cli.github.com/):

```sh
gh repo clone shayypy/mopidy-reveal
```

Enter the directory, and install dependencies using [uv](https://docs.astral.sh/uv/):

```sh
cd mopidy-reveal/
uv sync
```

### Running tests

To run all tests and linters in isolated environments, use
[tox](https://tox.wiki/):

```sh
tox
```

To only run tests, use [pytest](https://pytest.org/):

```sh
pytest
```

To format the code, use [ruff](https://docs.astral.sh/ruff/):

```sh
ruff format .
```

To check for lints with ruff, run:

```sh
ruff check .
```

To check for type errors, use [pyright](https://microsoft.github.io/pyright/):

```sh
pyright .
```

### Setup before first release

Before the first release, you must [enable trusted publishing on
PyPI](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
so that the `release.yml` GitHub Action can create the PyPI project and publish
releases to PyPI.

When following the instructions linked above, use the following values in the
form at PyPI:

- Publisher: GitHub
- PyPI project name: `mopidy-reveal`
- Owner: `shayypy`
- Repository name: `mopidy-reveal`
- Workflow name: `release.yml`
- Environment name: `pypi` (must match environment name in `release.yml`)

### Making a release

To make a release to PyPI, go to the project's [GitHub releases
page](https://github.com/shayypy/mopidy-reveal/releases)
and click the "Draft a new release" button.

In the "choose a tag" dropdown, select the tag you want to release or create a
new tag, e.g. `v0.1.0`. Add a title, e.g. `v0.1.0`, and a description of the changes.

Decide if the release is a pre-release (alpha, beta, or release candidate) or
should be marked as the latest release, and click "Publish release".

Once the release is created, the `release.yml` GitHub Action will automatically
build and publish the release to
[PyPI](https://pypi.org/project/mopidy-reveal/).


## Credits

- Original author: [Shay](https://github.com/shayypy)
- Current maintainer: [Shay](https://github.com/shayypy)
- [Contributors](https://github.com/shayypy/mopidy-reveal/graphs/contributors)

This repository was created from [mopidy-ext-template](https://github.com/mopidy/mopidy-ext-template). Some information related to package distribution may be inaccurate.
