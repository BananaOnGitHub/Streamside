# Emote settings

Preferences separate enabling the provider integration from changing how an already enabled UI behaves.

| Control | Lifetime | Effect |
| --- | --- | --- |
| Third-party emotes | Saved; read once at launch | Enables provider hooks/fetches after a full app restart |
| Suggestions: Automatic / Colon / Off | Saved; immediately observed | Changes owned completion presentation, not manual browsing or chat rendering |
| Reload Emotes | Explicit action | Retires definitions, changes fetch generations, and refreshes global/selected room catalogs |
| Clear Emote Cache | Explicit action | Drops owned definitions/mappings; lazy loading resumes from later room observations |
| Diagnostic Logging | Independent saved toggle | Controls persistent sanitized event logs; aggregate counters remain available |

The preference keys include `TASThirdPartyEmotesEnabled`, `StreamsideEmoteSuggestions`, and `StreamsideRecentEmotes`. Their ownership is in [TASEmotes.c](../../../src/TASEmotes.c), [SSComposer.c](../../../src/SSComposer.c), and [TASDiagnostics.c](../../../src/TASDiagnostics.c).

## Launch gating

With emotes disabled at launch, `tas_emotes_initialize()` does not install emote receive/image/UI hooks or initiate provider requests. The Streamside settings page remains available. Toggling the preference during a launch is not a complete uninstall/reinstall of runtime hooks; restart Twitch to apply it.

Suggestion modes are a smaller live configuration. RN polls the tiny mode/revision/enabled snapshot while relevant surfaces are active; catalog results are memoized by query/revision rather than rebuilt on every poll. Legacy refreshes its exact focused input state.

## Reload scope

RN's reload bridge requires an enabled admitted integration and exactly one known room for the sheet's explicit channel ID/login. Unknown or ambiguous channels are refused. A background last-room observation cannot redirect the action to another channel.

`reload_emotes_for_room()` retires current identities, advances generations, and refetches global and selected-channel definitions. Stale outstanding provider completions cannot repopulate the previous generation.

The legacy chat-menu action uses its existing native sheet integration. The root Streamside page owns enable, suggestion, and clear controls; the stream Chat Settings sheet owns the convenient reload action.

## RN menu integration

The exact donor registers the settings factory function 4884 as Metro module **4880**. Those IDs are not interchangeable. [ProviderEmoteStrip.js](../../../src/rn/ProviderEmoteStrip.js) wraps the writable `ChatSettingsSheet` export and routes only the `chat-settings-scroll` surface.

Main-page admission checks a child with settings, an onRequestClose function, and presence of the `containerSections` prop. The prop may be undefined, null, or empty; requiring a truthy value had hidden the row in build 90.

Reload is the first scroll row beneath the title and before Identity. Subpages preserve native UI. Presses recheck enabled/visible state, call the explicit-channel reload, and close the sheet.

Its Pressable style uses `theme.colors.backgroundElevation1` while pressed and transparent otherwise. React Native owns touch/hold/release/scroll-cancellation feedback. A custom long-press state machine is unnecessary.

## Clear is not a global image purge

Clear Emote Cache targets registry definitions and image-ID mappings. It does not clear Twitch's unrelated decoded cache, Foundation's configured provider HTTP cache, every composer GIF/thumbnail cache, or native Twitch history. “Clear everything” would describe a different operation.

Reload is normally the action for changed channel emotes. Existing Recently used names persist and are resolved against newly available definitions when a menu opens.

## Tests and evidence

[RN strip tests](../../../tests/test_rn_strip.py) and the compiled [settings donor fixture](../../../tests/fixtures/rn_settings_donor.js) check module registration, real donor factory/component execution, main/subpage admission, optional props, explicit scope, and both pressed styles.

[RN composer tests](../../../tests/test_rn_composer_ui.py) cover native reload refusal/generations alongside provisional-input handling. Device results for builds 89–92 are recorded in [History](../../HISTORY.md); the failed module/prop guards are not current pending features.

[Feature map](README.md) · [Diagnostics](../DIAGNOSTICS.md) · [README setup](../../../README.md#installation)
