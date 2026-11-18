import os
from pathlib import Path
import re
import runpy
from unittest.mock import patch
import subprocess
import concurrent.futures
import plistlib

import argparse

parser = argparse.ArgumentParser(description='Cross-build the Sequoia Debug kext from the prepared checkout.')
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('ld64', type=Path)
args = parser.parse_args()
source, output, linker = (path.resolve() for path in (args.source, args.output, args.ld64))
os.chdir(source)
output.mkdir(parents=True, exist_ok=True)
project = (source / 'itlwm.xcodeproj/project.pbxproj').read_text()
phase = project.split('AFFBDFD057C2402C908ECB89 /* Sources */ = {', 1)[1].split(');', 1)[0]
sources = []
for name in re.findall(r'/\* (\S+\.(?:c|cpp)) in Sources \*/', phase):
    candidates = list(source.rglob(name))
    if name == 'FwBinary.cpp':
        path = source / 'include' / name
    elif len(candidates) == 1:
        path = candidates[0]
    else:
        raise ValueError((name, candidates))
    sources.append(path)
# The upstream generator uses filesystem order. Pin the tested order so
# extracting the source archive on another filesystem preserves the binary.
firmware = source / 'itlwm/firmware'
firmware_order = Path(__file__).resolve().with_name('firmware-order.txt').read_text().splitlines()
if set(firmware_order) != {file.name for file in firmware.iterdir()}:
    raise ValueError('Firmware inputs differ from the Attempt 101 source archive')
generator = runpy.run_path(str(source / 'scripts/zlib_compress_fw.py'))
with patch.object(os, 'walk', return_value=[(str(firmware), [], firmware_order)]):
    generator['process_files'](str(source / 'include/FwBinary.cpp'), str(firmware))
common = [
    '--target=x86_64-apple-macos15.2', '-mkernel', '-fno-builtin',
    '-fno-stack-protector', '-mno-red-zone', '-fno-common',
    '-fvisibility=hidden', '-nostdinc', '-O0', '-w',
    '-isystem', 'MacKernelSDK/Headers', '-Iitl80211/openbsd',
    '-Iitl80211', '-Iinclude', '-Iinclude/Airport', '-Iitl80211/linux', '-Iitlwm/hal_iwm', '-Iitlwm/hal_iwn', '-Iitlwm/hal_iwx',
    '-DKERNEL=1', '-DKERNEL_PRIVATE=1', '-DDEBUG=1',
    '-DIEEE80211_STA_ONLY', '-DAIRPORT_WCL', '-DAIRPORT_VTD',
    '-DAIRPORT', '-D__IO80211_TARGET=__MAC_15_2', '-D__PRIVATE_SPI__',
    '-DIO80211FAMILY_V2', '-DITLWM_VERSION="2.4.0"',
    '-DGIT_COMMIT="_BE211_OPEN_NETWORKS_1"', '-include', 'itlwm/PrivateSPI.pch',
]
objects = output / 'objects'
objects.mkdir(exist_ok=True)

def compile_source(path):
    obj = objects / (path.name + '.o')
    result = subprocess.run(['clang++', *common, '-std=gnu++14', '-fapple-kext',
        '-fno-exceptions', '-fno-rtti', '-fno-use-cxa-atexit',
        '-fno-register-global-dtors-with-atexit', '-mllvm',
        '-disable-atexit-based-global-dtor-lowering', '-x', 'c++',
        '-c', path, '-o', obj], capture_output=True, text=True)
    (objects / (path.name + '.log')).write_text(result.stderr)
    if result.returncode:
        print(path, result.stderr.splitlines()[:12], flush=True)
        return None
    return obj

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    compiled = list(pool.map(compile_source, sources))
if any(obj is None for obj in compiled):
    raise SystemExit('Compilation failed')

metadata = output / 'AirportItlwm_info.c'
metadata.write_text('''#include <mach/mach_types.h>
extern kern_return_t _start(kmod_info_t *, void *);
extern kern_return_t _stop(kmod_info_t *, void *);
KMOD_EXPLICIT_DECL(com.zxystd.AirportItlwm, "2.4.0", _start, _stop)
__private_extern__ kmod_start_func_t *_realmain = 0;
__private_extern__ kmod_stop_func_t *_antimain = 0;
''')
info = objects / 'AirportItlwm_info.o'
subprocess.run(['clang', *common[:common.index('-isystem')], '-isystem', 'MacKernelSDK/Headers',
                '-DKERNEL=1', '-DKERNEL_PRIVATE=1', '-c', metadata, '-o', info],
               check=True)
bundle = output / 'AirportItlwm.kext' / 'Contents'
(bundle / 'MacOS').mkdir(parents=True, exist_ok=True)
subprocess.run([linker, '-arch', 'x86_64', '-kext', '-static', '-undefined',
                'dynamic_lookup', '-macosx_version_min', '15.2', '-o',
                bundle / 'MacOS/AirportItlwm', *compiled, info,
                'MacKernelSDK/Library/x86_64/libkmod.a'], check=True)
plist = plistlib.loads((source / 'AirportItlwm/WCL/Sequoia-Info.plist').read_bytes())
values = {'DEVELOPMENT_LANGUAGE':'en','EXECUTABLE_NAME':'AirportItlwm',
          'PRODUCT_BUNDLE_IDENTIFIER':'com.zxystd.AirportItlwm',
          'PRODUCT_NAME':'AirportItlwm','PRODUCT_BUNDLE_PACKAGE_TYPE':'KEXT',
          'MODULE_VERSION':'2.4.0'}
for key, value in plist.items():
    if isinstance(value, str) and value.startswith('$('):
        plist[key] = values[value[2:-1]]
(bundle / 'Info.plist').write_bytes(plistlib.dumps(plist))
