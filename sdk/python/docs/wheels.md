# Bundling `codex` into Python wheels (design notes)

The TypeScript SDK is shipped as an npm package that includes a `vendor/<target_triple>/codex/...`
directory. The Python SDK can use a similar approach, but via platform-specific wheels.

## Goal

Make `pip install codex-sdk` self-contained by embedding the `codex` binary in the wheel for each
supported platform/arch, while keeping a `PATH` fallback for development builds.

## Proposed layout

Package data inside the wheel:

```
codex_sdk/
  vendor/
    aarch64-apple-darwin/
      codex/codex
    x86_64-apple-darwin/
      codex/codex
    x86_64-unknown-linux-musl/
      codex/codex
    aarch64-unknown-linux-musl/
      codex/codex
    x86_64-pc-windows-msvc/
      codex/codex.exe
    aarch64-pc-windows-msvc/
      codex/codex.exe
```

Runtime selection mirrors the Node launcher logic: pick the target triple from
`sys.platform` + `platform.machine()`.

## Runtime resolver changes

1. Look for a bundled binary via `importlib.resources.files("codex_sdk") / "vendor" / <triple> / ...`
2. If present, ensure it is executable (POSIX chmod) and return that path.
3. Otherwise, fall back to `shutil.which("codex")`.

## Build / release strategy

- Use `cibuildwheel` to produce wheels for macOS, Linux, and Windows.
- Populate `codex_sdk/vendor/...` during wheel build:
  - Option A: download prebuilt artifacts from the Codex release pipeline
  - Option B: build from source in the wheel build job (slower; more toolchain setup)
- Mark the binaries as package data in `pyproject.toml` (setuptools `include-package-data` or
  MANIFEST.in).
- Keep sdist source-only (no binaries); users building from source still require `codex` on `PATH`.

## Risks / considerations

- Wheel size: shipping `codex` is large; consider splitting into `codex-sdk` (pure python) plus
  `codex-sdk-binary` extras, or shipping per-platform optional dependencies.
- macOS signing/notarization: end users may hit Gatekeeper if the embedded binary is not signed.
- Linux libc: prefer musl static builds (like the npm package) to avoid glibc mismatch.
- Windows: ensure `.exe` is discoverable and not blocked by SmartScreen.

