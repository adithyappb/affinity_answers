#!/usr/bin/env bash
#
# List company name, location and founding year from the S&P 500 constituents
# CSV, sorted by founding year (oldest first).
#
# Usage:
#   ./companies_by_founding_year.sh <csv-url-or-local-file>
#
# Example:
#   ./companies_by_founding_year.sh \
#     https://raw.githubusercontent.com/datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv
#
# Output: tab-separated  Company<TAB>Location<TAB>Founded  (aligned when printed
# to a terminal). Rows with no parsable year are listed last.

set -euo pipefail

usage() { echo "usage: $(basename "$0") <csv-url-or-file>" >&2; exit 2; }
[[ $# -eq 1 ]] || usage
src=$1

read_source() {
    if [[ $src =~ ^https?:// ]]; then
        if command -v curl >/dev/null; then
            curl -fsSL --retry 2 "$src"
        elif command -v wget >/dev/null; then
            wget -qO- "$src"
        else
            echo "error: need curl or wget to download $src" >&2; exit 1
        fi
    elif [[ -r $src ]]; then
        cat -- "$src"
    else
        echo "error: '$src' is neither a URL nor a readable file" >&2; exit 1
    fi
}

# POSIX awk (works with gawk, mawk and BSD awk): a small CSV field splitter
# that honours "quoted, fields" and "" escapes, then picks columns by header
# name so the script survives column reordering.
extract() {
    awk '
    function parse_csv(line, f,    n, i, c, field, inq) {
        n = 0; field = ""; inq = 0
        for (i = 1; i <= length(line); i++) {
            c = substr(line, i, 1)
            if (inq) {
                if (c == "\"" && substr(line, i + 1, 1) == "\"") { field = field "\""; i++ }
                else if (c == "\"") inq = 0
                else field = field c
            } else if (c == "\"") inq = 1
            else if (c == ",")    { f[++n] = field; field = "" }
            else                  field = field c
        }
        f[++n] = field
        return n
    }
    { sub(/\r$/, "") }                                   # tolerate CRLF files
    NR == 1 {
        n = parse_csv($0, h)
        for (i = 1; i <= n; i++) col[h[i]] = i
        if (!("Security" in col) || !("Headquarters Location" in col) || !("Founded" in col)) {
            print "error: CSV lacks Security / Headquarters Location / Founded columns" > "/dev/stderr"
            exit 1
        }
        print "Year\tCompany\tLocation\tFounded"
        next
    }
    NF == 0 { next }
    {
        parse_csv($0, f)
        founded = f[col["Founded"]]
        # Sort key = first 4-digit year: "2013 (1888)" -> 2013 (current entity).
        year = match(founded, /[0-9][0-9][0-9][0-9]/) ? substr(founded, RSTART, 4) : 9999
        printf "%s\t%s\t%s\t%s\n", year, f[col["Security"]], f[col["Headquarters Location"]], founded
    }'
}

# Sort everything except the header line.
sort_body() {
    IFS= read -r header && printf '%s\n' "$header"
    LC_ALL=C sort -t $'\t' -k1,1n -k2,2
}

render() {
    if [[ -t 1 ]] && command -v column >/dev/null; then column -t -s $'\t'; else cat; fi
}

read_source | extract | sort_body | cut -f2- | render
