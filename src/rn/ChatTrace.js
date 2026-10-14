/* Diagnostic-only rolling observer. No contents, raw IDs, styles or sends.
 * Slots: id,store,IDs,nonces,store-seen,label-sequence,last-snapshot,probes,
 * unsubscribe,objects,data-seen,render-seen,last-access,disposed,last-state,
 * mounts,cycle,last-measurement,client,viewport,scan-offset,probe-offset,frame,
 * own-labels,object-count,target-labels,store-hook. Bounded four-store LRU.
 * Wire: event,session,label,flags,a,b,c,d,cycle,frame (numbers only).
 */
function install(original) {
  var React=__r(72); React=React.default || React;
  var bridge=__r(16).default.buildLocalEcho, lines=__r(4782), jsx=__r(245), client=__r(3500).LibraryTmiClient;
  if (!bridge || typeof bridge.trace!=="function" || !React.createContext || !React.useEffect || !lines.ChatLine || !jsx.jsx || !client) return original;
  var Context=React.createContext(null),sessions=[],stores=new WeakMap(),clients=new WeakMap(),routes=new WeakMap(),sequence=0,hookRecords=[],rewardHook=null,rewardModule=safe(function(){return __r(4790);});
  var normal=32,geometry=24,metadata=8,priority=8,target=16,last=Date.now(),skipped=0,urgentSkipped=0,registrySkipped=0,aliases=0,sampleCursor=0,pending=0;
  function safe(fn) { try { return fn(); } catch (error) { return null; } }
  function number(value) { return typeof value==="number" && Number.isFinite(value) && Math.abs(value)<=10000000 ? value : -1; }
  function emit(event,s,id,f,a,b,c,d,frame) {
    if (!s || s[13]) return false;
    var time=Date.now(), elapsed=Math.max(0,time-last); last=time;
    normal=Math.min(32,normal+elapsed*0.032);geometry=Math.min(24,geometry+elapsed*0.016);metadata=Math.min(8,metadata+elapsed*0.004);priority=Math.min(8,priority+elapsed*0.008);target=Math.min(16,target+elapsed*0.012);
    var lifecycle=event===17 || event===18 || event===21;
    var urgent=event===0 || event===9 || event===11 || event===13 || ((f&1) && event<=3);
    var spatial=event===7 || event===8 || event===14 || event===19 || event===20;
    var status=event===12 || event===16 || event===22;
    if(lifecycle?target<1:urgent?priority<1:status?metadata<1:spatial?geometry<1:normal<1){if(urgent || lifecycle)urgentSkipped++;else skipped++;return false;}
    if(lifecycle)target--;else if(urgent)priority--;else if(status)metadata--;else if(spatial)geometry--;else normal--;
    var accepted=safe(function(){var value=bridge.trace(JSON.stringify([event,s[0],id||0,f||0,number(a),number(b),number(c),number(d),s[16],frame||0]));return value===1 || value===true;})===true;
    if(!accepted){if(urgent || lifecycle)urgentSkipped++;else skipped++;}return accepted;
  }
  function trim(map,key,value,limit) {
    if (map.has(key)) map.delete(key); map.set(key,value);
    if (map.size>limit) { map.delete(map.keys().next().value); aliases++; }
  }
  function flags(line) {
    var value=0, emotes=line && line.emotes;
    if (line && line.isUnpublished) value|=1;
    if (line && line.type==="channelpointsreward") value|=64;
    if (Array.isArray(emotes)) emotes.slice(0,128).forEach(function (e) {
      var id=Number(e.id); value|=(id>=860000000000000 && id<861000000000000) || (id>=900000000000000 && id<1000000000000000)?2:4;
    }); return value;
  }
  function label(s,line,create) {
    if (!s || s[13] || !line || typeof line!=="object") return 0;
    var id=typeof line.id==="string"?line.id:null, nonce=typeof line.clientNonce==="string"?line.clientNonce:null;
    var value=(id && s[2].get(id)) || (nonce && s[3].get(nonce)) || s[9].get(line);
    if (!value && create && s[5]<10000000) value=++s[5];
    if(value){
      if(id)trim(s[2],id,value,512);if(nonce)trim(s[3],nonce,value,512);
      if(!s[9].has(line)){if(s[24]>=256){s[9]=new WeakMap();s[24]=0;aliases++;}s[24]++;}
      s[9].set(line,value);
    }
    return value || 0;
  }
  function lineFlags(s,line,id) { return flags(line) | (s && s[23].get(id) || 0); }
  function watch(s,id,f){if(s && id && (f&1))trim(s[23],id,1,256);if(s && id && (f&65) && !s[25].has(id))trim(s[25],id,[f,0,0,-1],256);else if(s && s[25].has(id))s[25].get(id)[0]|=f;}
  function targets(s,full){
    if(!s || s[13] || !s[15] || !s[25].size)return;
    safe(function(){var list=s[1].getState().lines;if(!Array.isArray(list))return;
      var count=Math.min(list.length,full?2000:64),found=new Set(),live=new Set(),start=full?0:Math.max(0,list.length-count);
      s[2].forEach(function(id){live.add(id);});s[3].forEach(function(id){live.add(id);});
      for(var i=start;i<start+count;i++){var line=list[i].line || list[i],id=label(s,line,false);if(s[25].has(id))found.add(id);}
      s[25].forEach(function(record,id){var status=found.has(id)?2:count===list.length && live.has(id)?1:3,time=Date.now();
        if(record[1]!==status || record[3]!==s[16] || time-record[2]>=10000)
          if(emit(21,s,id,record[0],status,count,list.length,0)){record[1]=status;record[2]=time;record[3]=s[16];}
      });
    });
  }
  function storeHook(s){
    if(!s || s[13] || !s[15] || s[26])return;
    safe(function(){var state=s[1].getState(),descriptor=Object.getOwnPropertyDescriptor(state,"pushRewardRedemption");
      if(!descriptor || !descriptor.writable || typeof descriptor.value!=="function")return;
      var native=descriptor.value,copy=Object.assign({},descriptor);
      copy.value=function(){var line=arguments[0],id=0,f=0;
        safe(function(){if(s[13] || !s[15])return;id=label(s,line,true);f=lineFlags(s,line,id)|64;watch(s,id,f);emit(17,s,id,f,2,1,0,0);});
        try{var value=native.apply(this,arguments);safe(function(){if(id){emit(17,s,id,f,2,2,0,0);targets(s,true);}});return value;}
        catch(error){safe(function(){if(id)emit(17,s,id,f,2,3,0,errorCode(error));});throw error;}
      };
      Object.defineProperty(state,"pushRewardRedemption",copy);s[26]=[state,native,copy.value];
    });
  }
  function restoreStore(s){
    if(!s || !s[26])return;var record=s[26];
    safe(function(){[record[0],s[1].getState()].forEach(function(state){var d=Object.getOwnPropertyDescriptor(state,"pushRewardRedemption");if(d && d.writable && d.value===record[2]){d.value=record[1];Object.defineProperty(state,"pushRewardRedemption",d);}});});s[26]=null;
  }
  function seen(s,map,event,id,f,a) {
    if (!id || !s || s[13]) return;
    var time=Date.now(), previous=map.get(id);
    if (previous!==undefined && time-previous<10000) return;
    if (emit(event,s,id,f,a,0,0,0)) trim(map,id,time,256);
  }
  function snapshot(s,force) {
    if (!s || s[13] || (!force && Date.now()-s[6]<2000)) return;
    s[6]=Date.now();
    safe(function () {
      var state=s[1].getState(), list=state.lines, f=(state.paused?8:0)|(state.chatHidden?16:0)|(state.suspended?32:0);
      if (s[15]>0 && state._tmiClient!==s[18]) {
        if (s[18] && clients.get(s[18])===s) clients.delete(s[18]);
        s[18]=state._tmiClient; if (s[18]) clients.set(s[18],s);
      }
      var length=Array.isArray(list)?list.length:-1;
      storeHook(s);targets(s,true);
      emit(10,s,0,f,length,state.connected?1:0,Math.min(32,Math.max(0,length)),s[20]);
      if (length>0) {
        var count=Math.min(length,2000), start=s[20]%count;
        for (var i=0;i<Math.min(count,32);i++) {
          var entry=list[(start+i)%count], line=entry.line || entry, id=label(s,line,true);
          watch(s,id,lineFlags(s,line,id));
          seen(s,s[4],4,id,lineFlags(s,line,id)|f,1);
        }
        s[20]=(start+32)%count;
      }
    });
  }
  function unsubscribe(s) {
    restoreStore(s);
    if (typeof s[8]==="function") safe(s[8]); s[8]=null;
    if (s[18] && clients.get(s[18])===s) clients.delete(s[18]); s[18]=null;
  }
  function subscribe(s) {
    if (!s || s[13]) return;
    storeHook(s);
    if (!s[8] && typeof s[1].subscribe==="function") s[8]=safe(function () { return s[1].subscribe(function () { targets(s,false);snapshot(s,false); }); });
    snapshot(s,true);emit(12,s,0,0,typeof s[8]==="function"?1:0,currentHooks(),0,0);
  }
  function session(store) {
    if (!store || typeof store.getState!=="function") return null;
    var s=stores.get(store); if (s && !s[13]) { s[12]=Date.now(); return s; }
    if (sessions.length>=4) {
      var at=0;
      for (var i=1;i<sessions.length;i++) if ((sessions[i][15]===0 && sessions[at][15]>0) || ((sessions[i][15]===0)===(sessions[at][15]===0) && sessions[i][12]<sessions[at][12])) at=i;
      var old=sessions.splice(at,1)[0]; emit(11,old,0,0,3,old[15],0,0); unsubscribe(old); stores.delete(old[1]); old[13]=true;old[1]=null;
      old[2].clear();old[3].clear();old[4].clear();old[7].clear();old[9]=new WeakMap();old[10].clear();old[11].clear();old[23].clear();
      old[25].clear();
    }
    if (sequence>=10000000) return null;
    s=[];s[0]=++sequence;s[1]=store;s[2]=new Map();s[3]=new Map();s[4]=new Map();s[5]=0;s[6]=-100000;s[7]=new Map();s[9]=new WeakMap();s[10]=new Map();s[11]=new Map();
    s[12]=Date.now();s[13]=false;s[15]=0;s[16]=0;s[17]=0;s[19]=null;s[20]=0;s[21]=0;s[22]=0;s[23]=new Map();s[24]=0;
    s[25]=new Map();s[26]=null;
    stores.set(store,s);sessions.push(s);emit(0,s,0,0,1,0,0,0);return s;
  }
  function errorCode(error) { return safe(function () { return error && error.name==="TypeError"?1:error && error.name==="RangeError"?2:3; }) || 3; }
  function currentHooks(){var count=0;hookRecords.forEach(function(record){var descriptor=Object.getOwnPropertyDescriptor(record[0],record[1]);if(record[1]!=="onChannelPointsRewardEvent" && descriptor && descriptor.value===record[2])count++;});return count;}
  function routeHook(){return hookRecords.some(function(record){var d=Object.getOwnPropertyDescriptor(record[0],record[1]);return record[1]==="onChannelPointsRewardEvent" && d && d.value===record[2];})?1:0;}
  function method(name,wrap) {
    safe(function () {
      var target=client.prototype, descriptor=Object.getOwnPropertyDescriptor(target,name);
      if (!descriptor || typeof descriptor.value!=="function" || !descriptor.writable) return;
      var copy=Object.assign({},descriptor);copy.value=wrap(descriptor.value);Object.defineProperty(target,name,copy);hookRecords.push([target,name,copy.value]);
    });
  }
  method("translateChatMessage",function (native) { return function () {
    var result=native.apply(this,arguments), s=clients.get(this), event=arguments[0],route=routes.get(this);
    safe(function () { var id=label(s,result,true), own=event && event.sentByCurrentUser?1:0;if(s && id && own)trim(s[23],id,own,256);
      emit(1,s,id,lineFlags(s,result,id)|own,result?1:0,0,0,0);
      if(route){route[1]=id;route[2]=lineFlags(s,result,id)|own|64;watch(s,id,route[2]);emit(17,s,id,route[2],1,1,0,0);route[3]=true;}
    });return result;
  }; });
  method("emitLine",function (native) { return function () {
    var s=clients.get(this),line=arguments[0],id=safe(function () { return label(s,line,true); }) || 0;
    safe(function(){watch(s,id,lineFlags(s,line,id));});
    safe(function () { emit(2,s,id,lineFlags(s,line,id),1,0,0,0); });
    try { var value=native.apply(this,arguments);safe(function () { emit(3,s,id,lineFlags(s,line,id),1,0,0,0);targets(s,true);snapshot(s,false); });return value; }
    catch (error) { safe(function () { emit(3,s,id,lineFlags(s,line,id),0,errorCode(error),0,0); });throw error; }
  }; });
  method("onChannelPointsRewardEvent",function(native){return function(){
    var s=clients.get(this),previous=routes.get(this),route=[s,0,64,false];if(s)routes.set(this,route);
    try{var value=native.apply(this,arguments);safe(function(){if(!route[3])emit(17,s,0,64,1,1,0,0);emit(17,s,route[1],route[2],1,2,0,0);targets(s,true);});return value;}
    catch(error){safe(function(){if(!route[3])emit(17,s,0,64,1,1,0,0);emit(17,s,route[1],route[2],1,3,0,errorCode(error));});throw error;}
    finally{if(previous)routes.set(this,previous);else routes.delete(this);}
  };});
  safe(function(){if(!rewardModule)return;var descriptor=Object.getOwnPropertyDescriptor(rewardModule,"ChannelPointsRewardLine");
    if(!descriptor || !descriptor.writable || typeof descriptor.value!=="function")return;
    var native=descriptor.value,copy=Object.assign({},descriptor);
    copy.value=function(p){var c=React.useContext(Context),s=c && c[0],line=p && p.event,id=safe(function(){return label(s,line,true);}) || 0,f=safe(function(){return lineFlags(s,line,id)|64;}) || 64;
      var available=0,body=0;safe(function(){available=p.rewardsById && p.rewardsById[line.rewardId]?2:1;body=typeof line.body==="string"?(line.body.trim().length?2:1):0;watch(s,id,f);});
      try{var value=native.apply(this,arguments);safe(function(){emit(18,s,id,f,available,value===null?1:React.isValidElement && React.isValidElement(value)?2:0,body,0);});return value;}
      catch(error){safe(function(){emit(18,s,id,f,available,3,body,errorCode(error));});throw error;}
    };Object.defineProperty(rewardModule,"ChannelPointsRewardLine",copy);rewardHook=copy.value;
  });
  var NativeLine=lines.ChatLine;
  lines.ChatLine=function (p) {
    var c=safe(function () { var s=session(p.chatStore),id=label(s,p.line,true),f=lineFlags(s,p.line,id);watch(s,id,f);return [s,id,f]; }),props={};props.value=c;
    return React.createElement(Context.Provider,props,React.createElement(NativeLine,p));
  };
  function forward(ref,node) { if (typeof ref==="function") return ref(node);if(ref)ref.current=node; }
  function request(node,callback){
    if(pending>=32){registrySkipped++;return;}pending++;var complete=false;
    try{node.measureInWindow(function(){
      if(complete)return;complete=true;pending--;var args=arguments;safe(function(){callback.apply(null,args);});
    });}catch(error){if(!complete){complete=true;pending--;}}
  }
  function Row(p) {
    var c=React.useContext(Context),view=React.useRef(null),generation=React.useRef(0),current=React.useRef(null),token=React.useRef({}),layout=React.useRef(null);
    current.current=[p.data,c];
    var callbacks=React.useMemo(function () {
      var value={},originalRef=p.data.ref;
      value.sample=function (frame) {
        var c=current.current[1],node=view.current,version=generation.current,cycle=c && c[0] && c[0][16];
        if (!c || !c[0] || c[0][13] || !node || typeof node.measureInWindow!=="function") return;
        safe(function () { request(node,function(x,y,w,h) {
          var latest=current.current[1];
          if (latest && latest[0]===c[0] && latest[1]===c[1] && !c[0][13] && c[0][16]===cycle && c[0][22]===frame && version===generation.current && view.current===node) emit(7,c[0],c[1],c[2],x,y,w,h,frame);
        }); });
      };
      value.ref=function (node) {
        view.current=node;generation.current++;safe(function () { var c=current.current[1];if(c)emit(15,c[0],c[1],c[2],node?1:0,0,0,0); });
        var cleanup=forward(originalRef,node);
        if (typeof cleanup==="function") return function () { view.current=null;generation.current++;safe(function(){var c=current.current[1];if(c)emit(15,c[0],c[1],c[2],0,0,0,0);});return cleanup.apply(this,arguments); };
        return cleanup;
      };
      value.onLayout=function (event) {
        var data=current.current[0],c=current.current[1];
        try { if(data.onLayout)return data.onLayout.apply(this,arguments); }
        finally { safe(function () { var rect=event && event.nativeEvent && event.nativeEvent.layout;
          if(c && rect){var old=layout.current;
            if(!old || old[0]!==c[1] || old[1]!==rect.height || old[2]!==rect.width || old[3]!==rect.x || old[4]!==rect.y)
              if(emit(6,c[0],c[1],c[2],rect.height,rect.width,rect.x,rect.y))layout.current=[c[1],rect.height,rect.width,rect.x,rect.y];
          }
        }); }
      };return value;
    },[p.data.ref]);
    React.useEffect(function () {
      var s=c && c[0];if(!s || s[13])return;
      s[7].set(token.current,callbacks.sample);
      if(s[7].size>128){s[7].delete(s[7].keys().next().value);registrySkipped++;}
      return function(){s[7].delete(token.current);};
    },[c && c[0],c && c[1],callbacks]);
    var copy=Object.assign({},p.data);copy.ref=callbacks.ref;copy.onLayout=callbacks.onLayout;return React.createElement(p.type,copy);
  }
  function List(p) {
    var c=React.useContext(Context),current=React.useRef(null),view=React.useRef(null),generation=React.useRef(0);current.current=[p.data,c];
    var callbacks=React.useMemo(function () {
      var value={},originalRef=p.data.ref;
      value.sample=function(frame) {
        var s=current.current[1] && current.current[1][0],node=view.current,version=generation.current,cycle=s && s[16];
        safe(function(){var scroll=node && typeof node.getNativeScrollRef==="function" && node.getNativeScrollRef();
          if(s && !s[13] && scroll && typeof scroll.measureInWindow==="function")request(scroll,function(x,y,w,h){
            if(!s[13] && s[16]===cycle && s[22]===frame && version===generation.current && view.current===node && current.current[1] && current.current[1][0]===s)emit(8,s,0,0,x,y,w,h,frame);
          });
        });
        safe(function(){if(!s || !node)return;var state=typeof node.getState==="function"?safe(function(){return node.getState();}):null,data=state && state.data;
          emit(22,s,0,0,routeHook(),s[26] && s[1].getState().pushRewardRedemption===s[26][2]?1:0,rewardModule && rewardModule.ChannelPointsRewardLine===rewardHook?1:0,Array.isArray(data)?1:0);
          if(!Array.isArray(data)){registrySkipped++;return;}
          var count=Math.min(data.length,2000),selected=[];
          for(var i=0;i<count;i++){var line=data[i].line || data[i],id=label(s,line,false);if(s[25].has(id))selected.push([i,id,lineFlags(s,line,id)]);}
          var offset=s[27] || 0,limit=Math.min(4,selected.length);s[27]=selected.length?(offset+limit)%selected.length:0;
          for(var j=0;j<limit;j++){
            var entry=selected[(offset+j)%selected.length],index=entry[0],item=data[index],key=item.key,known=state.sizes && typeof state.sizes.has==="function" && state.sizes.has(key),size=known?number(state.sizes.get(key)):-1,pos=typeof state.positionAtIndex==="function"?state.positionAtIndex(index):-1;
            if(size<0)known=false;
            emit(19,s,entry[1],entry[2],size,pos,known?1:0,index,frame);
            var cell=typeof state.elementAtIndex==="function"?state.elementAtIndex(index):null;
            if(cell && typeof cell.measureInWindow==="function")(function(entry,index,key,cell){request(cell,function(x,y,w,h){
              var latest=view.current===node && typeof node.getState==="function"?node.getState():null;
              if(!s[13] && s[16]===cycle && s[22]===frame && version===generation.current && latest && latest.data && latest.data[index] && latest.data[index].key===key && latest.elementAtIndex(index)===cell)emit(20,s,entry[1],entry[2],x,y,w,h,frame);
            });})(entry,index,key,cell);
          }
        });
      };
      value.renderItem=function () {
        var data=current.current[0],s=current.current[1] && current.current[1][0],item=arguments[0];
        safe(function(){var line=item && item.item && (item.item.line || item.item),id=label(s,line,true);if(s)seen(s,s[11],5,id,lineFlags(s,line,id),2);});
        return data.renderItem.apply(this,arguments);
      };
      value.ref=function(node) {
        view.current=node;generation.current++;var result=forward(originalRef,node);
        if(typeof result==="function")return function(){view.current=null;generation.current++;return result.apply(this,arguments);};return result;
      };return value;
    },[p.data.ref,p.data.renderItem]);
    var s=c && c[0];
    if(s && Array.isArray(p.data.data))safe(function(){
      var data=p.data.data,count=Math.min(data.length,2000);
      for(var i=Math.max(0,count-32);i<count;i++){var line=data[i].line || data[i],id=label(s,line,true);seen(s,s[10],5,id,lineFlags(s,line,id),1);}
    });
    React.useEffect(function(){if(s && !s[13])s[19]=callbacks.sample;return function(){if(s && s[19]===callbacks.sample)s[19]=null;};},[s,callbacks]);
    var copy=Object.assign({},p.data);copy.ref=callbacks.ref;if(typeof p.data.renderItem==="function")copy.renderItem=callbacks.renderItem;return React.createElement(p.type,copy);
  }
  function Boundary(p) {
    var c=React.useContext(Context),current=React.useRef(null);current.current=[p.data,c];
    var report=React.useMemo(function(){return function(){
      var data=current.current[0],s=current.current[1] && current.current[1][0],error=arguments[0];
      safe(function(){var line=data.children && data.children.props && data.children.props.line,id=label(s,line,true);emit(9,s,id,lineFlags(s,line,id),errorCode(error),0,0,0);});
      return data.reportError.apply(this,arguments);
    };},[]);
    var copy=Object.assign({},p.data);copy.reportError=report;return React.createElement(p.type,copy);
  }
  function intercept(native){return function(type,p,key){
    var component=p && (p.testID==="chat-message-row" || p.testID==="chat-channelpointsreward-line")?Row:p && p.testID==="chat-message-list"?List:p && p.name==="ChatLine" && typeof p.reportError==="function"?Boundary:null;
    if(component){var props={};props.type=type;props.data=p;return native(component,props,key);}return native.apply(this,arguments);
  };}
  jsx.jsx=intercept(jsx.jsx);if(jsx.jsxs)jsx.jsxs=intercept(jsx.jsxs);
  setInterval(function(){safe(function(){
    var order=sessions.slice();order.forEach(function(value,index){var s=order[(index+sampleCursor)%order.length];if(s[13] || !s[15])return;
      snapshot(s,false);emit(12,s,0,0,typeof s[8]==="function"?1:0,currentHooks(),0,0);
      s[22]=s[22]>=10000000?1:s[22]+1;emit(14,s,0,0,s[7].size,Math.min(8,s[7].size),pending,0,s[22]);
      if(s[19])s[19](s[22]);
      var probes=Array.from(s[7].values()),count=probes.length;
      for(var i=0;i<Math.min(8,count);i++)probes[(s[21]+i)%count](s[22]);if(count)s[21]=(s[21]+8)%count;
    });
    var s=sessions.filter(function(s){return !s[13] && s[15]>0;})[0];
    if(s && emit(16,s,0,0,skipped,urgentSkipped,registrySkipped,aliases)){skipped=0;urgentSkipped=0;registrySkipped=0;aliases=0;}
    sampleCursor=(sampleCursor+1)%Math.max(1,order.length);
  });},2000);
  return function(p){
    var s=safe(function(){return session(p.chatStore);}),props={};props.value=[s,0,0];
    React.useEffect(function(){
      if(!s || s[13])return;s[15]++;s[16]++;subscribe(s);emit(13,s,0,0,1,s[15],0,0);
      return function(){if(s[13])return;s[15]=Math.max(0,s[15]-1);snapshot(s,true);emit(13,s,0,0,0,s[15],0,0);if(!s[15])unsubscribe(s);};
    },[s]);
    return React.createElement(Context.Provider,props,React.createElement(original,p));
  };
}
