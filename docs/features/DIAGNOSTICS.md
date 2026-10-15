# Diagnostics

Diagnostics answer which integration ran, what it admitted, and where a failure occurred. They do not replace a visible device result or turn an unobserved path into a validated feature.

[TASDiagnostics.c](../../src/TASDiagnostics.c) owns the settings/report UI and log. [TASPrivacy.c](../../src/TASPrivacy.c) owns temporary labels. Subsystems contribute bounded counters/status strings.

## Diagnostic configuration (3.1.0 development)

In 3.1.0, Profile → Settings → Streamside → **Diagnostics** offers a single preset selector and a **Summary**/**Detailed** selector. Category switches appear only for **Custom**, which keeps the current selections. A short contextual sentence explains the selected preset. Changing detail preserves the preset; selecting a preset restores its recommended detail. Changes are saved immediately but collection changes only after fully closing and relaunching Twitch. A single restart note appears on the Diagnostics page only while saved collection settings differ from the active configuration; reverting those changes clears it. Selecting Custom alone does not require a restart. The report distinguishes saved and active settings. Existing installations start with **Minimal / Summary** rather than inheriting the old all-or-nothing logging switch. The released 3.0.0 report uses the older switch and disk log.

| Preset | Enabled categories | Verbosity |
| --- | --- | --- |
| Minimal (default) | General | Summary |
| Ad Blocking | General, Playback / Ad Blocking | Detailed |
| Emotes | General, Emote Rendering, Image Transport, Composer / Picker | Detailed |
| Chat | General, Chat / Redemptions | Detailed |
| Custom | Independent category and verbosity selections | Selected value |

General covers compatibility admission and essential failure counters. Playback owns HLS manifests, routing, swaps and token events. Rendering owns matching, geometry and animation probes. Image Transport owns flights/cache and compiled decoder/header-comparison probes. Composer owns input, picker, popup and compiled library-demand/palette probes. Chat owns incoming/local lifecycle and the separate experimental redemption/list trace. A preset's selections are explicit; selecting only Chat does not turn on playback or image-demand probes.

Disabled categories skip event formatting, label creation, retention and diagnostic-only sampling/bridge registration. Essential operational counters remain available internally and can span disabled collection; they are not detailed event capture. Disabling diagnostics never disables interception, cache behavior, emotes, input or chat delivery. Functional hooks/algorithms are not controlled by diagnostic preferences.

Ordinary events use independent, fixed **48 × 384-byte** in-memory rings per category. Playback cannot consume another category's retention. Summary collects essential/failure events and exports at most four per category; Detailed exports at most twelve. Reports state accepted, retained, overwritten, shortened and export-omitted counts; bounded output truncation is marked. Disabled collection is explicitly different from zero observed events. Reports invoke only enabled category status exporters, plus the compact version/configuration/privacy header.

New reports contain no prior-launch disk event dump. Initialization removes the obsolete `diagnostics.log` and `diagnostics-r5.log`; the new session rings reset on relaunch along with temporary labels. Clear Diagnostic Log clears ordinary category rings, not launch counters, provider catalogs, source admission or the specialized rolling trace. Copy the report before restarting.

The settings/report controllers are created through the Objective-C runtime. A guarded main Profile → Settings integration opens Streamside's page; the project does not replace Twitch's entire settings data source.

## Privacy boundary

Ordinary reports/logs exclude channel names, room IDs, chat text, full URLs/paths, query strings/fragments, headers, access tokens, manifests, and image/source bytes.

Channel/resource labels are process-local, salted, bounded mappings. They stay stable for a label's retained lifetime and reset after restart or bounded-table replacement. They are not persistent cross-session identifiers.

Transport can retain actual URLs/header variants in its own runtime/HTTP-cache state. Provider metadata contains names/asset URLs for feature operation. Those facts are separate from what diagnostics exports.

An opt-in **Inspect Emote** diagnostic build deliberately includes the exact code entered as its target in the copied report. The UI warns about that narrower exception; surrounding chat is still not recorded. Raw screenshots, crash logs, and manually attached network captures need independent redaction.

## Playback interpretation

Report HLS interception, master/variant classification, ownership misses, ad-marked playlists, alternate-token failures, clean swaps, and synthetic suppression separately.

A clean-swap counter establishes that the code selected an admitted clean alternate. Zero ad-marked manifests in a run may simply mean no observed ad-bearing playlist; it is not proof of complete blocking.

An unmapped variant records active/retired route categories, generation, and ages. It does not authorize using the last channel's state. Compare main/PiP/profile-preview activity before attributing a routing symptom.

## Emote interpretation

Keep hook installation, module registration, patch admission, callback execution, range rewrite, image request, response, decoded assignment, and displayed result distinct.

Builds 57/58 demonstrate why “module registered” is not “own-message callback executed.” Build 59 demonstrates why export discovery is not native entry. A valid image response does not prove the correct image object reached the view.

Native catalogs, provider fetch outcomes, registry counts, composer previews, own-message paths, RN/legacy geometry, details, menu insertion, and cache behavior have separate report sections.

## Transport and cache counters

Shared/coalesced/completed/error counts describe flights/consumers at their documented boundary. Timing buckets are ≤250 ms, ≤1 s, ≤5 s, and >5 s. Queue wait, cache lookup, task completion, and JS onLoad must not be merged into one latency claim.

Foundation transaction metrics classify network versus local-cache work. Direct cache delivery may produce no new Foundation task at all. Cache annotation counters count the first rejection per proposal; after callbacks settle, successful annotations plus remaining rejections equal proposals.

Date-less receipt counters describe staged/stored/fallback outcomes. They do not export response headers or receipt timestamps. See [Image transport](third-party-emotes/IMAGE_TRANSPORT.md).

## Compile-time probes

Normal builds use `EMOTE_DIAGNOSTIC=0`, `IMAGE_DEMAND_DIAGNOSTIC=0` and `CHAT_TRACE_DIAGNOSTIC=0`. Reports state which modules were actually compiled. Runtime preferences cannot activate absent modules.

- **Emote diagnostics** add bounded target-code observations for matching, image identity, native handoff, and playback.
- **Image-demand diagnostics** add JS lifecycle/range/mask/geometry, Foundation timing, cache-header comparisons, and bounded legacy palette observations.
- **Chat-trace diagnostics**, on the chat investigation branch, retain their separate bounded rolling observer and native collector. Chat + Detailed at launch admits the diagnostic graft and bridge; Summary or a disabled Chat category omits them without changing functional chat grafts. The existing trace's own-message priority and redemption/geometry retention remain separate from ordinary category event rings.

Detailed launch selection is required for each compiled probe: Rendering for matching/animation, Image Transport for decoder/header comparison, Composer for library-demand/palette, and Chat for rolling chat. Probe absence, disabled collection, missing hook admission and unobserved stages have different meanings. Detailed still does not mean unlimited exports: emote probe output is capped at 16 KiB with a truncation marker; the specialized chat trace keeps its existing bounded exporter and retention semantics.

Probe flags compile extra work in; toggling ordinary logging cannot activate code absent from a normal binary. Historical build-46/47 or RN-boundary probes live on archived branches and are not all current production hooks.

Demand snapshots are immutable bounded scalar records with fixed caps and deadlines. Observing a JS committed instance differs from an attempted render, unique asset, flight, native decoded object, or physical image view. Unknown native attribution remains unknown.

## Evidence hierarchy

| Evidence | Establishes |
| --- | --- |
| Host production-code fixture | Algorithm/lifecycle behavior under the controlled adapter |
| Exact donor metadata/disassembly | The inspected ABI/bytecode structure and patch boundaries |
| Compiled Hermes fixture | Production graft executing with the admitted runtime/donor functions |
| Real Foundation fixture | Apple cache callbacks, storage, network/cache transactions, and revalidation |
| Device report | Activity counters and bounded observations in that session |
| Visible device check | Rendering/interaction outcome actually exercised on that configuration |

Do not promote one row into another. Independent reproduction can strengthen provenance, but it must be named separately from original source/artifacts.

## Reporting a problem

Choose the relevant preset, relaunch, reproduce once, and copy the report from that launch. Use Minimal/Summary unless event traces are needed. For local missing messages/rewards, use Chat/Detailed in a compiled chat-trace build, leaving Playback off. State the Twitch/iOS version, installation method, surface, expected behavior, and visible result. For playback, distinguish preroll/midroll/PiP/profile preview. For emotes, distinguish RN/legacy, incoming/sent/composer/library, and static/animated/wide cases.

Review the report before sharing. Do not attach tokens, certificates, profiles, raw authenticated requests, or unredacted private chat.

[Privacy tests](../../tests/test_privacy.py), [Demand tests](../../tests/test_image_demand.py), [Probe tests](../../tests/test_emote_probe.py), and [Legacy palette probe tests](../../tests/test_legacy_palette_probe.py) verify bounds, forwarding, privacy, and safe report construction.

[Testing](../development/TESTING.md) · [Research archive](../archive/README.md) · [Security](../../SECURITY.md)
