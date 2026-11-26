# Contributing to Streamside Native

Work on `feat/native-frontend`. Use the [native build guide](docs/development/NATIVE_SWIFTUI_CI.md) and [testing guide](docs/development/TESTING.md). Keep the pinned Twitch donor and signing material local. Use the existing native services and validate each binary boundary against the donor.

Run host tests and documentation checks before pushing. The hosted Apple pipeline compiles and validates donor-free components; package device candidates locally from the verified components.

During development, record technical findings in [investigations](docs/investigations/README.md) and follow the [documentation maintenance policy](docs/development/DOCUMENTATION.md). Keep private account and channel information out of committed reports. Use [Security](SECURITY.md) for sensitive issues.

The earlier React Native implementation and its development instructions are available at the [preserved revision](https://github.com/BananaOnGitHub/Streamside/tree/eb4d30f761e75921913451293b76a92d39eaa2d5).
