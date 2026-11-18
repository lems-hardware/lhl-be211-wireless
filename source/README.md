# Attempt 101 source and build

The [corresponding source archive](AirportItlwm-BE211-attempt-101-source.tar.gz) contains the patched AirportItlwm tree, the firmware inputs and the prepared MacKernelSDK. The [cumulative patch](be211-runtime.patch) applies to [AirportItlwm-BE200 FIX31-20261109](https://github.com/Ersiter/AirportItlwm-BE200/releases/tag/FIX31-20261109), commit `ff82f3e5647ce3885f5d48417b6356a6a23d2163`. The SDK comes from [MacKernelSDK](https://github.com/acidanthera/MacKernelSDK) commit `3f750085caa17ec3a7880f11c11bf4f48cd6a164`, with the driver's `scripts/prepare_tahoe_sdk.py` applied.

The SC A0 / WH B0 Core 106 image has SHA-256 `253876486e3b45267c9b67b510b90b2a6dc67e7d9b51ef4b367bf4813db693d3`. It is stored in the source archive as `itlwm/firmware/iwlwifi-sc-a0-wh-b0-c106.ucode`. The build generates the firmware byte arrays from the firmware inputs in the [recorded order](firmware-order.txt).

I built the preview on Linux with Python 3, Clang 23.1.4 and the [cctools-port](https://github.com/tpoechtrager/cctools-port) ld64-711 linker. From the repository root, extract the archive to an empty folder and run the build script.

```sh
mkdir driver-tree
tar -xzf source/AirportItlwm-BE211-attempt-101-source.tar.gz -C driver-tree
python3 source/build.py driver-tree output /path/to/cctools-port/ld64
```

The output is `output/AirportItlwm.kext`. The script targets x86_64 and compiles the Sequoia WCL translation units. The published kext comes from the hardware test. I rebuilt it from the archived inputs and verified that the executable and Info.plist matched byte for byte. Its digest is in [SHA256SUMS](../SHA256SUMS). The source archive and kext ZIP also have digests there.

The source includes upstream notices, the [driver license](../LICENSE), the SDK license and the [Intel firmware notice](../licenses/LICENCE.iwlwifi_firmware).
