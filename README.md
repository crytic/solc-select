# solc-select
A script to quickly switch between Solidity compiler versions.

It is becoming increasingly hard to run older versions of `solc`,
particularly on macOS since there are no official binary releases.
Versions prior to 0.5.0 no longer compile on macOS and are not
maintained. This is a problem because older Ethereum contracts no
longer compile on modern versions of Solidity. `solc-select` is a
utility that allows one to run _any_ legacy version of Solidity simply
by setting an environment variable.

## Quickstart

```
docker pull trailofbits/solc-select
```

Ensure that `solc` is _not_ installed on your host system. Instead, copy [this special solc script](bin/solc) to anywhere in your PATH.

If you do not wish to replace your local copy of `solc`, name [the special solc script](bin/solc) `solc-select` instead.

## Usage

The desired version of `solc` can be specified using the `SOLC_VERSION` environment varialble. By default, the latest version is used.

```
$ solc --version
solc, the solidity compiler commandline interface
Version: 0.5.2+commit.1df8f40c.Linux.g++
$ SOLC_VERSION=0.4.24 solc --version
solc, the solidity compiler commandline interface
Version: 0.4.24+commit.e67f0147.Linux.g++
```

## Upgrading

If everything is working properly, the [DockerHub image for `solc-select`](https://hub.docker.com/r/trailofbits/solc-select) will automatically update every time Solidity is updated.
Therefore, simply run
```
docker pull trailofbits/solc-select
```
to ensure that you have the latest version.

## Installation from Source

```
$ git clone https://github.com/trailofbits/solc-select.git
$ cd solc-select
$ docker build -t trailofbits/solc-select:latest .
$ export PATH=$PWD/bin:$PATH
```

or copy `bin/solc` into a directory within your `PATH`.

## Getting Help

Feel free to stop by our [Slack channel](https://empirehacking.slack.com/) for help on using or extending `solc-select`.

## License

`solc-select` is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](mailto:opensource@trailofbits.com) if you’re looking for an exception to the terms.