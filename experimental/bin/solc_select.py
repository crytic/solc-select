import os
import sys

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
