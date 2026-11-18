#!/usr/bin/env bash
set -euo pipefail

prefix=$(realpath -m "$1")
checkout=$(realpath -m "$2")
revision=9fc3e04656050ddc33d24c036ab822249af4ceee

if [[ -x "$prefix/bin/x86_64-apple-darwin-ld" ]]; then
    exit 0
fi
git init "$checkout"
git -C "$checkout" remote add origin https://github.com/tpoechtrager/cctools-port.git
git -C "$checkout" fetch --depth 1 origin "$revision"
git -C "$checkout" checkout --detach FETCH_HEAD
test "$(git -C "$checkout" rev-parse HEAD)" = "$revision"
cd "$checkout/cctools"
./configure --prefix="$prefix" --target=x86_64-apple-darwin \
    --disable-lto-support --disable-tapi-support
make -j2
make install
test -x "$prefix/bin/x86_64-apple-darwin-ld"
