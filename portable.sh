#!/bin/sh
set -eu
app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Each computer has its own points; no personal baseline is shipped in the portable ZIP.
if [ ! -x /usr/bin/python3 ]; then
    echo 'Python 3 is required at /usr/bin/python3.' >&2
    exit 1
fi
if [ "${1:-}" = "--tui" ] || { [ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ]; }; then
    export LINUX_FRESH_POINT_PORTABLE=1
    /usr/bin/python3 -I "$app_dir/dependency_check.py" --tui
    exec /usr/bin/python3 -I "$app_dir/tui.py"
fi
/usr/bin/python3 -I "$app_dir/dependency_check.py"
exec /usr/bin/python3 -I "$app_dir/portable.py" "$@"
