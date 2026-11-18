"""Validate a rebuilt bundle and package its binary, source and build record."""

import argparse
import hashlib
import json
import plistlib
import struct
import subprocess
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("bundle", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
bundle = args.bundle.resolve()
destination = args.destination.resolve()
destination.mkdir(parents=True, exist_ok=True)

def run(*command):
    return subprocess.check_output(command, text=True).strip()

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

binary = bundle / "Contents/MacOS/AirportItlwm"
data = binary.read_bytes()
magic, cpu, _, filetype, commands, command_bytes, _, _ = struct.unpack_from("<8I", data)
if (magic, cpu, filetype) != (0xFEEDFACF, 0x01000007, 11):
    raise SystemExit("Expected an x86_64 Mach-O KEXT_BUNDLE")
offset = 32
for _ in range(commands):
    command, size = struct.unpack_from("<II", data, offset)
    if size < 8 or offset + size > 32 + command_bytes:
        raise SystemExit("Invalid Mach-O load command")
    if command in (0xC, 0x80000018, 0x8000001F, 0x80000028):
        raise SystemExit("Unexpected dylib dependency or LC_MAIN")
    offset += size
if offset != 32 + command_bytes:
    raise SystemExit("Invalid load command size")
baseline = root / "kexts/AirportItlwm.kext"
if (bundle / "Contents/Info.plist").read_bytes() != (baseline / "Contents/Info.plist").read_bytes():
    raise SystemExit("Bundle plist differs from the tested preview")
plist = plistlib.loads((bundle / "Contents/Info.plist").read_bytes())
if plist["CFBundleExecutable"] != binary.name:
    raise SystemExit("Incorrect executable metadata")
def imports(path):
    return {line.split()[-1] for line in run("llvm-nm", "-u", str(path)).splitlines() if line.strip()}

expected_imports = imports(baseline / "Contents/MacOS/AirportItlwm")
actual_imports = imports(binary)
if actual_imports != expected_imports:
    print("Added imports:", sorted(actual_imports - expected_imports), flush=True)
    print("Removed imports:", sorted(expected_imports - actual_imports), flush=True)
    raise SystemExit("Undefined imports differ from the tested preview")
for marker in (b"_BE211_OPEN_NETWORKS_1", b"duration=until-disconnect", b"BSD TX ring tx="):
    if marker not in data:
        raise SystemExit(f"Missing driver marker {marker!r}")

record = {
    "commit": run("git", "-C", str(root), "rev-parse", "HEAD"),
    "compiler": run("clang++", "--version"),
    "linker": "cctools-port 9fc3e04656050ddc33d24c036ab822249af4ceee, ld64-711",
    "binary_sha256": sha256(binary),
    "matches_tested_binary": data == (baseline / "Contents/MacOS/AirportItlwm").read_bytes(),
    "validation": "Mach-O, Info.plist, imports and build markers passed",
    "hardware_test": "CI build has not been tested on hardware",
}
record_path = destination / "build-info.json"
record_path.write_text(json.dumps(record, indent=2) + "\n")
short = record["commit"][:12]
package = destination / f"AirportItlwm-BE211-{short}.zip"
with ZipFile(package, "w", compression=ZIP_DEFLATED) as archive:
    for file in sorted(bundle.rglob("*")):
        if file.is_file():
            archive.write(file, file.relative_to(bundle.parent))
    archive.write(root / "LICENSE", "LICENSE")
    archive.write(root / "licenses/LICENCE.iwlwifi_firmware", "LICENCE.iwlwifi_firmware")
    archive.write(record_path, "build-info.json")
    archive.writestr("SOURCE.txt", f"Corresponding source at commit {record['commit']}\n"
                     f"https://github.com/lems-hardware/lhl-be211-wireless/tree/{record['commit']}/source\n")
source_package = destination / f"AirportItlwm-BE211-source-{short}.zip"
with ZipFile(source_package, "w", compression=ZIP_DEFLATED) as archive:
    for file in sorted((root / "source").iterdir()):
        if file.is_file():
            archive.write(file, file.relative_to(root))
    archive.write(root / "LICENSE", "LICENSE")
    archive.write(root / "licenses/LICENCE.iwlwifi_firmware", "licenses/LICENCE.iwlwifi_firmware")
for archive_path in (package, source_package):
    with ZipFile(archive_path) as archive:
        if archive.testzip():
            raise SystemExit("ZIP verification failed")
(destination / "SHA256SUMS").write_text("".join(
    f"{sha256(file)}  {file.name}\n" for file in sorted(destination.iterdir()) if file.is_file()
    and file.name != "SHA256SUMS"
))
print(json.dumps(record, indent=2))
