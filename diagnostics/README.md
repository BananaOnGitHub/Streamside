# Built-in investigations

The initial RN chat profile selects versioned compiled capabilities. Its
event-driven armed lifecycle has no fixed expiration. Capture returns to Armed;
explicit Disarm ends collection. The native parser rejects unknown/duplicate
fields, new hooks or fields, incompatible profiles and limits above compiled
ceilings. Capability availability requires separate native donor, bootstrap and
command-channel admission.

The bundled registry is pinned to its exact original bytes with SHA-256 using
the system cryptographic primitive. An optional cached copy must match that
same pin; malformed or different bytes fall back to the verified bundle. This
is immutable bundled configuration, not a mutable remote update service.
Future fixed-repository retrieval can provide only those pinned bytes. Signed
mutable updates, transport and disk caching are not implemented in this stage.
No downloaded manifest can execute code or transmit diagnostic reports.

Regenerate the checked-in byte array with
`python3 tools/generate_investigation_registry.py`; `--check` detects stale data.
The native parser is the admission authority. The JSON Schema is an authoring
aid; integer spelling, UTF-8 byte budgets and cross-field capability/resource
checks are additionally enforced by the native parser.

Registry revision 2 selects the implemented translation, emission/local-echo,
aggregate store, IRC reward, reward-store and list-lifecycle adapters. Revision 1
is preserved as an earlier schema fixture, not an accepted cached replacement.
Filtering/deduplication, confirmed reconciliation, renderer/catalog and row
geometry are reported unavailable. The observer never infers server receipt.

Every ordinary build checks the committed, fingerprinted compiled-Hermes
validation receipt in `diagnostics/validation/hermes-v1.json`. A clean build
does not need copyrighted donor contents; replaying or refreshing that proof
requires the exact donor and the pinned Hermes toolchain. Run
`make test-investigation-runtime` with the same input variables as
`make test-rn-virtualization`. Changed runtime/graft/fixture inputs invalidate
the recorded proof and stop the build. This receipt records host validation,
not independent CI replay or device acceptance.
