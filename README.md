# solc-select

A tool to quickly switch between Solidity compiler versions.

The tool is split into two CLI utilities:

- `solc-select`: manages installing and setting different `solc` compiler versions
- `solc`: wrapper around `solc` which picks the right version according to what was set via `solc-select`

The `solc` binaries are downloaded from https://binaries.soliditylang.org/ which contains
official artifacts for many historial and modern `solc` versions for Linux and macOS.

The versioned binaries are stored in `~/.solc-select/artifacts/`.

## Installation

### Using pip

```bash
pip3 install solc-select
```

### Using uv (recommended for development)

```bash
uv tool install solc-select
```

To automatically install and use a version, run `solc-select use <version> --always-install`.

### Running on ARM (Mac M1/M2)

`solc-select` provides native ARM64 support for versions 0.8.5-0.8.23, and universal binary support for 0.8.24+. For versions older than 0.8.5, Rosetta is required. See the FAQ on [how to install Rosetta](#oserror-errno-86-bad-cpu-type-in-executable).

## Usage

### Quick Start

```bash
# Install and set a specific Solidity version
solc-select use 0.8.19 --always-install

# Check the current version
solc --version
```

### Managing Versions

The global version of `solc` will automatically be set to the latest version. You can change this with the `solc-select use <version>` command:

```shell
$ solc --version
solc, the solidity compiler commandline interface
Version: 0.5.2+commit.1df8f40c.Linux.g++
$ solc-select use 0.4.24
Switched global version to 0.4.24
$ solc --version
solc, the solidity compiler commandline interface
Version: 0.4.24+commit.e67f0147.Linux.g++
```

Use `SOLC_VERSION` environment variable to override the global version:

```shell
$ solc --version
solc, the solidity compiler commandline interface
Version: 0.4.24+commit.e67f0147.Linux.g++
$ SOLC_VERSION=0.5.2 solc --version
solc, the solidity compiler commandline interface
Version: 0.5.2+commit.1df8f40c.Linux.g++
```

By default, solc-select will halt if you try to use a version that you do not have installed already. Use the `--always-install` flags to bypass this.

```shell
$ solc-select use 0.8.1 --always-install
Installing '0.8.1'...
Version '0.8.1' installed.
```

### Available Commands

```shell
# List all available versions
solc-select install

# Install a specific version
solc-select install 0.8.19

# Switch to an installed version
solc-select use 0.8.19

# List installed versions
solc-select versions

# Install and switch to a version in one command
solc-select use 0.8.19 --always-install
```

## Getting Help

Feel free to stop by our [Slack channel](https://empirehacking.slack.com/) for help on using or extending `solc-select`.

## FAQ

### OSError: [Errno 86] Bad CPU type in executable

On newer `solc-select` versions, this might show as `solc binaries for macOS are
Intel-only. Please install Rosetta on your Mac to continue.` or `solc binaries
previous to 0.8.5 for macOS are Intel-only. Please install Rosetta on your Mac
to continue.`

`solc` releases earlier than 0.8.5 require Rosetta to be installed. Versions 0.8.5-0.8.23 run natively on ARM64, and 0.8.24+ use universal binaries. To see
whether you have Rosetta installed on your Mac, run

```bash
pgrep -q oahd && echo Rosetta is installed || echo Rosetta is NOT installed
```

If it is not installed, it can be installed with the command

```bash
/usr/sbin/softwareupdate --install-rosetta --agree-to-license
```

### solc-version not changing after running `solc-select use [version]` or setting `SOLC_VERSION`

Uninstall other installations of solc on your machine. `solc-select` re-installs solc binaries for your operating system and acts as a wrapper for solc. With duplicate solc installations, this may result in your `solc` version not being up to date.

### "Unsupported Platform" on Windows

You might be using an old version of `solc-select` or Python if you are seeing this error message. The current stable release supports Windows; try upgrading your `solc-select` installation with the following command.

```bash
pip install --upgrade solc-select
```

## Known Issues

### `SSL: CERTIFICATE_VERIFY_FAILED` on running `solc-select` commands [investigation ongoing]

**OS X**: Python distributions on OS X has no certificates and cannot validate SSL connections, a breaking change introduced in Python 3.6. See [StackOverflow](https://stackoverflow.com/a/42334357) post for additional details.

The following commands may resolve the issue; adjust the Python version to the one installed on your system:

```bash
pip3 install certifi
/Applications/Python\ 3.8/Install\ Certificates.command
```

### `Connection refused` [investigation ongoing]

Our `0.2.1` version of `solc-select` pulls older Linux binaries from [crytic/solc](https://github.com/crytic/solc) which seems to have introduced unexpected behavior in certain instances. Apparently, [certain ISPs such as Jio](https://github.com/crytic/solc-select/issues/205#issuecomment-1825171056) may be blocking access to certain GitHub domains. If possible, try using a different Internet provider to see if it resolves the problem.

Alternatively, try downgrading to `solc-select version 0.2.0`.

```bash
pip3 uninstall solc-select
pip3 install solc-select==0.2.0
solc-select install
```

### `solc-select` version changes, but `solc --version does not match`

Users seem to be experiencing situations in which the following command is successful:

```bash
solc-select use <version>
```

However, when running the following command, it points to an older version of Solidity.

```bash
solc --version
```

`solc-select` is intended to work with custom binaries. This means that Solidity installed through other means (i.e: `brew install solidity`) will _not_ work!.

Uninstall other versions Solidity from your computer.

## License

`solc-select` is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](mailto:opensource@trailofbits.com) if you’re looking for an exception to the terms.
