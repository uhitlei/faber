#!/bin/bash
# Faber — thin wrapper. The real installer ships with the plugin payload so
# that /faber:install and this script are always the same code path.
# Usage: ./install.sh [<target-repo>] [options]   (see plugins/faber/install.sh --help)
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/plugins/faber/install.sh" "$@"
