# Hosted Apple builds

Use Ubuntu to select one hosted provider for `feat/native-frontend`. Codemagic
M2 is preferred while its verified personal free-minutes budget is sufficient;
GitHub Actions is the fallback. No local Mac or signing credential is required.
Donor-free native Linux CI remains automatic. Apple builds are explicitly requested so a push
does not start duplicate macOS jobs.

Commit and push source first, then run:

```sh
make native-ci-plan    # read-only provider, quota and estimate
make native-ci         # submit once, or reuse the recorded build
make native-ci-status  # inspect progress; repeat when useful
make native-ci-fetch   # after success: download, verify, run Ubuntu ABI gates
```

Artifacts and the resumable build ticket live in `../artifacts/ci/<source-sha>/`
(or the external `STREAMSIDE_ARTIFACTS_DIR`). The verified components directory
printed by fetch can be passed to the existing native packaging command with
`--components`. Donor handling, final IPA assembly and Feather signing stay local.
A successful hosted build is not a physical-device test.

## Local authentication

Use an authenticated `gh` installation. Keep the Codemagic API token in
`$XDG_CONFIG_HOME/streamside/codemagic-token` (default
`~/.config/streamside/codemagic-token`), owned by the current user, mode 0600.
`STREAMSIDE_CODEMAGIC_TOKEN_FILE` can select another private file. Never paste
credentials into commands, Git, CI variables, reports or build artifacts.
No Codemagic token is installed in GitHub Actions. A missing/unusable local token
selects GitHub Actions.

## Budget and source admission

The selector reads the account's actual free allowance and consumed seconds
from Codemagic's legacy authenticated `GET /user`. It verifies agreement between
the two quota representations and the configured personal account. This quota
response is not in the new OpenAPI schema: if it changes, selection fails closed
to GitHub Actions. No assumed reset date or cached balance is used.

Recent successful builds of the same app, workflow, M2 machine and Xcode 26.6
supply at most 20 duration samples. The prediction is the nearest-rank 90th
percentile plus 30% and two minutes, rounded up. With fewer than five samples,
a 25-minute floor applies; this is a cautious estimate, not a statistical
confidence bound. Failed/cancelled short runs cannot lower it. A prediction over
the 40-minute workflow timeout selects GitHub Actions.

Admission additionally requires the full 40-minute timeout plus a ten-minute
reserve. Every unfinished account build reserves another 120 minutes, even if
it belongs to a different application. History is bounded at 1,000 records;
incomplete or unrecognized quota/history selects GitHub Actions. This protects
against ordinary timing variance; other clients can still consume minutes after
the check. No subscription or paid billing is enabled by this tooling.

Both providers validate the exact requested checkout before compiling. Xcode
26.6 / 17F113 and iPhoneOS SDK 26.5 remain strictly checked by the Apple worker.
The shared runner compiles both component modes, runs simulator/model tests,
native Foundation transport and host comparison/routing tests, then publishes only
owned components, logs and a source-bound validation receipt. Retrieval verifies
the archive hash, every component hash, source/toolchain/test receipts, and runs
the existing Ubuntu ARM64 ABI/admission/runtime-policy tests. The local ABI tests
need the repository's existing pinned Unicorn 2.1.4 test dependency. The Makefile
adds the external `../toolchains/python` directory to the test import path;
`NATIVE_CI_TEST_PATH` and `NATIVE_CI_PYTHON` can select an existing test environment.
On a new workspace with pip available, install it outside Git with
`python3 -m pip install --target ../toolchains/python unicorn==2.1.4`.

## Failed or interrupted builds

`start` is protected by a local lock and records intent before submission. It
also adopts existing same-source runs. Repeating it does not submit another job.
After an uncertain API response, use `status` to discover the submitted run;
never automatically retry the POST or switch providers. A compiler/test failure
is retained as a failure, with logs on its provider; it does not trigger a second
provider build. Fix and push a new commit before starting again. For a deliberate
same-commit retry, preserve the old `build.json` as evidence and start explicitly
through the provider UI, then update the local ticket to that verified run ID.

A failed download is preserved under `download/`. Move it aside before retrying
fetch. Signed artifact URLs and raw account responses are never saved in the
build ticket. The historical fixed-source benchmark remains recoverable in
commit `567b2276e6e10c46b12d7ce790e7ff1de6693f26`.
