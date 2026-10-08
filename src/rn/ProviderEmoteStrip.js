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
  /* The donor's library leaf uses JSX runtime 245 for exactly two verified
   * surfaces. Route those elements through context; other JSX calls retain
   * their original type, props, key and runtime. No hooks enter donor bodies. */
  var trays = __r(4174), NativeLibrary = trays.EmotePickerTray;
  var jsxRuntime = __r(245), nativeJSX = jsxRuntime.jsx, nativeJSXS = jsxRuntime.jsxs;
  var LibraryContext = React.createContext(null);
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
    value.provider = provider; value.scope = scope;
    value.onValueChange = function (next) { setProvider(next); setScope(0); }; value.onChange = setScope;
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
    var content = React.createElement(RN.View, properties(surface), React.createElement(RN.Image, ip),
      React.createElement(RN.Text, properties(title), m.name), React.createElement(RN.Text, properties(sub), m.subtitle),
      button(m.title, 0), button(m.label, 1), button(m.openURL, 2), button(m.closeLabel, -1));
    var sp = {}; sp.visible = handoff.visible; sp.onClose = handoff.onClose;
    sp.onClosed = function () { handoff.onClosed(); var action = pending.current; pending.current = -1; if (action >= 0) bridge.sendAction(m.id, action); };
    sp.initialDetent = false; sp.disableBodyInlinePadding = true; sp.accessibilityLabel = m.name;
    return React.createElement(ui.BottomSheet, sp, content);
  }
  function tile(item, context, width) {
    var style = {}; style.width = width; style.height = 52; style.alignItems = "center"; style.justifyContent = "center";
    var bp = properties(style); bp.key = item.id; bp.accessibilityRole = "button"; bp.accessibilityLabel = item.name;
    bp.onPress = function () { context.onSelectEmote(item); }; bp.onLongPress = function () { context.info(item); };
    var image = {}; image.height = Math.min(40, (width - 8) / Math.max(0.1, item.aspect));
    image.width = Math.min(width - 8, 40 * Math.max(0.1, item.aspect));
    var ip = properties(image), source = {}; source.uri = item.url; ip.source = source; ip.resizeMode = "contain";
    return React.createElement(RN.Pressable, bp, React.createElement(RN.Image, ip));
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
      if (i - first === selected) style.backgroundColor = context.theme.colors.backgroundAlt2;
      var bp = properties(style); bp.key = i; bp.accessibilityRole = "tab"; bp.accessibilityLabel = context.data.labels[i];
      var selectedState = {}; selectedState.selected = i - first === selected; bp.accessibilityState = selectedState;
      bp.onPress = (function (index) { return function () { set(index); }; })(i - first);
      var text = {}; text.fontSize = 13; text.color = context.theme.colors.textBase;
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
    var columns = Math.max(3, Math.min(12, Math.floor(width / 60)));
    var items = context.data.sections[context.scope].filter(function (item) { return !context.provider || item.provider === context.provider - 1; });
    var rows = [];
    for (var i = 0; i < items.length; i += columns) { var row = {}; row.key = context.data.title + "/" + i; row.emotes = items.slice(i, i + columns); rows.push(row); }
    if (!rows.length) { var row = {}; row.key = "provider"; row.emotes = []; rows.push(row); }
    var section = {}; section.key = "provider"; section.title = context.data.title; section.data = rows;
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
    copy.onLayout = function (event) { var w = event.nativeEvent.layout.width; if (w > 0) setWidth(w); if (native.onLayout) native.onLayout(event); };
    copy.getItemLayout = function (data, index) {
      var cursor = 0, offset = headerHeight;
      for (var s = 0; s < sections.length; s++) {
        var n = sections[s].data.length, h = sections[s].key === "provider" ? 88 : 28;
        var length = 0;
        if (index === cursor) length = h;
        else if (index > cursor && index <= cursor + n) { offset += h + (index - cursor - 1) * 52; length = 52; }
        else if (index === cursor + n + 1) offset += h + n * 52;
        else { cursor += n + 2; offset += h + n * 52; continue; }
        var layout = {}; layout.index = index; layout.offset = offset; layout.length = length; return layout;
      }
      var layout = {}; layout.index = index; layout.offset = offset; layout.length = 0; return layout;
    };
    copy.renderItem = function (info) {
      if (info.section.key !== "provider") return native.renderItem(info);
      var row = {}; row.height = 52; row.flexDirection = "row";
      var children = info.item.emotes.map(function (item) { return tile(item, context, width / columns); });
      if (!children.length) children = [title(context.data.message, context, 52)];
      return React.createElement(RN.View, properties(row), children);
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
      var recent = context.recents.map(function (item) { return tile(item, context, Math.min(112, Math.max(52, 40 * item.aspect + 8))); });
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
    if (NativeLibrary && nativeJSX && nativeJSXS && RN.SectionList && bridge.getSnapshot && bridge.remember && React.Children && React.cloneElement) {
      trays.EmotePickerTray = Library; jsxRuntime.jsx = jsx; jsxRuntime.jsxs = jsxs;
    }
  } catch (error) {
    inputs.EmoteTextInput = NativeInput; autocomplete.useAutocomplete = nativeAutocomplete;
    suggestions.ChatAutocompleteTray = NativeSuggestions;
    trays.EmotePickerTray = NativeLibrary; jsxRuntime.jsx = nativeJSX; jsxRuntime.jsxs = nativeJSXS;
    return original;
  }
  return Composer;
}
