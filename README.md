# solc-select
A script to quickly switch between Solidity compiler versions

```
$ git clone https://github.com/trailofbits/solc-select.git
$ cd solc-select
$ docker build -t trailofbits/solc-select:latest .
$ export PATH=$PWD/bin:$PATH
$ solc --version
solc, the solidity compiler commandline interface
Version: 0.5.2+commit.1df8f40c.Linux.g++
$ SOLC_VERSION=0.4.24 solc --version
solc, the solidity compiler commandline interface
Version: 0.4.24+commit.e67f0147.Linux.g++
```
