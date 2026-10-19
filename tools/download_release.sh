#!/usr/bin/env bash
set -euo pipefail
release_tag=v3-rtx3090-offline-20261019
destination="${1:-release-download}"
mkdir -p "$destination"
gh release download "$release_tag" --repo UESlubei/infertol20 --dir "$destination" --skip-existing
echo "Downloaded into: $destination"
echo "cd '$destination' && sha256sum -c SHA256SUMS.parts"
