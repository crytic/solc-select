#!/bin/bash

source semver.sh

function download {
    version="$1"
    url="$2"
    to="$3"

    curl -s -f -L "$url" -o "$to" && chmod +x "$to"

    if [[ $? -eq 0 ]]; then
        echo "[+] successfully downloaded solc $version"
    else
        echo "[+] failed to download solc $version"
    fi
}
function download_official_release {
    version="$1"
    asset_name="$2"
    target_location="$3"

    download "$version" "https://github.com/ethereum/solidity/releases/download/v${version}/${asset_name}" "$target_location"
}
function download_crytic_build {
    version="$1"
    target_location="$2"

    download "$version" "https://github.com/crytic/solc/raw/master/linux/amd64/solc-v${version}" "$target_location"
}

function install_solc_too_old {
    version="$1"
    target_location="$2"

    echo "[+] $version is too old, not installing"
}
function install_solc_crytic {
    version="$1"
    target_location="$2"

    download_crytic_build "$version" "$target_location"
}
function install_solc_0_4_10 {
    version="$1"
    target_location="$2"

    download_official_release "$version" "solc" "$target_location"
}
function install_solc_0_4_11_plus {
    version="$1"
    target_location="$2"

    download_official_release "$version" "solc-static-linux" "$target_location"
}

function install_solc {
    version="$1"

    target_location="$SSELECT_INSTALL_DIR/usr/bin/solc-v${version}"

    if [[ -f ${target_location} ]] && [[ ${FORCE} -ne 1 ]]; then
        echo "[+] ${version} is already installed"
        return 0
    fi

    if $(semverLt "$version" "0.4.0"); then
        install_solc_too_old "$version" "$target_location"
    elif $(semverLt "$version" "0.4.10"); then
        install_solc_crytic "$version" "$target_location"
    elif $(semverLt "$version" "0.4.11"); then
        install_solc_0_4_10 "$version" "$target_location"
    else
        install_solc_0_4_11_plus "$version" "$target_location"
    fi
}

function solc_releases_with_page {
  page="$1"

  curl --silent "https://api.github.com/repos/ethereum/solidity/releases?per_page=100&page=$page" |
    grep '"tag_name":' |
    sed -E 's/.*"v([^"]+)".*/\1/'
}

function solc_releases {
    result=""

    page="1"
    while : ; do
        tags="$(solc_releases_with_page "$page")"
        printf -v result '%s%s\n' "$result" "$tags"

        if [[ "$(echo "$tags" | wc -l)" != "100" ]]; then
            break
        fi

        page=$((page+1))
    done

    result=$(echo "$result" | sort -t. -k 1,1nr -k 2,2nr -k 3,3nr)
    echo "$result"
}

if [ ! -z "$SSELECT_INSTALL_DIR" ]; then
  echo "Installing solc versions into $SSELECT_INSTALL_DIR/usr/bin"
fi

for release in $(solc_releases); do
    if [[ ! -z "$SOLC_AFTER" ]] && semverLt "$release" "$SOLC_AFTER"; then
        break # we can break since the list of releases is sorted
    fi
    if [[ ! -z "$SOLC_BEFORE" ]] && ! semverLt "$release" "$SOLC_BEFORE"; then
        continue # skip until we hit the version we care about
    fi
    install_solc "$release" || true
done
