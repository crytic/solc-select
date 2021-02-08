import json
import os
import re
import sys
import urllib.request

home_dir = os.path.expanduser('~')
solc_select_dir = f"{home_dir}/.solc-select"
artifacts_dir = f"{solc_select_dir}/artifacts"
os.makedirs(artifacts_dir, exist_ok=True)

def current_version():
    version = os.environ.get('SOLC_VERSION')
    source = 'SOLC_VERSION'
    if version:
        if version not in installed_versions():
            print(f"Version '{version}' not installed (set by {source}). Run `solc-select install {version}`.")
            sys.exit(1)
    else:
        source = f"{solc_select_dir}/global-version"
        if os.path.isfile(source):
            with open(source) as f: version = f.read()
        else:
            # TODO: figure out a better place for this message
            print('No solc version set. Run `solc-select use VERSION` or set SOLC_VERSION environment variable.')
            return None
    return (version, source)

def installed_versions():
    return [f.replace('solc-', '') for f in sorted(os.listdir(artifacts_dir))]


# TODO: accept versions in range
def install_artifacts(versions):
    releases = get_available_versions()

    for version, artifact in releases.items():
        if 'all' not in versions:
            if versions and version not in versions:
                continue

        url = f"https://binaries.soliditylang.org/{soliditylang_platform()}/{artifact}"
        artifact_file = f"{artifacts_dir}/solc-{version}"
        print(f"Installing '{version}'...")
        urllib.request.urlretrieve(url, artifact_file)
        # NOTE: we could verify checksum here because the list.json file
        # provides checksums for artifacts, however those are keccak256 hashes
        # which are not possible to compute without additional dependencies
        os.chmod(artifact_file, 0o775)
        print(f"Version '{version}' installed.")

def switch_global_version(version):
    if version in installed_versions():
        with open(f"{solc_select_dir}/global-version", "w") as f:
            f.write(version)
        print("Switched global version to", version)
    elif version in get_available_versions():
        print(f"You need to install '{version}' prior to using it. Use `solc-select install {version}`")
        sys.exit(1)
    else:
        print(f"Unknown version '{version}'.")
        sys.exit(1)

def valid_version(version):
    # check that it matches <digit>.<digit>.<digit>
    match = re.search("^(\d+).(\d+).(\d+)$", version)
    if match is None:
        raise argparse.ArgumentTypeError(f"Invalid version '{version}'.")
    return version

def valid_install_arg(arg):
    if arg == 'all':
        return arg
    else:
        return valid_version(arg)

def get_installable_versions():
    return set(get_available_versions()) - set(installed_versions())

def get_available_versions():
    url = f"https://binaries.soliditylang.org/{soliditylang_platform()}/list.json"
    list_json = urllib.request.urlopen(url).read()
    return json.loads(list_json)["releases"]

def soliditylang_platform():
    if sys.platform == 'linux':
        platform = 'linux-amd64'
    elif sys.platform == 'darwin':
        platform = 'macosx-amd64'
    else:
        print("Unsupported platform.")
        sys.exit(1)
    return platform
