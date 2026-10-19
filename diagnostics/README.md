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
