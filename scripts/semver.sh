#!/bin/bash

function semverLt() {
    left="$1"
    right="$2"

    left_major=$(echo "$left" | cut -d'.' -f1)
    right_major=$(echo "$right" | cut -d'.' -f1)
    if [[ $((left_major > right_major)) -eq 1 ]]; then
        return 1
    elif [[ $((left_major < right_major)) -eq 1 ]]; then
        return 0
    fi

    left_minor=$(echo "$left" | cut -d'.' -f2)
    right_minor=$(echo "$right" | cut -d'.' -f2)
    if [[ $((left_minor > right_minor)) -eq 1 ]]; then
        return 1
    elif [[ $((left_minor < right_minor)) -eq 1 ]]; then
        return 0
    fi

    left_patch=$(echo "$left" | cut -d'.' -f3)
    right_patch=$(echo "$right" | cut -d'.' -f3)
    if [[ $((left_patch >= right_patch)) -eq 1 ]]; then
        return 1
    fi

    return 0
}
