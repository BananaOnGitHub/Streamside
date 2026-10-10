# Legacy picker: initially blank native recents

> Completed on `archive/rn-image-demand` and incorporated into active
> `compat/twitch-31.5` build 87. The user confirmed build 86 fixes native Recent
> at first opening and build 87 fixes footer tint and delayed icon insertion
> while dragging. The initial unresolved diagnosis below is historical; the
> corrections and regression evidence follow it.

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

## Build 85 device evidence and build 86 correction

The first device report recorded zero sections at bind and first layout, but
an owned 410-point gap at section zero. At settlement Twitch had published 18
sections and 14 section-zero items, while the query `[-177.3, 177.4]` was
compressed to end at zero. The single returned native attribute was filtered
out after translation; no heading or cells were observed. The second report
recorded a second opening and more queries, but no scroll-stage observations
or native cell callbacks. It does not establish what scrolling recovered.

The zero-section startup had been treated as an empty, prepared palette, so
placement inserted the library before the future first header. Later placement
required that header's realized title to distinguish Recent from Channel, but
the owned gap prevented its realization. Build 86 leaves a newly bound,
zero-section palette's coordinates intact and hides the library panel until
sections arrive. Prepared headerless palettes remain supported; an already
observed palette can still keep its library during a temporary empty model.

The regression now exercises zero sections followed by model publication,
using the device-sized viewport and prefetch rectangle. It verifies native
section-zero attributes remain reachable, the realized Recent header places
the library after Recent, and neither native reloads nor scroll offsets change.
The diagnostic adds only booleans for native palette class membership and
whether the collection itself owns its delegate/data source, to detect fallback
binding without recording object identities. The user confirmed that build 86
fixes native Recent on first opening.

## Build 87 legacy footer correction

Leaving the owned library restored native footer colors, selection and the
underline, but left the owned emoji button's tint purple until a later footer
refresh. Build 87 restores its inactive tint in the same section handoff. It
does not depend on the periodic refresh, which can wait during a drag.

The input now binds its known palette container before the lazy footer exists.
Footer and container lifecycle callbacks can resolve the delegate's weak input
owner after UIKit reparents the keyboard outside the input's ancestor chain.
They insert or repair the existing icon synchronously, without another timer,
native reload, data-source replacement or synthetic scroll.

Regression coverage verifies the tint at the exact library end boundary,
first insertion after container reparenting, repeated native stack rebuilds,
theme application, independent footer reparenting and an expired weak owner.
The image scheduler, cache and RN performance architecture are unchanged.

The user subsequently confirmed that both build-87 footer corrections work.
