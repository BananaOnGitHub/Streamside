/* Owned RN component for the exact Twitch 31.5 donor. install() is invoked
 * once in ChatCardHost's factory with its original emote sheet component.
 * No hooks in the routing wrapper; native/provider cards have separate trees.
 * Empty objects are populated incrementally so the compiled graft needs no
 * donor literal-buffer changes. UI labels come from the native snapshot.
 */
function install(original) {
  var React = __r(72);
  React = React.default || React;
  var RN = __r(5);
  var sheets = __r(2118);
  var bridge = __r(16).default.buildLocalEcho;
  if (!React || !RN.Image || !RN.Pressable || !sheets.BottomSheet ||
      !sheets.useSheetHandoff || !sheets.useTheme || !bridge ||
      !bridge.getMetadata || !bridge.sendAction) return original;

  function props(style) { var p = {}; p.style = style; return p; }
  function Provider(card) {
    var m = card.data;
    var theme = sheets.useTheme();
    var options = {}; options.initialVisible = true; options.onPlainClose = card.onClose;
    var handoff = sheets.useSheetHandoff(options);
    var pending = React.useRef(-1);
    function close() { handoff.onClose(); }
    function closed() {
      handoff.onClosed();
      var action = pending.current;
      pending.current = -1;
      if (action >= 0) bridge.sendAction(m.id, action);
    }
    function action(value) { pending.current = value; close(); }
    var surface = {}; surface.padding = 24; surface.backgroundColor = theme.colors.backgroundBase;
    var title = {}; title.fontSize = 22; title.fontWeight = "600"; title.color = theme.colors.textBase;
    var sub = {}; sub.fontSize = 14; sub.color = theme.colors.textAlt; sub.marginTop = 8;
    var image = {}; image.height = 112; image.width = Math.min(280, 112 * Math.max(0.1, m.aspect));
    image.alignSelf = "center"; image.marginBottom = 20;
    var ip = props(image); var source = {}; source.uri = m.url; ip.source = source;
    ip.resizeMode = "contain"; ip.accessibilityLabel = m.name;
    var row = {}; row.paddingVertical = 14; row.marginTop = 8;
    var label = {}; label.fontSize = 16; label.color = theme.colors.textBase;
    function button(text, callback) {
      var p = props(row); p.onPress = callback; p.accessibilityRole = "button";
      p.accessibilityLabel = text;
      return React.createElement(RN.Pressable, p, React.createElement(RN.Text, props(label), text));
    }
    var content = React.createElement(RN.View, props(surface),
      React.createElement(RN.Image, ip),
      React.createElement(RN.Text, props(title), m.name),
      React.createElement(RN.Text, props(sub), m.subtitle),
      button(m.title, function () { action(0); }),
      button(m.label, function () { action(1); }),
      button(m.openURL, function () { action(2); }),
      button(m.closeLabel, close));
    var sheet = {}; sheet.visible = handoff.visible; sheet.onClose = close;
    sheet.onClosed = closed; sheet.accessibilityLabel = m.name;
    sheet.initialDetent = false; sheet.disableBodyInlinePadding = true;
    return React.createElement(sheets.BottomSheet, sheet, content);
  }
  function Wrapper(p) {
    var m = null;
    try { m = bridge.getMetadata(p.emoteID); } catch (error) { m = null; }
    if (!m) return React.createElement(original, p);
    var c = {}; c.data = m; c.onClose = p.onClose; c.key = p.emoteID;
    return React.createElement(Provider, c);
  }
  return Wrapper;
}
