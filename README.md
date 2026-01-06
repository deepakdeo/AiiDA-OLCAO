[![Build Status][ci-badge]][ci-link]
[![Coverage Status][cov-badge]][cov-link]
[![Docs status][docs-badge]][docs-link]
[![PyPI version][pypi-badge]][pypi-link]

# AiiDA-OLCAO

AiiDA plugin to run and manage OLCAO calculations on HPC clusters (e.g. Hellbender at University of Missouri system)

This plugin is the default output of the
[AiiDA plugin cutter](https://github.com/aiidateam/aiida-plugin-cutter),
intended to help developers get started with their AiiDA plugins.

## Repository contents

* [`.github/`](.github/): [Github Actions](https://github.com/features/actions) configuration
  * [`ci.yml`](.github/workflows/ci.yml): runs tests, checks test coverage and builds documentation at every new commit
  * [`publish-on-pypi.yml`](.github/workflows/publish-on-pypi.yml): automatically deploy git tags to PyPI - just generate a [PyPI API token](https://pypi.org/help/#apitoken) for your PyPI account and add it to the `pypi_token` secret of your github repository
* [`aiida_olcao/`](aiida_olcao/): The main source code of the plugin package
  * [`data/`](aiida_olcao/data/): A new `OlcaoParameters` data class, used as input to the `OlcaoCalculation` `CalcJob` class
  * [`calculations.py`](aiida_olcao/calculations.py): A new `OlcaoCalculation` `CalcJob` class
  * [`cli.py`](aiida_olcao/cli.py): Extensions of the `verdi data` command line interface for the `OlcaoParameters` class
  * [`helpers.py`](aiida_olcao/helpers.py): Helpers for setting up a local AiiDA code for `dummy_olcao.sh`
  * [`parsers.py`](aiida_olcao/parsers.py): A new `Parser` for the `OlcaoCalculation`
* [`docs/`](docs/): A documentation template ready for publication on [Read the Docs](https://aiida-olcao.readthedocs.io/en/latest/)
* [`examples/`](examples/): An example of how to submit a calculation using this plugin
* [`tests/`](tests/): Basic regression tests using the [pytest](https://docs.pytest.org/en/latest/) framework (submitting a calculation, ...). Install `pip install -e .[testing]` and run `pytest`.
* [`.gitignore`](.gitignore): Telling git which files to ignore
* [`.pre-commit-config.yaml`](.pre-commit-config.yaml): Configuration of [pre-commit hooks](https://pre-commit.com/) that sanitize coding style and check for syntax errors. Enable via `pip install -e .[pre-commit] && pre-commit install`
* [`.readthedocs.yml`](.readthedocs.yml): Configuration of documentation build for [Read the Docs](https://readthedocs.org/)
* [`LICENSE`](LICENSE): License for your plugin
* [`README.md`](README.md): This file
* [`conftest.py`](conftest.py): Configuration of fixtures for [pytest](https://docs.pytest.org/en/latest/)
* [`pyproject.toml`](setup.json): Python package metadata for registration on [PyPI](https://pypi.org/) and the [AiiDA plugin registry](https://aiidateam.github.io/aiida-registry/) (including entry points)

For more information, see the [developer guide](https://aiida-olcao.readthedocs.io/en/latest/developer_guide) of your plugin.


## Features

 * Provide the OLCAO input file using `SinglefileData`:
   ```python
   SinglefileData = DataFactory('core.singlefile')
   inputs['input_file'] = SinglefileData(file='/path/to/olcao.in')
   ```

 * Specify optional parameters via `OlcaoParameters`:
   ```python
   params = { 'dummy': True }
   OlcaoParameters = DataFactory('olcao')
   inputs['parameters'] = OlcaoParameters(dict=params)
   ```

 * `OlcaoParameters` dictionaries are validated using [voluptuous](https://github.com/alecthomas/voluptuous).
   Find out about supported options:
   ```python
   OlcaoParameters = DataFactory('olcao')
   print(OlcaoParameters.schema.schema)
   ```

## Installation

```shell
pip install AiiDA-OLCAO
verdi quicksetup  # better to set up a new profile
verdi plugin list aiida.calculations  # should now show your calclulation plugins
```


## Usage

Here goes a complete example of how to submit a test calculation using this plugin.

A quick demo of how to submit a calculation:
```shell
verdi daemon start     # make sure the daemon is running
cd examples
verdi run examples/example_01.py --code olcao-dummy@localhost
verdi process list -a  # check record of calculation

If you omit `--code`, the example will create `olcao-dummy@localhost` for you.
```

The plugin also includes verdi commands to inspect its data types:
```shell
verdi data olcao list
verdi data olcao export <PK>  # prints parameters for an OlcaoParameters node
```

## Development

```shell
git clone https://github.com/deepakdeo/AiiDA-OLCAO.git
cd AiiDA-OLCAO
pip install --upgrade pip
pip install -e .[pre-commit,testing]  # install extra dependencies
pre-commit install  # install pre-commit hooks
pytest -v  # discover and run all tests
```

See the [developer guide](https://aiida-olcao.readthedocs.io/en/latest/developer_guide/index.html) for more information.

## License

MIT
## Contact

dd9wn@umkc.edu


[ci-badge]: https://github.com/deepakdeo/AiiDA-OLCAO/actions/workflows/ci.yml/badge.svg?branch=main
[ci-link]: https://github.com/deepakdeo/AiiDA-OLCAO/actions/workflows/ci.yml
[cov-badge]: https://coveralls.io/repos/github/deepakdeo/AiiDA-OLCAO/badge.svg?branch=main
[cov-link]: https://coveralls.io/github/deepakdeo/AiiDA-OLCAO?branch=main
[docs-badge]: https://readthedocs.org/projects/aiida-olcao/badge
[docs-link]: https://aiida-olcao.readthedocs.io/
[pypi-badge]: https://badge.fury.io/py/AiiDA-OLCAO.svg
[pypi-link]: https://badge.fury.io/py/AiiDA-OLCAO
