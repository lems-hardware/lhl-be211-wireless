## lhl-be211-wireless

This repository documents my experimental Intel BE211 Wi-Fi bring-up on a **Framework Laptop 13 Pro** running macOS Sequoia. The current developer preview is **Attempt 101**.

| Component | Tested configuration |
| --- | --- |
| Laptop | Framework Laptop 13 Pro, Intel Core Ultra X7 358H |
| Wireless | Intel BE211 Wi-Fi 7 (CNVio3), PCI `8086:e440`, subsystem `8086:0114` |
| System | macOS Sequoia 15.8.3, build `24H241`, Darwin `24.6.0`, x86_64 |
| Bootloader | OpenCore 1.0.8 |
| Driver | `AirportItlwm.kext`, build marker `_BE211_OPEN_NETWORKS_1` |
| Firmware | Intel Core 106 SC A0 / WH B0, `iwlwifi-sc-a0-wh-b0-c106.ucode` |

## Current Progress

| Component | Status | Notes |
| --- | --- | --- |
| Native Wi-Fi menu | Working on the test system | macOS discovers networks and can initiate an eligible open 2.4 GHz join. |
| Network selection | Implemented | Attempt 101 uses the SSID from the macOS join request. It honors a valid requested BSSID and checks the beacon and channel. Testing across additional network names is still open. |
| IPv4 connectivity | Working within the tested traffic path | Native DHCP, ARP, DNS and HTTPS over TCP. |
| Safari | Working in the tested setup | I loaded a public HTTPS page on CISD-Guest in Attempt 100. The packet capture showed the DNS response and a two-way TCP exchange with the resolved address. |
| Connection duration | Working in a multi-hour test | After removing the scheduled disconnect, I used Wi-Fi for about 3–4 hours without unexpected drops. |
| Lid-close reconnect | Observed once | Wi-Fi reconnected automatically after I reopened the lid the next morning. The sleep state and reconnect latency were unmeasured. |
| Secured Wi-Fi and other bands | Open work | The experimental join path is limited to visible open networks on enabled 2.4 GHz channels 1–11. WPA2, WPA3, enterprise Wi-Fi, 5 GHz and 6 GHz are outside the current path. |
| Additional protocols | Open work | The data path implements selected IPv4 traffic. General IPv6, QUIC, captive portals and Bluetooth remain unverified. |

## Research Milestones

- **Attempt 97** brought up the native BSD link on `en0`. macOS obtained and published a DHCP lease, then resolved the gateway over ARP.
- **Attempts 98-99** moved from gateway ICMP tests to two-way DNS and TCP payload. The first Safari test failed, and background traffic exhausted all 76 one-use web transmit slots.
- **Attempt 100** reclaimed completed descriptors in a 128-slot transmit ring. During a 45-second test, the driver submitted and reclaimed 33,444 descriptors with no ring-full events. Safari loaded Example Domain.
- **Attempt 101** removed the fixed connection deadline and fixed SSID. The multi-hour and overnight lid-close results come from direct use without a collector trace. The mounted test USB matched the staged driver. Its OpenCore config differed in NVRAM settings.

The full platform investigation and earlier boot history are in [lhl-hackintosh-docs](https://github.com/lems-hardware/lhl-hackintosh-docs).

## Developer Preview

Download [AirportItlwm-BE211-attempt-101.zip](kexts/AirportItlwm-BE211-attempt-101.zip) or browse the [kext bundle](kexts/AirportItlwm.kext). This is the exact Attempt 101 executable and Info.plist. Use [SHA256SUMS](SHA256SUMS) to verify the files.

For an existing OpenCore test setup that already boots build `24H241`, keep a rollback copy of its EFI. Put the bundle at `EFI/OC/Kexts/AirportItlwm.kext` and use a single enabled AirportItlwm entry in `Kernel → Add`.

| OpenCore field | Tested value |
| --- | --- |
| `Arch` | `x86_64` |
| `BundlePath` | `AirportItlwm.kext` |
| `ExecutablePath` | `Contents/MacOS/AirportItlwm` |
| `PlistPath` | `Contents/Info.plist` |
| `MinKernel` and `MaxKernel` | `24.6.0` |

Boot the test EFI and choose a visible open 2.4 GHz network in the Wi-Fi menu. This build uses the network selected by macOS. It needs no SSID boot argument. Full EFI setup and compatibility with other macOS builds are outside this preview.

The optional [Safari collector](tools/capture-safari.sh) is for the Framework test setup. It expects `en0` and a mounted `FILES` volume with a `wifi-logs` directory. It records local IP state, DNS and TCP metadata. Review the capture for network names and addresses before sharing it.

## Automated Builds

GitHub Actions builds the source snapshot on pushes to `main`, pull requests and manual runs. The workflow checks the archived files, compiles the driver, validates its bundle and imports, and uploads a kext ZIP with matching source, checksums and `build-info.json`. Download these from the run's Artifacts section. [Build workflow](.github/workflows/build.yml)

CI uses Ubuntu 24.04, Clang 18 and a pinned ld64-711 source revision. The published Attempt 101 executable was built with Clang 23.1.4. Each CI artifact records its own compiler, commit and digest. Hardware testing is recorded separately from successful compilation.

Pushing a tag beginning with `v` also creates a draft prerelease containing the validated artifacts. Review the draft and hardware results before publishing it.

## Source and License

The [build notes](source/README.md) point to the complete source archive, the cumulative driver patch and the build script. The driver is based on [AirportItlwm-BE200 FIX31-20261109](https://github.com/Ersiter/AirportItlwm-BE200/releases/tag/FIX31-20261109).

Driver code is distributed under the [GNU GPL v2](LICENSE), with component notices in the corresponding source. Embedded Intel firmware carries its [separate redistribution notice](licenses/LICENCE.iwlwifi_firmware).
