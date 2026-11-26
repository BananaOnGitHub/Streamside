# Native frontend testing

## Ubuntu checks

Use Zig 0.14.0 for ARM64 compiler/header fixtures and Unicorn 2.1.4 for instruction-level tests. Install the tools outside the checkout. Set `ZIG` to the compiler path when it is outside PATH.

- `make test-host` runs donor-free native and build-tool tests.
- `make test-donor` runs inspection/admission and actual donor ABI contract checks with the local pinned Twitch 32.0 IPA. Set `SSN_DONOR` to override its default path.
- `make test` runs both sets.

GitHub Linux CI runs the donor-free set. No donor is uploaded.

## Apple validation

Run the [hosted Apple pipeline](NATIVE_SWIFTUI_CI.md) for native Swift and Objective-C compilation, linkage, runtime policy, native account and playback request fixtures, Foundation playback transport, model tests and all simulator coordinate tests. Component admission verifies exact source, toolchain and receipts. Independent original-startup control and RN/Hermes/worklet probe tests remain part of validation.

The earlier tweak's Foundation provider-image cache test belongs to the archived implementation. The current native networking tests run with the Apple component worker.

## Documentation integrity

Run `make docs-check` when changing documentation or the native framework metadata. The validator checks local links and anchors and the framework's development identity. Historical links may refer to an immutable prior source revision.

## Device evidence

Local IPA assembly verifies the pinned donor and compiled component identities. Sign with Feather and use the [native device checklist](../investigations/SWIFTUI_NATIVE_DEVICE_TEST.md). Actual authenticated data, video, chat, lifecycle behavior and runtime isolation require iPhone validation.
