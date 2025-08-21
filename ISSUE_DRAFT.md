# Add Linux ARM64/aarch64 Architecture Support

## Summary

solc-select currently lacks support for Linux ARM64/aarch64 architecture, causing installation and usage failures on ARM-based Linux systems (including Docker containers running on Apple Silicon Macs, AWS Graviton instances, Raspberry Pi, and other ARM64 Linux environments).

## Current Behavior

When running solc-select on a Linux ARM64 system:
1. The `soliditylang_platform()` function incorrectly identifies the system as `linux-amd64` regardless of actual architecture
2. solc-select attempts to download x86_64 binaries from `https://binaries.soliditylang.org/linux-amd64/`
3. The downloaded x86_64 binaries fail to execute on ARM64 systems with "Exec format error"

## Root Cause Analysis

### Architecture Detection Issue
The `soliditylang_platform()` function in `solc_select/solc_select.py:275-284` only checks the operating system, not the architecture:

```python
def soliditylang_platform() -> str:
    if sys.platform.startswith("linux"):
        platform = LINUX_AMD64  # Always returns AMD64 for any Linux
    elif sys.platform == "darwin":
        platform = MACOSX_AMD64
    elif sys.platform in ["win32", "cygwin"]:
        platform = WINDOWS_AMD64
    else:
        raise argparse.ArgumentTypeError("Unsupported platform")
    return platform
```

### Binary Availability Challenge
The Solidity team does not provide official ARM64 Linux binaries:
- Available platforms at binaries.soliditylang.org:
  - ✅ linux-amd64
  - ✅ macosx-amd64 (Universal binaries since v0.8.24)
  - ✅ windows-amd64
  - ✅ emscripten-wasm32
  - ✅ emscripten-asmjs
  - ❌ linux-arm64 (does not exist)
  - ❌ linux-aarch64 (does not exist)

## Comparison with macOS Approach

solc-select already handles architecture differences on macOS:
- Detects Apple Silicon vs Intel Macs
- Checks for Rosetta 2 availability for running Intel binaries on ARM
- Identifies Universal binaries (v0.8.24+) that run natively on both architectures
- See `solc_select/utils.py:10-30` for implementation

## Proposed Solution

### Phase 1: Immediate Improvements (Error Handling)
1. **Detect actual architecture** on Linux systems using `platform.machine()`
2. **Provide clear error messages** when running on unsupported architectures
3. **Document workarounds** for ARM64 Linux users

### Phase 2: ARM64 Support Implementation

#### Option A: Use solc-js/WASM binaries (Recommended)
- Leverage the existing emscripten-wasm32 binaries which work on any architecture
- Add a new platform type `LINUX_ARM64_WASM` that uses WASM binaries
- Implement a wrapper to make WASM binaries behave like native ones
- Benefits: Works immediately, maintained by Solidity team, cross-architecture
- Drawbacks: Slightly slower performance, requires Node.js

#### Option B: Build native ARM64 binaries
- Set up CI/CD to compile Solidity for linux-arm64
- Host binaries in Crytic's supplemental repository
- Similar to how older Linux versions (0.4.0-0.4.10) are handled
- Benefits: Native performance
- Drawbacks: Maintenance burden, build infrastructure needed

#### Option C: Use QEMU user-mode emulation
- Document how to set up QEMU with binfmt_misc for transparent x86_64 emulation
- Similar to Rosetta 2 on macOS but for Linux
- Benefits: Works with existing binaries
- Drawbacks: Performance overhead, setup complexity

## Recommended Implementation Plan

1. **Update architecture detection**:
```python
def soliditylang_platform() -> str:
    if sys.platform.startswith("linux"):
        machine = platform.machine()
        if machine in ["x86_64", "AMD64"]:
            platform = LINUX_AMD64
        elif machine in ["aarch64", "arm64"]:
            platform = LINUX_ARM64  # New constant
        else:
            raise argparse.ArgumentTypeError(f"Unsupported Linux architecture: {machine}")
    # ... rest of function
```

2. **Add WASM-based fallback for ARM64**:
   - Download emscripten-wasm32 binaries for ARM64 Linux
   - Create a Node.js wrapper script that executes the WASM binary
   - Install wrapper as the `solc` executable

3. **Add compatibility checks**:
   - Check for Node.js availability when on ARM64
   - Provide helpful error messages with installation instructions

## Impact

This issue affects:
- Docker containers on Apple Silicon Macs (very common in development)
- AWS Graviton instances (increasingly popular for cost savings)
- Raspberry Pi and other ARM SBCs
- Any CI/CD running on ARM64 infrastructure
- Projects using Manticore, Slither, or other tools depending on solc-select

## Testing

The solution should be tested on:
- [ ] x86_64 Linux (regression testing)
- [ ] ARM64 Linux (Docker on Apple Silicon)
- [ ] ARM64 Linux (native, e.g., Raspberry Pi OS)
- [ ] Various Solidity versions (especially older ones like 0.4.x)

## Related Issues

- Similar architecture detection is needed for Windows ARM64 (emerging platform)
- The approach could be extended to support other architectures (RISC-V, etc.)

## References

- [Solidity Official Binaries Repository](https://binaries.soliditylang.org/)
- [macOS Universal Binary Support (v0.8.24+)](https://github.com/ethereum/solidity/issues/12291#issuecomment-2223328961)
- [solc-js npm package](https://www.npmjs.com/package/solc) - JavaScript/WASM version