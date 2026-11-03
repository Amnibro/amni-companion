#!/bin/bash
cd "$(dirname "$0")/../web" && exec python3 -m http.server "${1:-7437}" --bind 127.0.0.1
