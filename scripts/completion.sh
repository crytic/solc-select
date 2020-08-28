#!/bin/bash

function _listversions()
{
    local cur
    COMPREPLY=()
    cur=${COMP_WORDS[COMP_CWORD]}
    line=${COMP_LINE}
    case "$line" in
      *use*)
         COMPREPLY=($( compgen -W "$(ls ~/.solc-select/usr/bin/ | grep 'solc-v' | cut -d 'v' -f 2)" -- $cur ) )
    esac
}

complete -F _listversions solc
