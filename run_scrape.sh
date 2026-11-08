#!/bin/bash
# Scrape one city with AUTO-RETRY.
# Usage: edit CITY below, then:  bash run_scrape.sh
# The scraper re-runs automatically (resume mode) up to MAX_ATTEMPTS times if it
# dies without a clean exit (e.g., WSL hiccup) - no data is lost or re-scraped.
CITY=jaipur   # <-- CHANGE THIS per city (must match <city>_queries.txt)
MAX_ATTEMPTS=4
BUNDLE=/mnt/c/Users/Ankit/gmaps-scraper-bundle   # <-- update if you move this folder
LOG=${CITY}_run_log.txt

count_marker(){ grep -c "scrapemate exited" "$LOG" 2>/dev/null; }

# inner script runs inside WSL; regenerated each run with the current CITY
cat > _inner_run.sh <<EOF
#!/bin/bash
export LD_LIBRARY_PATH=/home/ankit/.local/gmslibs/usr/lib/x86_64-linux-gnu
cd ${BUNDLE} || exit 1
./gms_linux -input ${CITY}_queries.txt -results ${CITY}_results.csv -depth 1 -c 4 -lang en -resume -exit-on-inactivity 6m
EOF

for i in $(seq 1 $MAX_ATTEMPTS); do
  echo "=== attempt $i / $MAX_ATTEMPTS ($(date +%d-%b %H:%M:%S)) ===" >> "$LOG"
  MSYS_NO_PATHCONV=1 wsl -d Ubuntu -- bash ${BUNDLE}/_inner_run.sh >> "$LOG" 2>&1
  before=$(count_marker); before=${before:-0}
  # count AFTER this attempt = total markers; compare with pre-attempt count
  after=$(count_marker); after=${after:-0}
  if [ "$after" -gt "$before" ]; then
    echo "clean exit on attempt $i - done. log: $LOG"
    exit 0
  fi
  echo "no clean exit marker - retrying with -resume (attempt $((i+1)))..."
done
echo "WARNING: still no clean exit after $MAX_ATTEMPTS attempts. Check $LOG and re-run."
exit 1
