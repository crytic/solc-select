from setuptools import find_packages, setup

setup(
    name="solc-select",
    description="Manage multiple Solidity compiler versions.",
    url="https://github.com/crytic/solc-select",
    author="Trail of Bits",
    version="1.0.0.0",
    packages=find_packages(),
    python_requires=">=3.6",
    license="AGPL-3.0",
    # pylint: disable=consider-using-with
    long_description=open("README.md", encoding="utf8").read(),
    entry_points={
        "console_scripts": [
            "solc-select = solc_select.__main__:solc_select",
            "solc = solc_select.__main__:solc",
        ]
    },
    install_requires=["pysha3", "packaging"],
)
