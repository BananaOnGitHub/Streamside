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
  var composerHooks = __r(4687) || {}, nativeComposer = composerHooks.useChatComposer;
  var smartBackspace = (__r(3758) || {}).smartBackspace, aliases = (__r(3382) || {}).emoteTokenAliases;
  if (!React.createContext || !React.useContext || !RN.ScrollView || !RN.Pressable ||
      !ui.useTheme || !NativeInput || !caretFromEdit || !nativeAutocomplete || !NativeSuggestions ||
      !autocomplete.EMOTE_URL_TEMPLATE || !autocomplete.EMOTE_URL_TEMPLATE_STATIC ||
      !bridge || !bridge.getState || !bridge.search) return original;
  var Context = React.createContext(null);
  // Demand-only wrapper: original Image type/source/style and handlers remain
  // intact. Effects count committed JS instances, never attempted renders.
  function observe(event, scope, asset, a, b) {
    if (bridge.observe) try { bridge.observe(event, scope, asset || "", a || 0, b || 0); } catch (error) {}
  }
  function DemandImage(p) {
    var ip = p.data, scope = p.index, uri = ip.source && ip.source.uri || ip.src;
    var current = React.useRef(null);
    function signal(event, asset, duration) {
      if (p.context) observe(22, 0, null, p.context.type, p.context.index);
      observe(event, scope, asset, duration);
    }
    React.useEffect(function () { signal(1, uri); return function () { signal(2, uri); }; }, [scope]);
    React.useEffect(function () {
      observe(0, scope);
      if (!current.current || current.current.uri !== uri) {
        current.current = {}; current.current.uri = uri; current.current.start = performance.now(); current.current.loaded = false;
        signal(3, uri);
      } else observe(4, scope);
    });
    var copy = Object.assign({}, ip);
    if(scope !== 5) copy.testID = scope === 1 ? "provider" : scope === 2 ? "recents" : scope === 3 ? "emote" : "EmoteCard";
    copy.onLoadStart = function (event) { signal(5); if (ip.onLoadStart) ip.onLoadStart(event); };
    copy.onLoad = function (event) {
      var latest = current.current;
      if (latest && latest.uri === uri && !latest.loaded) {
        latest.loaded = true; signal(6, null, Math.max(0, performance.now() - latest.start));
      } else if (!latest || latest.uri !== uri) observe(14, scope);
      if (ip.onLoad) ip.onLoad(event);
    };
    copy.onError = function (event) { signal(7); if (ip.onError) ip.onError(event); };
    return React.createElement(p.type || RN.Image, copy);
  }
  function imageElement(ip, scope, trace) {
    if (!bridge.observe) return React.createElement(RN.Image, ip);
    var p = {}; p.data = ip; p.index = scope; p.context = trace; return React.createElement(DemandImage, p);
  }
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
  // No additional hook slots or catalog mutations. Use Twitch's functional
  // draft setter and its existing token/Unicode deletion helper. Recognition
  // adds provider codes only in this hook's explicit channel, including Off.
  function useChatComposer(p) {
    var result = nativeComposer(p), config = state();
    if (!config || !config.enabled || !result.setDraft) return result;
    var copy = Object.assign({}, result);
    copy.backspaceDraft = function () {
      result.setDraft(function (value) {
        if (typeof value !== "string") return value;
        function recognized(code) {
          if (Object.prototype.hasOwnProperty.call(p.emoteTokenMap || {}, code) ||
              Object.prototype.hasOwnProperty.call(result.cheermoteTokenImages || {}, code) ||
              (p.emoteSuggestions || []).some(function (item) { return aliases(item.token).includes(code); })) return true;
          var fresh = state();
          if (!fresh || !fresh.enabled) return false;
          try {
            return !!bridge.lookup(p.channelID, code);
          } catch (error) { return false; }
        }
        return smartBackspace(value, value.length, recognized).value;
      });
    };
    return copy;
  }
  function useConfig() {
    var pair = React.useState(state), config = pair[0], update = pair[1];
    React.useEffect(function () {
      var timer = setInterval(function () {
        var next = state();
        update(function (old) {
          return old && next && old.mode === next.mode && old.revision === next.revision && old.enabled === next.enabled ? old : next;
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
      if (!item.native && bridge.remember) try { bridge.remember(data.channelID, item.name, item.id); } catch (error) {}
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
        children.push(React.createElement(RN.Pressable, button, imageElement(ip, 3), React.createElement(RN.Text, text, item.name)));
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
  /* The donor's library leaf uses JSX runtime 245 for exactly two verified
   * surfaces. Route those elements through context; other JSX calls retain
   * their original type, props, key and runtime. No hooks enter donor bodies. */
  var trays = __r(4174), NativeLibrary = trays.EmotePickerTray;
  var jsxRuntime = __r(245), nativeJSX = jsxRuntime.jsx, nativeJSXS = jsxRuntime.jsxs;
  var LibraryContext = React.createContext(null);
  var librarySequence = 0, calculationSequence = 0;
  function snapshot(channel) {
    try { return bridge.getSnapshot(channel); } catch (error) { return null; }
  }
  function Library(p) {
    var child = {}; child.data = p; child.key = p.channelID + "/" + p.emotePickerSID;
    return React.createElement(LibrarySession, child);
  }
  function LibrarySession(child) {
    var p = child.data, config = useConfig(), theme = ui.useTheme();
    var opened = React.useRef(null), list = React.useRef(null), latest = React.useRef(null);
    var trace = React.useRef(null);
    if (bridge.observe && !trace.current) { trace.current = {}; trace.current.index = ++librarySequence; trace.current.type = 0; }
    React.useEffect(function () { return function () {
      if (trace.current) { trace.current.type = 4; observe(22, 0, null, 4, trace.current.index); }
    }; }, []);
    var filter = React.useState(0), provider = filter[0], setProvider = filter[1];
    var domain = React.useState(0), scope = domain[0], setScope = domain[1];
    var highlight = React.useState(false), active = highlight[0], setActive = highlight[1];
    var details = React.useState(null), card = details[0], setCard = details[1];
    var data = React.useMemo(function () {
      return config && config.enabled ? snapshot(p.channelID) : null;
    }, [p.channelID, config && config.enabled, config && config.revision]);
    // Freeze the first admitted snapshot for this opening, including empty
    // recents. Catalog refresh and insertion never replace this snapshot.
    if (data && !opened.current) opened.current = data.recents.slice(0, 40);
    latest.current = p;
    if (!data) return React.createElement(NativeLibrary, p);
    var value = {}; value.data = data; value.recents = opened.current;
    value.trace = trace.current;
    value.provider = provider; value.scope = scope;
    function changed() { if (trace.current) { trace.current.type = 5; observe(22, 0, null, 5, trace.current.index); } }
    value.onValueChange = function (next) { changed(); setProvider(next); setScope(0); };
    value.onChange = function (next) { changed(); setScope(next); };
    value.active = active; value.setActive = setActive; value.theme = theme; value.list = list;
    value.onSelectEmote = function (item) {
      var current = latest.current, fresh = state();
      if (!fresh || !fresh.enabled || current.channelID !== p.channelID || !current.onSelectEmote) return;
      var valid = null;
      try { valid = bridge.remember(current.channelID, item.name, item.id); } catch (error) {}
      if (valid) current.onSelectEmote(valid.name, ""); // Donor appendToken expects an ordinary string.
    };
    value.info = function (item) {
      try { var m = bridge.getMetadata(item.id); if (m) setCard(m); } catch (error) {}
    };
    var copy = p;
    if (!p.sections || !p.sections.length) {
      // Give the native tray a grid surface while its own catalog is empty.
      // The seed is removed before the real SectionList receives its rows.
      copy = Object.assign({}, p); var seed = {}; seed.id = "provider"; seed.title = data.title; seed.emotes = [];
      copy.sections = [seed];
    }
    var cp = {}; cp.value = value;
    var content = React.createElement(NativeLibrary, copy);
    var popup = null;
    if (card) { var pp = {}; pp.data = card; pp.onClose = function () { setCard(null); }; popup = React.createElement(LibraryInfo, pp); }
    return React.createElement(LibraryContext.Provider, cp, content, popup);
  }
  function LibraryInfo(p) {
    var m = p.data, theme = ui.useTheme(), options = {}; options.initialVisible = true; options.onPlainClose = p.onClose;
    var handoff = ui.useSheetHandoff(options), pending = React.useRef(-1);
    var surface = {}; surface.padding = 24; surface.backgroundColor = theme.colors.backgroundBase;
    var title = {}; title.fontSize = 22; title.color = theme.colors.textBase;
    var sub = {}; sub.fontSize = 14; sub.color = theme.colors.textAlt; sub.marginTop = 8;
    var image = {}; image.height = 112; image.width = Math.min(280, 112 * Math.max(0.1, m.aspect)); image.alignSelf = "center";
    var ip = properties(image), source = {}; source.uri = m.url; ip.source = source; ip.resizeMode = "contain";
    function button(label, action) {
      var style = {}; style.paddingVertical = 14;
      var bp = properties(style); bp.accessibilityRole = "button"; bp.accessibilityLabel = label;
      bp.onPress = function () { pending.current = action; handoff.onClose(); };
      return React.createElement(RN.Pressable, bp, React.createElement(RN.Text, properties(sub), label));
    }
    var content = React.createElement(RN.View, properties(surface), imageElement(ip, 4),
      React.createElement(RN.Text, properties(title), m.name), React.createElement(RN.Text, properties(sub), m.subtitle),
      button(m.title, 0), button(m.label, 1), button(m.openURL, 2), button(m.closeLabel, -1));
    var sp = {}; sp.visible = handoff.visible; sp.onClose = handoff.onClose;
    sp.onClosed = function () { handoff.onClosed(); var action = pending.current; pending.current = -1; if (action >= 0) bridge.sendAction(m.id, action); };
    sp.initialDetent = false; sp.disableBodyInlinePadding = true; sp.accessibilityLabel = m.name;
    return React.createElement(ui.BottomSheet, sp, content);
  }
  function tile(item, context, width, scope) {
    var style = {}; style.width = width; style.height = 52; style.alignItems = "center"; style.justifyContent = "center";
    var bp = properties(style); bp.key = item.id; bp.accessibilityRole = "button"; bp.accessibilityLabel = item.name;
    bp.onPress = function () { context.onSelectEmote(item); }; bp.onLongPress = function () { context.info(item); };
    var image = {}; image.height = Math.min(40, (width - 8) / Math.max(0.1, item.aspect));
    image.width = Math.min(width - 8, 40 * Math.max(0.1, item.aspect));
    var ip = properties(image), source = {}; source.uri = item.url; ip.source = source; ip.resizeMode = "contain";
    return React.createElement(RN.Pressable, bp, imageElement(ip, scope || 1, context.trace));
  }
  // Diagnostic-only adapter. Bounded owned-instance observers read the exact
  // donor's VirtualizedList state and real metric queries. Calculation results,
  // input props, metrics and render masks retain their original values.
  function LibraryColumnsTrace(p) {
    var native = p.data, trace = p.context, ref = React.useRef(null), timer = React.useRef(null);
    var calculation = React.useRef(null);
    var previous = React.useRef(null), samples = React.useRef(0), offset = React.useRef(0);
    var latest = React.useRef(native); latest.current = native;
    function mark(stage) { trace.type = stage; observe(22, 0, null, stage, trace.index); }
    // Only the first two owned list instances, for <=5 seconds, <=128 calls
    // and <=16 distinct calculation snapshots each. No prototype/global hook.
    function bindCalculation(value) {
      if (calculation.current) { calculation.current(); calculation.current = null; }
      ref.current = value;
      if (!value) return;
      var list = value._listRef;
      if (calculationSequence >= 2) { observe(29, 0, null, 3); return; }
      if (!list || typeof list._adjustCellsAroundViewport !== "function") { observe(29, 0, null, 3); return; }
      var slot = ++calculationSequence, original = list._adjustCellsAroundViewport;
      var owned = Object.prototype.hasOwnProperty.call(list, "_adjustCellsAroundViewport");
      var calls = 0, records = 0, last = null, running = false, stopped = false, deadline;
      function stop(reason) {
        if (stopped) return; stopped = true; clearTimeout(deadline);
        if (list._adjustCellsAroundViewport === wrapped) {
          if (owned) list._adjustCellsAroundViewport = original; else delete list._adjustCellsAroundViewport;
        }
        observe(28, 0, null, calls, records); observe(29, 0, null, 2);
        if (reason) observe(29, 0, null, reason);
      }
      function number(value) { return typeof value === "number" && Number.isFinite(value) && Math.abs(value) < 10000000 ? value : -1; }
      var preparation = 0;
      function begin(step) { preparation = step; observe(30, 0, null, step, 0); }
      function pass(step) { observe(30, 0, null, step, 1); }
      function fail(step) { observe(30, 0, null, step, 2); }
      function wrapped(props, previousRange, pending) {
        if (stopped || running) return original.apply(this, arguments);
        if (calls >= 128 || records >= 16) { stop(calls >= 128 ? 4 : 6); return original.apply(this, arguments); }
        calls++; running = true;
        var metric, get, metricOwned, metricWrapped, values = null;
        var frames = [], frameCalls = 0, invalid = 0, mismatches = 0, frameFailures = 0;
        try {
          begin(1); metric = this._listMetrics;
          var metrics = this._scrollMetrics, count = props.getItemCount(props.data);
          pass(1); begin(2);
          var content = metric.getContentLength(), zoom = metrics.zoomScale, velocity = metrics.velocity;
          pass(2); begin(3);
          var zoomCode = typeof zoom !== "number" ? 4 : !Number.isFinite(zoom) ? 5 : zoom === 0 ? 0 : zoom === 1 ? 1 : zoom < 0 ? 3 : 2;
          var branch = metrics.visibleLength <= 0 || content <= 0 ? 2 : props.disableVirtualization ? 4 : pending > 0 ? 3 : 1;
          pass(3);
          // Independent optional observations: neither failure masks the other
          // or aborts the calculation snapshot. Unknown numeric fields are -1.
          var previousFirst = -1, previousLast = -1, previousOutcome = 2;
          try {
            if (previousRange == null) previousOutcome = 1;
            else if (typeof previousRange === "object") {
              var rangeStart = previousRange.first, rangeEnd = previousRange.last;
              if (typeof rangeStart === "number" && typeof rangeEnd === "number" && Number.isFinite(rangeStart) && Number.isFinite(rangeEnd) &&
                  rangeStart >= 0 && rangeStart < 10000000 && Math.floor(rangeStart) === rangeStart && Math.floor(rangeEnd) === rangeEnd &&
                  rangeEnd < 10000000 && (rangeEnd >= rangeStart || (rangeStart === 0 && rangeEnd === -1))) {
                previousFirst = rangeStart; previousLast = rangeEnd; previousOutcome = 3;
              }
            }
          } catch (error) { previousOutcome = 2; }
          observe(31, 0, null, previousOutcome);
          var nestedValue = -1, nestedOutcome = 4;
          try {
            var nestedHelper = this._isNestedWithSameOrientation;
            if (typeof nestedHelper === "function") {
              nestedValue = nestedHelper.call(this) ? 1 : 0; nestedOutcome = 6;
            }
          } catch (error) { nestedOutcome = 5; }
          observe(31, 0, null, nestedOutcome);
          begin(4);
          values = [previousFirst, previousLast, 0, 0,
            number(metrics.visibleLength), number(content), zoomCode, number(zoom),
            metrics.offset === 0 ? 0 : metrics.offset > 0 ? 1 : metrics.offset < 0 ? -1 : 2,
            typeof velocity !== "number" || !Number.isFinite(velocity) ? 2 : velocity > 1 ? 1 : velocity < -1 ? -1 : 0,
            number(pending), number(count), number(props.initialNumToRender), number(props.maxToRenderPerBatch), number(props.windowSize), branch,
            0, 0, 0, nestedValue, typeof props.getItemLayout === "function" ? 1 : 0];
          observe(31, 0, null, 7); pass(4); begin(5); get = metric.getCellMetricsApprox;
          if (typeof get !== "function") throw new Error();
          metricOwned = Object.prototype.hasOwnProperty.call(metric, "getCellMetricsApprox");
          pass(5); begin(6);
          metricWrapped = function (index, actualProps) {
            var frame = get.apply(this, arguments); // Exactly one real query.
            if (frameCalls++ < 64) try {
              var expected = typeof actualProps.getItemLayout === "function" ? actualProps.getItemLayout(actualProps.data, index) : null;
              var length = number(frame.length), offset = number(frame.offset);
              if (length <= 0 || offset < 0) invalid++;
              if (expected && (Math.abs(frame.length - expected.length) > 0.5 || Math.abs(frame.offset - expected.offset) > 0.5)) mismatches++;
              if (frames.length < 4 && !frames.some(function (sample) { return sample[0] === index; }))
                frames.push([number(index), length, offset, expected ? number(expected.length) : -1, expected ? number(expected.offset) : -1]);
            } catch (error) { invalid++; frameFailures++; }
            return frame;
          };
          metric.getCellMetricsApprox = metricWrapped;
          if (metric.getCellMetricsApprox !== metricWrapped) throw new Error();
          pass(6);
        } catch (error) { fail(preparation); values = null; observe(29, 0, null, 3); }
        var result;
        try { result = original.apply(this, arguments); }
        catch (error) { observe(29, 0, null, 7); throw error; }
        finally {
          if (metricWrapped) try {
            begin(8);
            if (metric.getCellMetricsApprox === metricWrapped) {
              if (metricOwned) metric.getCellMetricsApprox = get; else delete metric.getCellMetricsApprox;
            }
            pass(8);
          } catch (error) { fail(8); observe(29, 0, null, 3); }
          running = false;
        }
        if (frameCalls) { begin(7); if (frameFailures) fail(7); else pass(7); }
        if (values) try {
          begin(9);
          values[2] = number(result.first); values[3] = number(result.last);
          pass(9); begin(10);
          values[16] = frameCalls; values[17] = invalid; values[18] = mismatches;
          for (var i = 0; i < 4; i++) {
            if (frames[i]) values = values.concat(frames[i]);
            else for (var j = 0; j < 5; j++) values.push(-1);
          }
          if (values.length !== 41) throw new Error();
          pass(10); begin(11);
          var signature = JSON.stringify(values);
          pass(11);
          if (signature !== last) {
            begin(12); mark(trace.type);
            var accepted = bridge.observe(27, 0, signature, slot, 0);
            if (accepted !== 1 && accepted !== true) throw new Error();
            last = signature; records++; observe(31, 0, null, 8); pass(12);
          }
        } catch (error) { fail(preparation); observe(29, 0, null, 3); }
        if (calls >= 128 || records >= 16) stop(calls >= 128 ? 4 : 6);
        return result;
      }
      list._adjustCellsAroundViewport = wrapped; observe(29, 0, null, 1);
      deadline = setTimeout(function () { stop(5); }, 5000);
      calculation.current = function () { stop(0); };
    }
    var binding = React.useRef(bindCalculation);
    function sample(stabilizing) {
      mark(trace.type);
      try {
        var list = ref.current && ref.current._listRef;
        var state = list && list.state, metrics = list && list._scrollMetrics;
        var range = state && state.cellsAroundViewport, mask = state && state.renderMask;
        if (!range || !metrics || !mask || !mask.enumerateRegions) { observe(25, 0); return false; }
        var regions = mask.enumerateRegions(), count = 0;
        if (!Array.isArray(regions) || regions.length > 16) { observe(25, 0); return false; }
        for (var i = 0; i < regions.length; i++) if (!regions[i].isSpacer) count += regions[i].last - regions[i].first + 1;
        var content = list._listMetrics && list._listMetrics.getContentLength();
        observe(16, 0, null, range.first, range.last);
        observe(17, 0, null, count, latest.current.data.length);
        observe(18, 0, null, metrics.visibleLength, content);
        observe(19, 0, null, typeof metrics.zoomScale === "number" ? metrics.zoomScale : -1, state.pendingScrollUpdateCount);
        observe(20, 0, null, list._isNestedWithSameOrientation() ? 1 : 0, list.props.disableVirtualization ? 1 : 0);
        observe(21, 0, null, list.props.initialNumToRender, list.props.windowSize);
        observe(24, 0, null, list.props.maxToRenderPerBatch, metrics.offset === 0 ? 0 : 1);
        var signature = range.first + "/" + range.last + "/" + count + "/" + metrics.visibleLength + "/" + content + "/" + metrics.zoomScale + "/" + state.pendingScrollUpdateCount;
        var stable = metrics.visibleLength > 0 && content > 0 && previous.current === signature;
        if (stabilizing) previous.current = signature; return stable;
      } catch (error) { observe(25, 0); return false; }
    }
    function settle() {
      timer.current = null;
      if (sample(true)) { mark(1); return; }
      if (++samples.current < 20) timer.current = setTimeout(settle, 250);
      else observe(26, 0);
    }
    React.useEffect(function () {
      if (trace.value !== undefined && trace.value !== native.key) mark(5);
      trace.value = native.key;
      mark(trace.type); timer.current = setTimeout(settle, 250);
      return function () {
        if (timer.current !== null) clearTimeout(timer.current); timer.current = null;
        if (calculation.current) { calculation.current(); calculation.current = null; }
      };
    }, []);
    var copy = Object.assign({}, native);
    copy.ref = binding.current;
    copy.onLayout = function (event) { if (native.onLayout) native.onLayout(event); sample(); };
    copy.onContentSizeChange = function (w, h) { if (native.onContentSizeChange) native.onContentSizeChange(w, h); sample(); };
    copy.onViewableItemsChanged = React.useRef(function (event) {
      if (latest.current.onViewableItemsChanged) latest.current.onViewableItemsChanged(event); sample();
    }).current;
    copy.onScroll = function (event) {
      var next = event.nativeEvent.contentOffset.x;
      if (next !== offset.current) mark(next < offset.current ? 3 : 2);
      offset.current = next; sample();
      if (native.onScroll) native.onScroll(event);
      if (timer.current !== null) clearTimeout(timer.current);
      samples.current = 0; previous.current = null; timer.current = setTimeout(settle, 250);
    };
    return React.createElement(RN.FlatList, copy);
  }
  function title(text, context, height) {
    var style = {}; style.height = height; style.paddingHorizontal = 12; style.fontSize = 14;
    style.fontWeight = "600"; style.color = context.theme.colors.textAlt;
    return React.createElement(RN.Text, properties(style), text);
  }
  function controls(context, first, last, selected, set) {
    var children = [], row = {}; row.flexDirection = "row"; row.height = 30; row.marginHorizontal = 12;
    row.borderRadius = 15; row.backgroundColor = context.theme.colors.backgroundAlt;
    for (var i = first; i < last; i++) {
      var style = {}; style.flex = 1; style.borderRadius = 15; style.alignItems = "center"; style.justifyContent = "center";
      // Contrast stays explicit in both themes; backgroundAlt2 was identical
      // to the track on the shipped dark theme.
      if (i - first === selected) style.backgroundColor = context.theme.colors.textBase;
      var bp = properties(style); bp.key = i; bp.accessibilityRole = "tab"; bp.accessibilityLabel = context.data.labels[i];
      var selectedState = {}; selectedState.selected = i - first === selected; bp.accessibilityState = selectedState;
      bp.onPress = (function (index) { return function () { set(index); }; })(i - first);
      var text = {}; text.fontSize = 13; text.color = i - first === selected ? context.theme.colors.backgroundBase : context.theme.colors.textBase;
      children.push(React.createElement(RN.Pressable, bp, React.createElement(RN.Text, properties(text), context.data.labels[i])));
    }
    return React.createElement(RN.View, properties(row), children);
  }
  function GridAdapter(p) {
    var context = React.useContext(LibraryContext);
    if (!context) return React.createElement(p.type, p.data);
    var cp = {}; cp.data = p.data; cp.context = context;
    return React.createElement(LibraryGrid, cp);
  }
  function LibraryGrid(p) {
    var native = p.data, context = p.context;
    var size = React.useState(360), width = size[0], setWidth = size[1];
    var current = React.useRef(null), ref = React.useRef(null);
    var viewable = React.useRef(function (event) { observe(11, 0, null, (event.viewableItems || []).length, 0); });
    var columns = Math.max(3, Math.min(12, Math.floor(width / 60)));
    var items = context.data.sections[context.scope].filter(function (item) { return !context.provider || item.provider === context.provider - 1; });
    // One bounded outer row; virtualize horizontal columns of five inside it.
    // Native sections retain their ordinary 52-point rows and vertical list.
    var row = {}; row.key = "provider"; row.emotes = items;
    var section = {}; section.key = "provider"; section.title = context.data.title; section.data = [row];
    var sections = native.sections.filter(function (s) { return s.key !== "provider"; });
    var position = sections.length && sections[0].key === "recents" ? 1 : 0;
    sections = sections.slice(0, position).concat([section], sections.slice(position));
    var headerHeight = context.recents.length ? 84 : 0;
    current.current = {}; current.current.native = native; current.current.position = position; current.current.context = context;
    var onView = React.useRef(function (event) {
      var latest = current.current, tokens = event.viewableItems || [];
      var first = tokens.find(function (token) { return token.isViewable && token.section; });
      latest.context.setActive(!!first && first.section.key === "provider");
      if (latest.native.onViewableItemsChanged) latest.native.onViewableItemsChanged(event);
    });
    var bind = React.useRef(function (list) {
      ref.current = list; current.current.context.list.current = list;
      var originalRef = current.current.native.ref;
      var proxy = null;
      if (list) {
        proxy = {}; proxy.scrollToLocation = function (location) {
          var copy = Object.assign({}, location);
          if (copy.sectionIndex >= current.current.position) copy.sectionIndex++;
          return ref.current && ref.current.scrollToLocation(copy);
        };
        proxy.scrollToOffset = function (location) { if (ref.current) return ref.current.getScrollResponder().scrollTo(location); };
        proxy.getScrollResponder = function () { return ref.current && ref.current.getScrollResponder(); };
      }
      if (typeof originalRef === "function") originalRef(proxy); else if (originalRef) originalRef.current = proxy;
    });
    context.list.index = position;
    React.useEffect(function () {
      if (ref.current && context.active) {
        var location = {}; location.sectionIndex = position; location.itemIndex = 0; location.animated = false;
        ref.current.scrollToLocation(location);
      }
    }, [context.provider, context.scope]);
    var copy = Object.assign({}, native); copy.sections = sections; copy.ref = bind.current;
    copy.onViewableItemsChanged = onView.current;
    copy.onLayout = function (event) { var w = event.nativeEvent.layout.width;
      observe(8, 0, null, w, event.nativeEvent.layout.height);
      if (w > 0) setWidth(w); if (native.onLayout) native.onLayout(event); };
    copy.getItemLayout = function (data, index) {
      var cursor = 0, offset = headerHeight;
      for (var s = 0; s < sections.length; s++) {
        var n = sections[s].data.length, h = sections[s].key === "provider" ? 88 : 28;
        var rowHeight = sections[s].key === "provider" ? 260 : 52;
        var length = 0;
        if (index === cursor) length = h;
        else if (index > cursor && index <= cursor + n) { offset += h + (index - cursor - 1) * rowHeight; length = rowHeight; }
        else if (index === cursor + n + 1) offset += h + n * rowHeight;
        else { cursor += n + 2; offset += h + n * rowHeight; continue; }
        var layout = {}; layout.index = index; layout.offset = offset; layout.length = length; return layout;
      }
      var layout = {}; layout.index = index; layout.offset = offset; layout.length = 0; return layout;
    };
    copy.renderItem = function (info) {
      if (info.section.key !== "provider") return native.renderItem(info);
      var groups = [], cellWidth = width / columns;
      for (var i = 0; i < info.item.emotes.length; i += 5) {
        var column = {}; column.key = context.data.title + "/" + i; column.emotes = info.item.emotes.slice(i, i + 5); groups.push(column);
      }
      var style = {}; style.height = 260; style.flexGrow = 0;
      if (!groups.length) return React.createElement(RN.View, properties(style), title(context.data.message, context, 52));
      var fp = properties(style); fp.key = context.provider + "/" + context.scope; fp.horizontal = true; fp.data = groups;
      fp.showsHorizontalScrollIndicator = false; fp.keyboardShouldPersistTaps = "always";
      fp.initialNumToRender = columns + 1; fp.maxToRenderPerBatch = columns + 1; fp.windowSize = 3;
      if (bridge.observe) {
        fp.onLayout = function (event) { observe(9, 0, null, event.nativeEvent.layout.width, event.nativeEvent.layout.height); };
        fp.onContentSizeChange = function (w, h) { observe(10, 0, null, w, h); };
        // Stable callback, no viewability config change or React state update.
        fp.onViewableItemsChanged = viewable.current;
      }
      fp.keyExtractor = function (item) { return item.key; };
      fp.getItemLayout = function (data, index) { var layout = {}; layout.length = cellWidth; layout.offset = cellWidth * index; layout.index = index; return layout; };
      fp.renderItem = function (info) {
        var style = {}; style.width = cellWidth; style.height = 260;
        return React.createElement(RN.View, properties(style), info.item.emotes.map(function (item) { return tile(item, context, cellWidth); }));
      };
      if (bridge.observe) { var probe = {}; probe.data = fp; probe.context = context.trace; probe.key = fp.key; return React.createElement(LibraryColumnsTrace, probe); }
      return React.createElement(RN.FlatList, fp);
    };
    copy.renderSectionHeader = function (info) {
      if (info.section.key !== "provider") return native.renderSectionHeader(info);
      var style = {}; style.height = 88; style.backgroundColor = context.theme.colors.backgroundBase;
      return React.createElement(RN.View, properties(style), title(context.data.title, context, 28),
        controls(context, 0, 4, context.provider, context.onValueChange), controls(context, 4, 6, context.scope, context.onChange));
    };
    if (headerHeight) {
      var style = {}; style.height = 84;
      var scroll = {}; scroll.horizontal = true; scroll.showsHorizontalScrollIndicator = false; scroll.keyboardShouldPersistTaps = "always";
      var recent = context.recents.map(function (item) { return tile(item, context, Math.min(112, Math.max(52, 40 * item.aspect + 8)), 2); });
      copy.ListHeaderComponent = React.createElement(RN.View, properties(style), title(context.data.label, context, 28), React.createElement(RN.ScrollView, scroll, recent));
    }
    return React.createElement(RN.SectionList, copy);
  }
  function NavAdapter(p) {
    var context = React.useContext(LibraryContext);
    if (!context) return React.createElement(p.type, p.data);
    var native = p.data, children = React.Children.toArray(native.children).map(function (child) {
      var copy = {}; if (context.active) copy.active = false;
      copy.onPress = function () { context.setActive(false); if (child.props.onPress) child.props.onPress.apply(null, arguments); };
      return React.cloneElement(child, copy);
    });
    var style = {}; style.width = 48; style.height = 48; style.alignItems = "center"; style.justifyContent = "center";
    style.borderTopWidth = 2; style.borderTopColor = context.active ? context.theme.colors.textLink : "transparent";
    var bp = properties(style); bp.key = "provider"; bp.accessibilityRole = "tab"; bp.accessibilityLabel = context.data.title;
    var selected = {}; selected.selected = context.active; bp.accessibilityState = selected;
    bp.onPress = function () {
      if (context.list.current) { var location = {}; location.sectionIndex = context.list.index; location.itemIndex = 0;
        location.viewOffset = 0; location.animated = true; context.list.current.scrollToLocation(location); context.setActive(true); }
    };
    var text = {}; text.fontSize = 30; text.color = context.active ? context.theme.colors.textLink : context.theme.colors.textBase;
    var button = React.createElement(RN.Pressable, bp, React.createElement(RN.Text, properties(text), context.data.icon));
    var position = children.length && children[0].props.category && children[0].props.category.key === "recents" ? 1 : 0;
    children.splice(position, 0, button);
    var copy = Object.assign({}, native); copy.children = children;
    return React.createElement(RN.ScrollView, copy);
  }
  function route(runtime, type, p, key) {
    if (bridge.observe && p && typeof p.src === "string" && typeof p.testID === "string" && p.testID.indexOf("chat-emote-") === 0) {
      var image = {}; image.type = type; image.data = p; image.index = 5; image.key = key;
      return React.createElement(DemandImage, image);
    }
    if (p && ((type === RN.SectionList && p.testID === "emote-grid-list") || (type === RN.ScrollView && p.testID === "emote-nav-tablist"))) {
      var cp = {}; cp.data = p; cp.type = type; cp.key = key;
      return React.createElement(type === RN.SectionList ? GridAdapter : NavAdapter, cp);
    }
    return runtime(type, p, key);
  }
  function jsx(type, p, key) { return route(nativeJSX, type, p, key); }
  function jsxs(type, p, key) { return route(nativeJSXS, type, p, key); }
  // Assign only verified, writable leaf exports. Public barrels use live
  // getters. Roll back every adapter if any export cannot be installed.
  try {
    inputs.EmoteTextInput = Input; autocomplete.useAutocomplete = useAutocomplete;
    suggestions.ChatAutocompleteTray = StockSuggestions;
    if (nativeComposer && smartBackspace && aliases && bridge.lookup) composerHooks.useChatComposer = useChatComposer;
    if (NativeLibrary && nativeJSX && nativeJSXS && RN.SectionList && RN.FlatList && bridge.getSnapshot && bridge.remember && React.Children && React.cloneElement) {
      trays.EmotePickerTray = Library; jsxRuntime.jsx = jsx; jsxRuntime.jsxs = jsxs;
    }
  } catch (error) {
    inputs.EmoteTextInput = NativeInput; autocomplete.useAutocomplete = nativeAutocomplete;
    suggestions.ChatAutocompleteTray = NativeSuggestions;
    composerHooks.useChatComposer = nativeComposer;
    trays.EmotePickerTray = NativeLibrary; jsxRuntime.jsx = nativeJSX; jsxRuntime.jsxs = nativeJSXS;
    return original;
  }
  return Composer;
}
