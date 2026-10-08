/* Unified RN suggestions. Twitch keeps its input/tokenizer and catalog.
 * Stock autocomplete takeover is conditional. Context scopes input adapters; no
 * last-room fallback or global draft/selection state. */
function install(original) {
  var React = __r(72); React = React.default || React;
  var RN = __r(5), ui = __r(2118);
  var bridge = __r(16).default.buildLocalEcho;
  var inputs = __r(3759), NativeInput = inputs.EmoteTextInput;
  var autocomplete = __r(4619), caretFromEdit = autocomplete.caretFromEdit;
  var nativeAutocomplete = autocomplete.useAutocomplete;
  var suggestions = __r(4713), NativeSuggestions = suggestions.ChatAutocompleteTray;
  if (!React.createContext || !React.useContext || !RN.ScrollView || !RN.Pressable ||
      !ui.useTheme || !NativeInput || !caretFromEdit || !nativeAutocomplete || !NativeSuggestions ||
      !autocomplete.EMOTE_URL_TEMPLATE || !autocomplete.EMOTE_URL_TEMPLATE_STATIC ||
      !bridge || !bridge.getState || !bridge.search) return original;
  var Context = React.createContext(null);
  function properties(style) { var p = {}; p.style = style; return p; }
  function space(c) {
    return c === 32 || c === 9 || c === 10 || c === 13 || c === 160 ||
      (c >= 8192 && c <= 8202) || c === 8232 || c === 8233 || c === 12288;
  }
  function completion(text, start, end, mode) {
    if (typeof text !== "string" || mode < 0 || mode > 1 || start !== end ||
        start <= 0 || start > text.length || Math.floor(start) !== start ||
        (start < text.length && !space(text.charCodeAt(start)))) return null;
    var from = start;
    while (from && !space(text.charCodeAt(from - 1)) && text.charCodeAt(from - 1) !== 65532) from--;
    var prefix = from;
    if (text.charCodeAt(from) === 58) prefix++;
    else if (mode === 1) return null;
    if (start - prefix > 96 || (prefix === from && start - prefix < 2)) return null;
    for (var i = prefix; i < start; i++) {
      var c = text.charCodeAt(i);
      if (c === 58 || c === 47 || c === 64 || c === 65532) return null;
    }
    var r = {}; r.start = from; r.end = start; r.text = text.slice(prefix, start); return r;
  }
  function state() {
    try { return bridge.getState(); } catch (error) { return null; }
  }
  function takeover(config) { return !!config && !!config.enabled && (config.mode === 0 || config.mode === 1); }
  function useConfig() {
    var pair = React.useState(state), config = pair[0], update = pair[1];
    React.useEffect(function () {
      var timer = setInterval(function () {
        var next = state();
        update(function (old) {
          return old && next && old.mode === next.mode && old.enabled === next.enabled ? old : next;
        });
      }, 250);
      return function () { clearInterval(timer); };
    }, []);
    return config;
  }
  function emoteMatches(matches) {
    return Array.isArray(matches) && matches.length > 0 && matches[0].type === "emote";
  }
  function StockSuggestions(p) {
    var config = useConfig();
    return takeover(config) && emoteMatches(p.matches) ? null : React.createElement(NativeSuggestions, p);
  }
  var providerCache = new WeakMap();
  function useAutocomplete(draft, setDraft, providers, onCompleteSuggestion) {
    var active = takeover(state()), filtered = providers;
    // This adapter adds NO React hooks: the parent can have rendered before
    // this child factory installs it. Keep Twitch's existing hook sequence.
    if (active && Array.isArray(providers)) {
      filtered = providerCache.get(providers);
      if (!filtered) {
        filtered = providers.filter(function (value) { return !value || value.autocompleteType !== "emote"; });
        if (filtered.length === providers.length) filtered = providers;
        providerCache.set(providers, filtered);
      }
    }
    var result = nativeAutocomplete(draft, setDraft, filtered, onCompleteSuggestion);
    // Twitch retains matches in state until an edit. Hide a pre-takeover
    // emote match before its composer hook constructs native Send handlers.
    if (active && emoteMatches(result.matches)) {
      var copy = Object.assign({}, result); copy.matches = null;
      copy.confirmHighlightedMatch = function () { return null; };
      return copy;
    }
    return result;
  }
  function entriesFor(data, query) {
    var entries = [], map = data.emoteMap;
    var template = data.emoteAnimationsEnabled === false ? autocomplete.EMOTE_URL_TEMPLATE_STATIC : autocomplete.EMOTE_URL_TEMPLATE;
    if (map && typeof map === "object") {
      var keys = Object.keys(map), needle = query.toLowerCase();
      if (keys.length <= 20000) for (var i = 0; i < keys.length; i++) {
        var name = keys[i], id = map[name];
        if (!name || name.length > 96 || name.toLowerCase().indexOf(needle) < 0 ||
            typeof id !== "string" || !id || id.length > 256) continue;
        var item = {}; item.name = name; item.id = id; item.native = true; item.aspect = 1;
        item.url = template.replace("{id}", encodeURIComponent(id)); entries.push(item);
      }
    }
    try {
      var provider = bridge.search(data.channelID, query);
      for (var i = 0; provider && i < provider.length; i++) {
        if (!map || !Object.prototype.hasOwnProperty.call(map, provider[i].name)) entries.push(provider[i]);
      }
    } catch (error) {}
    entries.sort(function (a, b) {
      var x = a.name.toLowerCase(), y = b.name.toLowerCase();
      return x < y ? -1 : x > y ? 1 : a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });
    return entries.slice(0, 64);
  }
  function Input(p) {
    var context = React.useContext(Context);
    if (!context) return React.createElement(NativeInput, p);
    var copy = Object.assign({}, p);
    copy.onSelectionChange = function (event) {
      var selection = event && event.nativeEvent && event.nativeEvent.selection;
      if (selection) context.onSelectionChange(p.value, selection);
      if (p.onSelectionChange) p.onSelectionChange(event);
    };
    copy.onChangeText = function (text) {
      context.onChangeText(text);
      if (p.onChangeText) p.onChangeText(text);
    };
    copy.onFocus = function (event) { context.onFocus(); if (p.onFocus) p.onFocus(event); };
    copy.onBlur = function (event) { context.onBlur(); if (p.onBlur) p.onBlur(event); };
    if (context.selection && context.selection.text === p.value) copy.selection = context.selection;
    return React.createElement(NativeInput, copy);
  }
  function Composer(p) {
    var theme = ui.useTheme();
    var configState = React.useState(state), config = configState[0], setConfig = configState[1];
    var focusState = React.useState(!!p.inputFocused), focused = focusState[0], setFocused = focusState[1];
    var selectionState = React.useState(null), selection = selectionState[0], setSelection = selectionState[1];
    var pendingState = React.useState(null), pending = pendingState[0], setPending = pendingState[1];
    var current = React.useRef(null), scroll = React.useRef(null), native = React.useRef(null);
    React.useEffect(function () {
      if (!native.current || native.current.channelID !== p.channelID || native.current.text !== p.draft) {
        native.current = {}; native.current.text = p.draft; native.current.channelID = p.channelID;
        setSelection(null); setPending(null);
      }
    }, [p.channelID, p.draft]);
    React.useEffect(function () {
      if (!focused) return;
      function refresh() {
        var next = state();
        setConfig(function (old) {
          if (old && next && old.mode === next.mode && old.revision === next.revision && old.enabled === next.enabled) return old;
          return next;
        });
      }
      refresh(); var timer = setInterval(refresh, 250);
      return function () { clearInterval(timer); };
    }, [focused]);
    var caret = selection && selection.channelID === p.channelID && selection.text === p.draft ? selection : null;
    var span = null;
    if (takeover(config) && focused && p.canSend && !p.viewerBanned && !p.viewerTimedOut && caret) {
      span = completion(p.draft, caret.start, caret.end, config.mode);
    }
    var entries = React.useMemo(function () {
      if (!span) return null;
      return entriesFor(p, span.text);
    }, [p.channelID, span && span.text, !!span, config && config.revision, p.emoteMap, p.emoteAnimationsEnabled]);
    current.current = {}; current.current.data = p; current.current.selection = caret;
    current.current.span = span; current.current.mode = config && config.mode;
    current.current.focused = focused;
    React.useEffect(function () {
      if (scroll.current && scroll.current.scrollTo) { var point = {}; point.x = 0; point.animated = false; scroll.current.scrollTo(point); }
    }, [p.channelID, span && span.text]);
    function choose(item) {
      var latest = current.current, data = latest.data, selected = latest.selection, fresh = state();
      if (!takeover(fresh) || !latest.focused || !data.canSend || data.viewerBanned || data.viewerTimedOut ||
          !selected || !data.onDraftChange ||
          data.draft !== p.draft || data.channelID !== p.channelID || !span ||
          selected.start !== caret.start || selected.end !== caret.end ||
          !native.current || native.current.text !== data.draft || native.current.channelID !== data.channelID ||
          native.current.start !== selected.start || native.current.end !== selected.end) return;
      var range = completion(data.draft, selected.start, selected.end, fresh.mode);
      if (!range || !latest.span || range.start !== latest.span.start || range.end !== latest.span.end ||
          range.text !== latest.span.text || fresh.mode !== latest.mode) return;
      // Re-resolve in the current room before applying a possibly stale row.
      var found = entriesFor(data, range.text), valid = false;
      for (var i = 0; i < found.length; i++) if (found[i].id === item.id && found[i].name === item.name && !!found[i].native === !!item.native) valid = true;
      if (!valid) return;
      var tail = data.draft.slice(range.end), suffix = tail && space(tail.charCodeAt(0)) ? "" : " ";
      var value = data.draft.slice(0, range.start) + item.name + suffix + tail;
      if (typeof data.remaining === "number" && value.length - data.draft.length > data.remaining) return;
      var next = {}; next.text = value; next.channelID = data.channelID;
      next.start = range.start + item.name.length + suffix.length; next.end = next.start;
      native.current = next; setPending(next); setSelection(next); data.onDraftChange(value);
    }
    var context = {};
    context.selection = pending && pending.channelID === p.channelID && pending.text === p.draft ? pending : null;
    context.onSelectionChange = function (text, value) {
      // A text change may precede the parent value prop update. Selection is
      // emitted against that newer native text, not the stale React prop.
      if (native.current && native.current.channelID === p.channelID && native.current.text !== p.draft) text = native.current.text;
      var next = {}; next.text = text; next.channelID = p.channelID; next.start = value.start; next.end = value.end;
      native.current = next; setSelection(next);
      if (pending && pending.text === text) setPending(null);
    };
    context.onChangeText = function (text) {
      // Same verified donor caret helper as Twitch's autocomplete hook. This
      // covers selection-before-change delivery; a later selection overrides
      // the inferred position. Draft/send payloads remain ordinary strings.
      var before = native.current && native.current.channelID === p.channelID ? native.current.text : p.draft;
      var next = {}; next.text = text; next.channelID = p.channelID;
      next.start = before === text && native.current ? native.current.start : caretFromEdit(before, text); next.end = next.start;
      native.current = next; setSelection(next); setPending(null);
    };
    context.onFocus = function () { setFocused(true); };
    context.onBlur = function () { native.current = null; setFocused(false); setSelection(null); setPending(null); };
    var strip = null;
    if (span && entries && entries.length) {
      var children = [], label = {}; label.fontSize = 11; label.color = theme.colors.textAlt;
      label.marginTop = 2; label.maxWidth = 100;
      for (var i = 0; i < entries.length; i++) {
        var item = entries[i];
        var cell = {}; cell.height = 60; cell.minWidth = 52; cell.maxWidth = 112;
        cell.paddingHorizontal = 6; cell.alignItems = "center"; cell.justifyContent = "center";
        var button = properties(cell); button.key = item.name + "/" + (item.native ? item.url : item.id); button.accessibilityRole = "button";
        button.accessibilityLabel = item.name; button.onPress = (function (value) { return function () { choose(value); }; })(item);
        var image = {}; image.height = 32; image.width = Math.min(96, 32 * Math.max(0.1, item.aspect));
        var ip = properties(image), source = {}; source.uri = item.url; ip.source = source; ip.resizeMode = "contain";
        var text = properties(label); text.numberOfLines = 1;
        children.push(React.createElement(RN.Pressable, button, React.createElement(RN.Image, ip), React.createElement(RN.Text, text, item.name)));
      }
      if (children.length) {
        var style = {}; style.height = 60; style.flexGrow = 0; style.backgroundColor = theme.colors.backgroundBase;
        var sp = properties(style); sp.horizontal = true; sp.showsHorizontalScrollIndicator = false;
        sp.keyboardShouldPersistTaps = "always"; sp.ref = scroll;
        strip = React.createElement(RN.ScrollView, sp, children);
      }
    }
    var provider = {}; provider.value = context;
    var surface = {}; surface.minWidth = 0; surface.alignSelf = "stretch";
    return React.createElement(Context.Provider, provider,
      React.createElement(RN.View, properties(surface), strip, React.createElement(original, p)));
  }
  // Assign only verified, writable leaf exports. Public barrels use live
  // getters. Roll back every adapter if any export cannot be installed.
  try {
    inputs.EmoteTextInput = Input; autocomplete.useAutocomplete = useAutocomplete;
    suggestions.ChatAutocompleteTray = StockSuggestions;
  } catch (error) {
    inputs.EmoteTextInput = NativeInput; autocomplete.useAutocomplete = nativeAutocomplete;
    suggestions.ChatAutocompleteTray = NativeSuggestions;
    return original;
  }
  return Composer;
}
