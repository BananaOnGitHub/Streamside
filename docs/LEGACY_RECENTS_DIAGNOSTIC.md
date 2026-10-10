# Legacy picker: initially blank native recents

On Twitch 31.5, the user observed legacy UIKit player/chat on broadcasts with
both horizontal and vertical formats. Native Twitch recents below Streamside's
provider recent row are blank on initial opening, then appear after scrolling
down and back. Build 84's deferred layout settlement passed the host ordering
fixture but did not fix the device behavior. The root cause remains unresolved.

The decrypted donor exposes the native palette's section/item count, cell
creation and scroll delegate methods. Its `ThemeableCollectionView` superclass
implements `layoutSubviews` separately from the scroll callback. The current
host fixture cannot establish native UIKit cell realization or Swift model
readiness on the device. Another forced layout or reload is not justified yet.

Build 85 retains build 84's behavior and adds passive observations only when
`TAS_IMAGE_DEMAND_DIAGNOSTIC=1`. It does not reload native history, change the
native data source, request extra layout attributes, or synthesize scrolling.
The scheduler, cache, transfer limits and RN library behavior are unchanged.

The report's **Legacy palette trace** records:

- Exact-ABI native cell callback forwarding and section-0/other/nil results.
- Native section/item counts, viewport geometry, inset and owned library gap.
- Original versus returned attributes, including section-0 cell counts.
- Visible cells, section-0 cells, hidden cells and viewport intersections.
- At most 16 immutable scalar snapshots and 128 cells/attributes per scan.

Stages are bind, first positive-height layout, deferred settlement, before/after
the first scroll away from the top, and return to the top. Section 0 is only an
index; a recognized native Recent heading is reported separately. Records
contain no text, image values, identifiers, object pointers or private Swift
storage. The report reads an atomically published immutable prefix rather than
querying UIKit from the reporting thread. Production builds contain no probe
hook or UIKit probe calls.

Restart Twitch with build 85, enter a vertical-enabled channel and open the
legacy picker. Capture one diagnostic report before scrolling, then another
after scrolling down/back makes native recents appear. Keep both in the same
launch. Clearing the on-disk log does not reset these launch counters.

The probe test executes production code with host ABI adapters. It verifies
unchanged callback arguments/results, untouched arrays/reloads/scroll offsets,
immutable observations, privacy, scan/storage bounds and safe short buffers.
The existing native library geometry suite also runs with probes enabled.
These checks validate instrumentation behavior, not the device bug's cause.
