#!/bin/bash
export LD_LIBRARY_PATH=/home/ankit/.local/gmslibs/usr/lib/x86_64-linux-gnu
BIN=/home/ankit/.cache/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-linux64/chrome-headless-shell
mkdir -p /home/ankit/.local/gmslibs
cd /home/ankit/debs || exit 1
for p in libasound2t64 libasound2 libgbm1 libxkbcommon0 libdrm2 libx11-6 libxcb1 libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 libpango-1.0-0 libcairo2 libatspi2.0-0t64 libcups2t64 libatk1.0-0t64 libatk-bridge2.0-0t64 libdbus-1-3 libexpat1 libglib2.0-0t64 libfontconfig1 libx11-xcb1; do
  apt-get download "$p" >/dev/null 2>&1 || true
done
for f in *.deb; do
  [ -e "$f" ] && dpkg-deb -x "$f" /home/ankit/.local/gmslibs/ 2>/dev/null
done
echo "=== still missing ==="
ldd "$BIN" | grep "not found" | sort -u
echo "=== chromium version ==="
"$BIN" --version
