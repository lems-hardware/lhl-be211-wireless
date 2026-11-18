#!/bin/sh
# Run with sudo in macOS, then join an open 2.4 GHz network and try Safari when prompted.
set -eu

interface=en0
out=/Volumes/FILES/wifi-logs/wifi-logs-30.txt

if [ "$(id -u)" -ne 0 ]; then
    echo 'Run this script with sudo.' >&2
    exit 1
fi
if [ ! -d "${out%/*}" ] || ! ifconfig "$interface" >/dev/null 2>&1; then
    echo 'Mount FILES with its wifi-logs folder and check that en0 exists.' >&2
    exit 1
fi
if [ -e "$out" ]; then
    echo "Move the existing $out aside before collecting again." >&2
    exit 1
fi

scratch=$(mktemp -d "${TMPDIR:-/tmp}/lhl-wifi-101.XXXXXXXX")
packet_pid=
summary_pid=

stop_job() {
    if [ -n "$1" ]; then
        kill "$1" 2>/dev/null || :
        wait "$1" 2>/dev/null || :
    fi
}

cleanup() {
    stop_job "$packet_pid"
    stop_job "$summary_pid"
    rm -f "$scratch/packets" "$scratch/summary"
    rmdir "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

timestamp() {
    date '+%Y-%m-%d %H:%M:%S %z'
}

last_window_start() {
    dmesg | grep -F 'BE211 probe: BSD packet window started' | tail -n 1
}

sample_summary() (
    query_pid=
    trap 'stop_job "$query_pid"; exit 0' TERM INT
    for sample in $(seq 1 21); do
        printf '\nSummary request at %s\n' "$(timestamp)"
        ipconfig getsummary "$interface" &
        query_pid=$!
        wait "$query_pid" || :
        query_pid=
        printf 'Summary returned at %s\n' "$(timestamp)"
        dmesg | grep -E 'BE211 probe: BSD (link heartbeat|packet window complete)' | tail -n 2
        sleep 15
    done
)

baseline=$(last_window_start)
tcpdump -p -i "$interface" -nn -e -tttt -l 'arp or (ip and (port 53 or (udp and (port 67 or port 68)) or (tcp port 443 and (tcp[13] & 7 != 0))))' \
    > "$scratch/packets" 2>&1 &
packet_pid=$!
for check in 1 2 3 4 5; do
    if grep -q 'listening on' "$scratch/packets"; then
        break
    fi
    kill -0 "$packet_pid" 2>/dev/null || break
    sleep 1
done
if ! grep -q 'listening on' "$scratch/packets"; then
    cat "$scratch/packets" >&2
    echo 'Packet capture did not start.' >&2
    exit 1
fi

started_at=$(timestamp)
window=
detected_at=
echo 'Turn Wi-Fi on and select an open 2.4 GHz network if macOS has not already joined it.'
for poll in $(seq 1 40); do
    marker=$(last_window_start)
    if [ -n "$marker" ] && [ "$marker" != "$baseline" ]; then
        window=$marker
        detected_at=$(timestamp)
        break
    fi
    sleep 1
done
if [ -n "$window" ]; then
    sample_summary > "$scratch/summary" 2>&1 &
    summary_pid=$!
    echo 'Wi-Fi test window started. Load https://example.com/ in Safari now.'
    echo 'Keep Wi-Fi on. I will prompt for another page load in 4 minutes 30 seconds.'
    sleep 270
    echo 'Load https://example.com/?attempt=101-late in Safari now.'
    echo 'Leave Wi-Fi on until Saved. Saving the capture does not disconnect Wi-Fi.'
    sleep 37
fi

stop_job "$packet_pid"
packet_pid=
# Keep the timed observations independent of a delayed IPConfiguration request.
stop_job "$summary_pid"
summary_pid=
ended_at=$(timestamp)

{
    printf 'Collector started at %s\nCollector stopped at %s\n' "$started_at" "$ended_at"
    sysctl kern.boottime
    if [ -n "$window" ]; then
        printf 'Window detected at %s\n%s\n' "$detected_at" "$window"
        printf '\n--- IPConfiguration snapshots ---\n'
        cat "$scratch/summary"
    else
        echo 'No new BSD packet window detected.'
    fi
    printf '\n--- en0 DHCP, ARP, DNS and TCP connection packets ---\n'
    cat "$scratch/packets"
    printf '\n--- Driver trace ---\n'
    dmesg | grep -Ei 'BE211 probe|WCL join|firmware error|SYSASSERT' || :
    printf '\n--- IPConfiguration log ---\n'
    log show --last 6m --info --style compact \
        --predicate 'subsystem == "com.apple.IPConfiguration"' || :
    printf '\n--- macOS Wi-Fi join and leave log ---\n'
    log show --last 6m --info --style compact \
        --predicate '(process == "airportd" OR process == "wifid") AND (eventMessage CONTAINS[c] "join" OR eventMessage CONTAINS[c] "leave" OR eventMessage CONTAINS[c] "disassoc" OR eventMessage CONTAINS[c] "deauth" OR eventMessage CONTAINS[c] "abort" OR eventMessage CONTAINS[c] "cancel" OR eventMessage CONTAINS[c] "link")' || :
} > "$out" 2>&1
printf 'Saved %s\n' "$out"
