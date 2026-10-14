/* Diagnostic-only exact-donor observer; no contents, raw IDs, styles or sends.
 * Session slots: id,store,IDs,nonces,store-seen,count,samples,measurements,
 * unsubscribe,objects,data-seen,render-seen. Components add no native views. */
function install(original) {
  var React = __r(72); React = React.default || React;
  var bridge = __r(16).default.buildLocalEcho, lines = __r(4782), jsx = __r(245), client = __r(3500).LibraryTmiClient;
  if (!bridge || typeof bridge.trace !== "function" || !React.createContext || !lines.ChatLine || !jsx.jsx || !client) return original;
  var Context = React.createContext(null), sessions = [], stores = new WeakMap(), clients = new WeakMap();
  var active = true, packets = 0, timer = null, restore = [];
  function safe(fn) { try { return fn(); } catch (error) { return null; } }
  function number(value) { return typeof value === "number" && Number.isFinite(value) && Math.abs(value) <= 10000000 ? value : -1; }
  function emit(event, s, id, f, a, b, c, d) {
    if (!active || !s) return;
    if (packets >= 1500 && event !== 11) { stop(2); return; }
    packets++;
    safe(function () { bridge.trace(JSON.stringify([event,s[0],id||0,f||0,number(a),number(b),number(c),number(d)])); });
  }
  function stop(reason) {
    if (!active) return;
    sessions.forEach(function (s) { emit(11,s,0,0,reason,0,0,0); }); active = false;
    if (timer !== null) clearTimeout(timer);
    restore.forEach(function (fn) { safe(fn); }); restore = [];
    sessions.forEach(function (s) { if (typeof s[8] === "function") safe(s[8]); s[2].clear(); s[3].clear(); s[9] = new WeakMap(); });
  }
  function flags(line) {
    var value = 0, emotes = line && line.emotes;
    if (line && line.isUnpublished) value |= 1;
    if (Array.isArray(emotes)) emotes.slice(0,128).forEach(function (e) {
      var id = Number(e.id); value |= (id >= 860000000000000 && id < 861000000000000) || (id >= 900000000000000 && id < 1000000000000000) ? 2 : 4;
    });
    return value;
  }
  function label(s,line,create) {
    if (!active || !s || !line || typeof line !== "object") return 0;
    var id = typeof line.id === "string" ? line.id : null, nonce = typeof line.clientNonce === "string" ? line.clientNonce : null;
    var value = (id && s[2].get(id)) || (nonce && s[3].get(nonce)) || s[9].get(line);
    if (!value && create && s[5] < 256) value = ++s[5];
    if (value) { if (id && s[2].size < 512) s[2].set(id,value); if (nonce && s[3].size < 512) s[3].set(nonce,value); s[9].set(line,value); }
    return value || 0;
  }
  function snapshot(s) {
    if (!active || !s || s[6]++ >= 256) return;
    safe(function () {
      var state = s[1].getState(), list = state.lines, f = (state.paused?8:0)|(state.chatHidden?16:0)|(state.suspended?32:0);
      if (state._tmiClient) clients.set(state._tmiClient,s);
      emit(10,s,0,f,Array.isArray(list)?list.length:-1,state.connected?1:0,s[6],0);
      if (Array.isArray(list)) list.slice(0,2000).forEach(function (entry) {
        var line = entry.line || entry, id = label(s,line,false);
        if (id && !s[4].has(id)) { s[4].add(id); emit(4,s,id,flags(line)|f,1,0,0,0); }
      });
    });
  }
  function session(store) {
    if (!active || !store || typeof store.getState !== "function") return null;
    var s = stores.get(store); if (s) return s;
    if (sessions.length >= 2) return null;
    s = []; s[0]=sessions.length+1; s[1]=store; s[2]=new Map(); s[3]=new Map(); s[4]=new Set(); s[5]=0; s[6]=0; s[7]=0; s[9]=new WeakMap(); s[10]=new Set(); s[11]=new Set();
    stores.set(store,s); sessions.push(s); emit(0,s,0,0,1,0,0,0); snapshot(s);
    if (typeof store.subscribe === "function") s[8]=safe(function () { return store.subscribe(function () { snapshot(s); }); });
    emit(12,s,0,0,typeof s[8]==="function"?1:0,restore.length,0,0);
    if (timer === null) timer=setTimeout(function () { stop(1); },120000);
    return s;
  }
  function errorCode(error) { return safe(function () { return error && error.name==="TypeError"?1:error && error.name==="RangeError"?2:3; }) || 3; }
  function method(name,wrap) {
    safe(function () {
      var target=client.prototype, descriptor=Object.getOwnPropertyDescriptor(target,name);
      if (!descriptor || typeof descriptor.value!=="function" || !descriptor.writable) return;
      var replacement=wrap(descriptor.value), copy=Object.assign({},descriptor); copy.value=replacement;
      Object.defineProperty(target,name,copy);
      restore.push(function () { if (target[name]===replacement) Object.defineProperty(target,name,descriptor); });
    });
  }
  method("translateChatMessage",function (native) { return function () {
    var result=native.apply(this,arguments), s=clients.get(this), event=arguments[0];
    safe(function () { emit(1,s,label(s,result,true),flags(result)|(event && event.sentByCurrentUser?1:0),result?1:0,0,0,0); });
    return result;
  }; });
  method("emitLine",function (native) { return function () {
    var s=clients.get(this), line=arguments[0], id=safe(function () { return label(s,line,true); }) || 0;
    safe(function () { emit(2,s,id,flags(line),1,0,0,0); });
    try { var value=native.apply(this,arguments); safe(function () { emit(3,s,id,flags(line),1,0,0,0); snapshot(s); }); return value; }
    catch (error) { safe(function () { emit(3,s,id,0,0,errorCode(error),0,0); }); throw error; }
  }; });
  var NativeLine=lines.ChatLine;
  lines.ChatLine=function (p) {
    var c=safe(function () { var s=session(p.chatStore), id=label(s,p.line,true); snapshot(s); return [s,id,flags(p.line)]; }), props={}; props.value=c;
    return React.createElement(Context.Provider,props,React.createElement(NativeLine,p));
  };
  function forward(ref,node) { if (typeof ref==="function") return ref(node); if (ref) ref.current=node; }
  function Row(p) {
    var c=React.useContext(Context), view=React.useRef(null), generation=React.useRef(0), current=React.useRef(null); current.current=[p.data,c];
    var callbacks=React.useMemo(function () {
      var value={}, originalRef=p.data.ref;
      value.ref=function (node) { view.current=node; generation.current++; var cleanup=forward(originalRef,node);
        if (typeof cleanup==="function") return function () { view.current=null; generation.current++; return cleanup.apply(this,arguments); };
        return cleanup;
      };
      value.onLayout=function (event) {
        var data=current.current[0], c=current.current[1];
        try { if (data.onLayout) return data.onLayout.apply(this,arguments); }
        finally { safe(function () {
          if (!active || !c || !c[0]) return;
          var rect=event && event.nativeEvent && event.nativeEvent.layout;
          if (rect) emit(6,c[0],c[1],c[2],rect.height,rect.width,rect.x,rect.y);
          var node=view.current, token=generation.current;
          if (node && typeof node.measureInWindow==="function" && c[0][7]++<64) node.measureInWindow(function (x,y,w,h) {
            if (active && token===generation.current && view.current===node && current.current[1]===c) emit(7,c[0],c[1],c[2],x,y,w,h);
          });
        }); }
      };
      return value;
    },[p.data.ref]);
    var copy=Object.assign({},p.data); copy.ref=callbacks.ref; copy.onLayout=callbacks.onLayout;
    return React.createElement(p.type,copy);
  }
  function List(p) {
    var c=React.useContext(Context), current=React.useRef(null), view=React.useRef(null), generation=React.useRef(0); current.current=[p.data,c];
    var callbacks=React.useMemo(function () {
      var value={}, originalRef=p.data.ref;
      value.renderItem=function () {
        var data=current.current[0], s=current.current[1] && current.current[1][0], item=arguments[0];
        safe(function () { var line=item && item.item && (item.item.line || item.item), id=label(s,line,true);
          if (id && !s[11].has(id)) { s[11].add(id); emit(5,s,id,flags(line),2,0,0,0); snapshot(s); }
        });
        return data.renderItem.apply(this,arguments);
      };
      value.ref=function (node) {
        view.current=node; generation.current++;
        var result=forward(originalRef,node), token=generation.current, s=current.current[1] && current.current[1][0];
        safe(function () { var nativeView=node && typeof node.getNativeScrollRef==="function" && node.getNativeScrollRef();
          if (active && s && nativeView && typeof nativeView.measureInWindow==="function" && s[7]++<64) nativeView.measureInWindow(function (x,y,w,h) {
            if (active && token===generation.current && view.current===node && current.current[1] && current.current[1][0]===s) emit(8,s,0,0,x,y,w,h);
          });
        });
        if (typeof result==="function") return function () { view.current=null; generation.current++; return result.apply(this,arguments); };
        return result;
      };
      return value;
    },[p.data.ref,p.data.renderItem]);
    var s=c && c[0];
    if (active && s && Array.isArray(p.data.data)) safe(function () {
      p.data.data.slice(0,2000).forEach(function (entry) { var line=entry.line || entry, id=label(s,line,true);
        if (id && !s[10].has(id)) { s[10].add(id); emit(5,s,id,flags(line),1,0,0,0); }
      }); snapshot(s);
    });
    var copy=Object.assign({},p.data); copy.ref=callbacks.ref;
    if (typeof p.data.renderItem==="function") copy.renderItem=callbacks.renderItem;
    return React.createElement(p.type,copy);
  }
  function Boundary(p) {
    var c=React.useContext(Context), current=React.useRef(null); current.current=[p.data,c];
    var report=React.useMemo(function () { return function () {
      var data=current.current[0], s=current.current[1] && current.current[1][0], error=arguments[0];
      safe(function () { var line=data.children && data.children.props && data.children.props.line; emit(9,s,label(s,line,true),flags(line),errorCode(error),0,0,0); });
      return data.reportError.apply(this,arguments);
    }; },[]);
    var copy=Object.assign({},p.data); copy.reportError=report; return React.createElement(p.type,copy);
  }
  function intercept(native) { return function (type,p,key) {
    var component=p && p.testID==="chat-message-row"?Row:p && p.testID==="chat-message-list"?List:p && p.name==="ChatLine" && typeof p.reportError==="function"?Boundary:null;
    if (component) { var props={}; props.type=type; props.data=p; return native(component,props,key); }
    return native.apply(this,arguments);
  }; }
  jsx.jsx=intercept(jsx.jsx); if (jsx.jsxs) jsx.jsxs=intercept(jsx.jsxs);
  return function (p) { var s=safe(function () { return session(p.chatStore); }), props={}; props.value=[s,0,0]; return React.createElement(Context.Provider,props,React.createElement(original,p)); };
}
