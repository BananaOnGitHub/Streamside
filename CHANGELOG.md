# Changelog

## 3.0.0 (Streamside; prepared, not published)

- Diagnostic build 52 follows confirmed build-51 RN IRC delivery with passive
  bridgeless surface, native JS scheduling, catalog-shape/input-event and
  GraphQL send-operation observations. Document same-launch device results and
  separate incoming, picker insertion and send stages. No JS patches or RN emote
  implementation changes; direct JS parser/local-echo execution remains unobserved.

- Diagnostic build 51 adds passive RN transport, native/JS event, surface/bundle,
  composer/catalog and image/decode observations. Original messages, requests,
  callbacks and geometry are untouched. Build-50 validation applies to legacy
  chat only; compatibility with active RN chat remains unimplemented.
- Compatibility build 50 enriches the native per-message subscriber-emote
  definitions on Twitch 31.5. Preserve the original message and tokens; let
  Twitch construct presentation tokens and attachments using Streamside's
  existing synthetic IDs. Keep provider image redirection, TextKit spacing and
  layer proportions unchanged. Gate account/channel scope, native-name
  conflicts and moderated/shared-channel messages. Host identity/geometry
  checks cover square, wide, animated and animated-wide fixtures; device
  local-echo and playback validation remain pending. Forensic probes are off.
- Build 44 corrects diagnostic child roles using the attachment's actual fields,
  observes both native children, and admits visible layers ahead of hidden ones
  within the 64-layer budget. Report capacity denials, live observer evictions,
  genuine weak-layer release and recorder heartbeat separately. Retain per-ID
  transport/mapping, native decoded-input/assignment and last-progress histories
  independently of cleanup traffic and target selection. No raw image bytes,
  object descriptions or URLs are retained. Normal builds compile these changes
  out; native playback/recovery and image transport are unchanged. Device
  validation pending.
- Build 43 adds diagnostic-only retrospective playback recording before target
  selection. Keep bounded per-ID visible samples, transitions and separate
  last-visible snapshots after chat rows disappear; observe native image
  assignment/clearing, static replacement, stopping and removal. Selection does
  not reset playback clocks/history. Numeric copied records, weak live layers,
  capacity limits and ten-minute expiry preserve privacy and bound memory.
  Normal builds compile it out; playback/recovery behavior is unchanged.
  Device validation pending.
- Build 42 adds diagnostic-only playback sampling for the selected emote.
  Count native refresh callbacks and frame changes; report link state, native
  animation flags, frame/contents presence, loop countdown and visibility gate.
  Sample already cached animations with a separate main-thread observer; keep
  32 playback observations apart from sizing/layout traffic. Weak references,
  a ten-minute sampling window and fixed identity slots bound its lifetime.
  Normal builds compile it out. Playback/recovery behavior is unchanged; device
  validation pending.
- Build 41 retains each channel identifier through its asynchronous emote-catalog
  completion. Plain C blocks do not retain captured object pointers; reading an
  expired string caused the build 40 BTTV callback crash. Release the identifier
  after completion, cancellation, obsolete responses and task-creation failures.
  Add a deferred-completion regression that drains the creating autorelease pool
  and checks all three providers and every release path. Device validation pending.
- Build 40 gives provider images a separate URL-protocol transport session from
  HLS. Alternate token/manifest downloads in HLS's serial completion queue can
  no longer block emote responses. Keep asynchronous cancellation and recursion
  guards. Extend the opt-in probe with protocol start/cancel stages and original
  request attribution for failures without response URLs, including error codes.
  Device validation of the missing-emote symptom remains pending.
- Prepare temporary build 39 diagnostics for provider codes that remain text.
  Opt in with `EMOTE_DIAGNOSTIC=1`; normal builds compile out the probe and its
  settings row. Inspect Emote selects one code explicitly, then the copied report
  includes catalog presence/readiness, case variants, IRC match/rejection/native
  overlap, native delivery token type, composer lookup, image transport and chat
  layout/decoded-animation stages. Keep 48 observations and stage totals in
  memory, reset on a new target or relaunch, and retain no surrounding chat,
  sender/channel identifiers or URLs. No matching/rendering fix is included.
- Rename the project and current documentation to Streamside; the sideload app
  and package display name are Twitch Streamside. Both native artifacts now use
  Streamside identities. Keep the jailbreak package ID for upgrade continuity.
- Add a compact emote suggestion strip with Automatic, Colon (:name), and Off
  modes, plus provider-image previews in the composer that serialize back to
  emote names for editing, clipboard operations, undo/redo and sending.
- Add a third-party library inside Twitch’s existing emote keyboard: All / 7TV /
  BTTV / FFZ, then Channel / Global. Provider changes reset Channel.
- Integrate up to 40 provider-emote recents into Twitch’s native Recent tab.
  Place the scroller beneath its localized Frequently Used heading and above
  the native history grid, sharing the section background and preserving native
  cell geometry, sticky headers, navigation and the menu-opening snapshot.
- Clip the provider Recent row beneath the pinned Frequently Used heading
  during scrolling, preserving its transparent appearance and horizontal swipe.
- Restore the complete provider library's footer entry after Recent whenever
  Twitch replaces its native button/highlight stacks. Match native slot sizes
  and highlight behavior; keep the emote grid, All / 7TV / BTTV / FFZ filters and
  Channel / Global control reachable. Every provider change resets Channel.
- Place the full provider library inline between native Recent and account
  subscription emotes. Its footer entry jumps to that section; provider controls
  and all grid rows share the native picker’s vertical scroll. Reserve native
  layout space without changing section indexes, and virtualize the owned grid
  to keep only a viewport of cells active, including after width/scope changes.
- Bound thumbnail requests/cache and validate native bridge signatures; add
  UTF-16 selection/deletion, native-attachment preservation and identity-layout
  regression tests. Keep every existing Mach-O and packaging guard mandatory.
- Preserve the existing icon. The forthcoming logo must support UIKit dynamic
  background/appearance and tint; logo work and release publication remain pending.
- Explicitly invalidate cached native flow-layout delegate metrics and attributes
  when the inline library height changes, then apply native cell frames before
  placing the transparent panel. Clip the panel and its viewport grid to their
  own bounds; add a cached-metrics regression covering the full 6,500-emote grid.
- Replace the ineffective native section-inset spacer with copied layout
  attributes that move following native cells and headers, a matching content
  height extension, and visible-rectangle translation. Bind the exact Twitch
  palette and handle empty/headerless native sections without changing their
  models or cached attributes. Add regression coverage for both direct and
  visible-cell queries, large libraries, rotation and unrelated collections.
- Device-confirmed the build 22 inline library spacing. Make its provider grid
  scroll horizontally in five rows, filling each column top to bottom. Larger
  libraries add columns instead of extending the native vertical scroll. Keep
  browsing position during refresh/outer scrolling/rotation, reset it for
  provider/scope/channel switches, and allow swipes starting on emote buttons
  through an isolated collection-view subclass.
- Device-confirmed the build 23 horizontal library. Sort picker snapshots by
  name ignoring capitalization across all included providers/scopes, with an
  exact-name tie-break and limits applied after sorting. Keep the registry's
  case-sensitive code lookup and channel-over-global precedence intact.
- Device-confirmed the build 24 alphabetical library order. Replace blocking
  URL-protocol downloads with cancellable asynchronous tasks for provider images
  and HLS. Suppress callbacks after stop, including stops during response delivery;
  preserve manifest rewriting, internal-request recursion protection and blank ads.
- Reuse the emote library's sorted metadata snapshot until its catalog revision,
  channel, provider or scope changes. Image completions and periodic refreshes
  update visible thumbnails without rebuilding thousands of metadata objects.
- Device-observed the build 25 playback pause fix. Match composer suggestions
  against case-insensitive fragments anywhere in native and provider emote names,
  following Frosty's substring rule: `awa` finds `wawa`. Keep exact emote-code
  lookup, provider/scope filters, result interleaving and the 64-item limit.
- Device-confirmed build 26 suggestion matching. Preview exact provider codes
  on the next run-loop turn after UIKit finishes the edit, without a typing
  debounce or waiting for the image. Reserve attachment bounds immediately;
  fill arriving images in place without rewriting text or moving the caret.
- Route the emote-menu backspace through the text editor's deletion path so
  completed provider previews delete as whole codes, including unloaded
  placeholders. Preserve keyboard deletion, native validation, selected ranges,
  ordinary text/emoji deletion and marked composition. Add production-code
  regression coverage for image arrivals, both backspaces and native serialization.
- Device-confirmed build 27 immediate previews and menu backspace. Replace nil
  loading images with a shared transparent RGBA pixel so UIKit does not draw a
  white missing-image box. Keep reserved bounds, image requests and whole-code
  deletion intact; verify alpha bytes and placeholder-to-image replacement.
- Device-confirmed build 28 transparent loading previews. Distinguish an
  unrealized native header from an observed Channel/headerless section when
  placing the inline library. Finish pending native layout before inserting
  the provider gap; defer insertion while its title/geometry are unavailable.
  Keep the observation while headers are offscreen and clear it when rebinding
  the palette. Add initial-layout, empty-title, zero-height, headerless and empty
  collection regressions so native Recent cells retain their opening position.
- Device-confirmed build 29 initial native Recent layout. Play cached provider
  GIFs in composer attachments using one 30-fps display link per visible input,
  the decoder's frame delays and its existing bounded lazy frame cache. Repaint
  only changed attachment characters without rewriting text or moving the caret.
  Preserve playheads across edits/image refreshes/cache eviction; stop on
  detachment, hiding or expansion and remove deleted previews from playback.
  Add timing, looping, pending-decoder, edit/IME, deletion and lifecycle regressions.
- Device-observed build 30 animation interference when the caret-adjacent
  suggestion and composer use the same GIF at different playback positions.
  Give each composer attachment its own four-frame decoder using the existing
  downloaded data, retaining it across edits and cache/image refreshes. Avoid
  competing for the thumbnail decoder's moving cache window, including repeated
  copies of one emote in the input. Add interleaved playback, decoder reuse,
  source replacement, static fallback and whole-code deletion regressions.
- Device-confirmed build 31 independent preview playback. Decide inline library
  highlight ownership before Twitch's scroll callback publishes a native tab.
  Suppress that native selection publication only while the provider section
  leads the viewport and its footer highlight is available; restore native
  callbacks at both boundaries, for closed menus and unrelated collections.
  Add rapid-scroll, entry/exit, unavailable-footer and native-fallback regressions
  to prevent Recent from competing with the provider shortcut.
- Device-rejected build 32's scroll-publication fix: Recent still flickers.
  Guard tint/background writes to the six currently bound native footer views
  while the inline provider library owns selection, including Swift/reactive
  paints outside scroll/apply callbacks. Save requested native colors for handoff
  and theme changes; let Streamside's own styling and all unrelated views pass
  through. Do not temporarily restore native highlighting during active apply.
  Test every rendering-boundary write across 200 independent native repaints,
  theme updates, native handoff and stale/unbound view associations. Report
  guard installation and blocked-write counts without user/channel identifiers.
- Device-confirmed build 33's guarded library highlight. Reuse the chat emote
  details sheet when holding a provider preview in the composer or a provider
  library, Recent or suggestion tile. Suppress UIKit's generic image actions
  only for verified owned composer attachments, with modern text-item and
  legacy attachment delegate paths; preserve native/foreign attachment and
  link menus. Defer presentation until UIKit returns, coalesce repeated requests,
  and ignore removed attachments/detached inputs. Cancel tile tracking when a
  hold recognizes, preventing an extra insertion on release. Read current cell
  metadata after reuse without changing tap insertion or horizontal scrolling.
- Device-confirmed build 34 library holds; composer details opened too early
  and its window-level suggestions overlaid the sheet. Give the composer an
  owned long-press recognizer with the same explicit 0.5-second duration as
  library tiles. UIKit image-menu callbacks only suppress generic actions and
  cannot authorize presentation. Hit-test actual owned attachment glyph bounds,
  retain native selection/scroll gestures, and replace the recognizer when the
  editor changes. Hide suggestions before presenting details; pending details
  and any modal in the owning controller chain block subsequent layout raises.
  Restore normal suggestion placement after dismissal. Cover early callbacks,
  gesture states, shared timing, whitespace/native/IME rejection, editor reuse,
  failed presentation, parent modals and repeated sheet-time layout ticks.
- Device-confirmed build 35 composer hold timing and sheet layering. Give the
  owned composer hold priority over native image gestures on provider previews,
  and emit one light haptic only after successfully opening details. Reject
  ordinary/native text and marked input at touch-down so native editing gestures
  keep their behavior. Library feedback is unchanged. Cover touch location,
  scoped gesture priority, duplicate/stale/failed requests and haptic counts.
- Device-confirmed build 36 single composer haptic. Fix the browser handoff
  starting before the emote sheet's animated dismissal: dismiss only our owned
  navigation wrapper and open the URL from its completion. Coalesce repeat taps,
  preserve the URL across sheet destruction, and skip launch if another event
  has made Twitch inactive. No dismissals are initiated after leaving Twitch.
  Cover action ordering, detached/wrong wrappers, lifecycle interruption, URL
  lifetime, repeat taps and unchanged Copy/Done actions at the UIKit boundary.
- Device-confirmed build 37 browser return. Recover provider chat animations
  that pause after their last layout/image event using one one-second timer
  and weak layer membership. Preserve Twitch's decoder/playhead, repair an
  exhausted provider countdown, and leave native emotes untouched. Require an
  active app, visible ancestors, a window and intersection with clipping/chat
  bounds; stop the timer when no tracked emotes are visible. Existing foreground
  hook retries restart recovery. Expose count-only recovery checks in diagnostics.
- Preserve valid composer GIF delays above ten seconds, including final-frame
  holds, instead of replacing them with 0.1 seconds. Accept ImageIO rounding at
  20 ms while retaining fallbacks for missing/nonfinite/invalid delays. The
  inspected chat player already sums every frame's delay; no last-frame exclusion
  was found in source history. Cover long final-frame playback, rounding, idle
  recovery, foreground/reattachment, clipping, weak removal and native reuse.
- Candidate bundle build: `3.0.0.38`; animation edge-case fixes await device testing.

## 2.3.1 (prepared; not published)

- Accept bounded provider responses up to 8 MiB and retain up to 4,000 emotes
  per channel. Live 7TV channel sets exceeded the old 2 MiB response limit;
  valid HTTP 200 responses were discarded before parsing. Separate HTTP,
  transport, body-size/empty, JSON/schema failures, and absent channels in
  diagnostics, with status/byte/entry counts and no channel IDs or API bodies.
- Clear pending fetch state even when session or task creation fails, so the
  existing retry path can recover. Test both large channel responses and
  response-limit/error boundaries. Candidate bundle build is `2.3.1.2`.
- Replace the active sideload loader, install name, signing identifier, and
  bundle metadata with `Streamside.framework/Streamside`. Initialization still
  uses the native C constructor; no donor runtime or filename is required.
- Normalize both native build outputs to their 16 KiB segment ranges and reject
  incorrect offsets, sizes, gaps, overlaps, sections, or trailing linkedit ranges.
- Validate exact required load commands, code-signature placement/reservations,
  CodeDirectory identity/executable range, and every code-page hash.
- Record a build fingerprint after normalization. IPA, DEB, and distribution
  packagers require it and compare actual packaged binary bytes, failing closed
  instead of normalizing a different binary silently. IPA output is verified
  before atomic replacement and old injected frameworks/loads are removed.
- Add corruption and normalization-regression tests to ordinary build CI.
  Release publication still requires separate user approval; none is performed.

## 2.3.0 (third-party emotes and native chat integration)

- Accept TWChatMessage.senderId's NSNumber bridge. Dev.7 rejected every
  local message before token matching because it required NSString.
- Correct provider ImageAttachmentLayer frames as well as TextKit spacing.
  Resolve the strong image-data field only after validating the runtime tuple
  span; scope frame changes to registered synthetic provider image IDs.
- Add a layer layout fallback and aggregate frame/ID/resize counters.
- Regression coverage includes NSNumber sender IDs, non-square image frames,
  repeated adjustment, unchanged native frames, and unexpected tuple spans.
- Device-confirmed on Twitch 30.4.2: incoming static and animated emotes,
  proportional image widths, own sent emotes, Reload Emotes in Chat Settings,
  and provider detail sheets.

## 2.3.0-dev.7 (development; corrections from device diagnostics)

- Resolve emote-map values through TWMessageEmoteToken.emoteId, fixing the
  shared lookup used by proportional sizing and provider tap details.
- Cover native and base TextKit attachment callbacks; Swift can bypass
  Objective-C sizing bridges. Keep this fallback scoped to Twitch chat.
- Replace the uncalled Kotlin send-constructor hook with the native chat
  delivery callback. Convert provider words in the current user's text tokens
  while preserving native tokens, message IDs, tags, replies, and badges.
- Separate delivery and sizing invocation counters from successful matches.
- Device-confirmed in dev.6: scrolling Reload Emotes row works. Incoming
  provider fetches and images succeeded; own sends, proportions, and taps
  failed. The dev.7 corrections still need an on-device retest.

## 2.3.0-dev.6 (development; emote UI and local messages)

- Preserve provider emote proportions in message sizing and native attachments.
  Learn dimensions from provider APIs or bounded GIF/PNG/WebP headers.
- Add channel/global third-party definitions to the local outgoing-message
  tokenizer while preserving native Twitch emotes and the original message text.
- Replace the chat settings overlay button with a scrolling Reload Emotes row.
- Intercept third-party emote taps with a provider sheet: animated preview,
  name, provider/scope, creator credit when supplied, Copy name, Copy image URL,
  and Open in browser. Native emote taps continue through Twitch.
- Add aggregate hook, local-message, sizing, hit-test, and popup diagnostics.
- Device verification is pending; private hooks target decrypted Twitch 30.4.2.

## 2.3.0-dev.5 (development; emote matching and chat-menu fix)

- Match third-party emote names at the start or end of punctuation-delimited
  chat words, and report scanned words and punctuation matches.
- Hook Twitch's native `TwitchCoreUI.ActionSheetViewController` and add a
  Reload Emotes button to the stream chat action sheet.
- Register the button action and retry hook installation after Twitch launches;
  report hook installation, sheet appearances, button insertions, and taps.
- Requires device verification for both emote rendering and menu placement.

## 2.3.0-dev.4 (development; provider image and menu tracing)

- The dev.3 report showed four rewritten chat frames and two delegate-based
  image tasks, but no observable image responses or Chat Settings action sheet.
- Observe only enabled third-party CDN image responses through the existing
  URL protocol, including HTTP status and MIME type. Count registry entries,
  matched emote words, and provider fetch failure categories without retaining
  chat text, room IDs, or URLs.
- Record the presented navigation controller's top and visible controller
  classes to identify Twitch's actual three-dot chat menu implementation.
  Reload Emotes placement is still pending device verification.

## 2.3.0-dev.3 (development; image/menu diagnosis)

- The dev.2 report confirmed provider fetches, incoming IRC rewrites, and
  synthetic image redirects, while the previous chat-menu hooks saw no sheet.
- Added aggregate image response status/MIME counters and a targeted chat
  settings button and presentation probe. No chat text, room IDs, or image URLs
  are recorded.

## 2.3.0-dev.2 (development; device retest pending)

- Added privacy-safe emote and chat-menu counters to the diagnostic report.
- Hooked inherited WebSocket receive implementations and recognized sheets
  presented by Twitch's ChatSettingsController without an exact title match.
- Kept the emote switch off by default and the published 2.2.1 assets unchanged.

## 2.3.0-dev.1 (development; device validation pending)

- Added optional 7TV, BTTV, and FFZ global and channel emotes to incoming chat.
- Added a relaunch-gated emote switch and Clear Emote Cache to Ad Block, plus
  Reload Emotes in the stream Chat Settings action sheet.
- Bounded per-room maps and image-ID history, with idle expiry and API retry
  backoff. No separate emote image files are stored by the module.
- Built the same source for the IPA framework and rootful/rootless jailbreak
  packages. The emote hooks and menu placement still need on-device testing.

## 2.2.1 source-backed replacement (IPA and jailbreak prerelease)

- Reconstructed the R5 diagnostics in checked-in source. Both package formats
  now use the same implementation of temporary channel and resource labels,
  route registration history, and retired-route reasons for unmapped variants.
- Logging remains off by default. The older 2.2.0 diagnostic log containing
  request paths is removed on first initialization of this build.
- Retains the device-confirmed main Settings button scope fix. These new
  replacement binaries have not yet been tested on a device.

## 2.2.1 original IPA (superseded)

- Added opt-in diagnostics with temporary channel and playlist labels that
  reset when Twitch restarts, plus route history for investigating playback.
- Clarified in the app that diagnostic logging starts off and explained the
  lifetime of those labels.
- Limited the Ad Block button to the main Settings screen; fixed its absence
  in the R6 candidate and its appearance on Chat Identity in the R5 build.
- Published the device-confirmed R7 behavior with a 2.2.1 build label.
- The separately versioned 2.2.1-jb source build has the Settings entry fix,
  but lacks the IPA's newer R5 privacy and route diagnostics.

## 2.2.1-jb original packages (superseded)

- Built the standalone rootful and rootless packages from the checked-in
  source with the main Settings button fix.
- Kept the original 2.2.0 diagnostics implementation; R5's newer privacy
  labels and route history are not present in these packages.

## 2.2.0

- Added an Ad Block entry to Twitch's profile settings screen.
- Added persistent, opt-in diagnostic logging with a 512 KiB cap.
- Added an in-app diagnostic report with session counters, viewing, copying,
  and clearing controls.
- Sanitized all logged URLs and excluded query strings, fragments, headers,
  access tokens, and manifest contents.
- Logged HLS interception, manifest classification, VAFT candidate selection,
  access-token failures, clean swaps, unmapped variants, and suppressed
  segments.
- Restored the proven `Tweach.framework/Tweach` physical path for sideload
  compatibility while retaining `TwitchAdBlock.dylib` for jailbreak packages.
- Normalized the sideload framework's Mach-O segments to 16 KiB boundaries so
  ESign and LiveContainer/ZSign can replace its signature successfully.
- Updated the build, verification, patching, tests, and release tooling for the
  framework-based sideload layout.

## 2.1.0

- Renamed the native library and load command to `TwitchAdBlock.dylib`.
- Added standalone rootful and rootless jailbreak DEB packages scoped to the
  Twitch bundle.
- Added DEBs to automated builds, release archives, and checksums.
- The clean dylib identity remains the jailbreak packaging path; sideload
  builds subsequently returned to the compatibility path in 2.2.0.

## 2.0.3

- Replaced the single global stream slot with per-channel VAFT contexts.
- Mapped each media-playlist URL to the master playlist that produced it.
- Scoped clean variants and alternate-player caches to their owning stream.
- Fixed profile previews that could clone the active PiP stream or turn black.
- Added a local IPA patcher, Mach-O verification, tests, and reproducible
  GitHub Actions builds.
