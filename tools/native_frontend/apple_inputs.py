"""Owned build input allowlist. Donors and signing material are never inputs."""
import hashlib
import json


def build_inputs(root, header, mode, proof, revision):
    names = ["native/" + name for name in (
        "SSNCore.c", "SSNCore.h", "SSNIntegration.c", "SSNIntegration.h",
        "SSNWindowOwnership.h", "SSNWindowOwnership.m", "SSNSessionPolicy.h",
        "SSNAccount.c", "SSNFeed.c", "SSNFeed.h", "SSNSwiftABI.h", "SSNObjC.h", "SSNNativeBridge.h", "SSNNativeBridge.m")]
    names += [str(p.relative_to(root)) for p in sorted((root / "native/swift").glob("*.swift"))]
    names += ["tools/native_frontend/apple_worker.py", "tests/native_frontend/abi_calls.c",
              "tests/native_frontend/swift/ModelsTests.swift", "tests/native_frontend/swift/ClockTests.swift", "tests/native_frontend/ownership_test.m"]
    inputs = {name: (root / name).read_bytes() for name in names}
    inputs["generated/SSNBuild.h"] = header.read_bytes()
    config = dict(mode=mode, proof_id=proof, source_revision=revision,
                  toolchain=json.loads((root / "native/apple-toolchain.json").read_text()),
                  inputs={name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()})
    inputs["config.json"] = (json.dumps(config, indent=2) + "\n").encode()
    return inputs
