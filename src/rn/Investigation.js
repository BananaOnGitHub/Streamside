/* Fixed donor adapter. Dormant: ref registration only, no timers or scans.
 * Numeric wire rows: kind,time,family,scope,label,flags,a,b,c.
 * Private bounded aliases never cross the bridge. No message contents read. */
// Metro supplies its global object to donor factories; the legacy global alias
// is not established in this donor. Use the standard Hermes globalThis binding.
function install() {
  var bridge=null;try{
  var name=String.fromCharCode(83,116,114,101,97,109,115,105,100,101,73,110,118,101,115,116,105,103,97,116,105,111,110);
  var modules=__r(16).default,nativeJSX=__r(245).jsx,bridge=modules && modules[name];
  if(bridge && typeof bridge.startup==="function"){
    var available=(typeof bridge.ready==="function"?1:0)|(typeof bridge.ack==="function"?2:0)|(typeof bridge.report==="function"?4:0)|(typeof nativeJSX==="function"?8:0)|(typeof globalThis.RN$registerCallableModule==="function"?16:0)|(typeof WeakMap==="function"?32:0)|(typeof Map==="function"?64:0)|(globalThis.performance && typeof globalThis.performance.now==="function"?128:0);
    bridge.startup(available);
  }
  if(!bridge || typeof bridge.ready!=="function" || typeof bridge.ack!=="function" || typeof bridge.report!=="function" || typeof nativeJSX!=="function" || typeof globalThis.RN$registerCallableModule!=="function" || typeof WeakMap!=="function" || typeof Map!=="function" || !globalThis.performance || typeof globalThis.performance.now!=="function")return null;
  var refs=new WeakMap(),lists=[],next=0,epoch=0,active=false,generation=0,sequence=0,config=null,hooks=[],clients=new WeakMap();
  var ordinary=[],priority=[],ordinaryAt=0,priorityAt=0,aliases=[],aliasBytes=0,labels=0,skipped=0,urgentSkipped=0,evicted=0,errors=0,coverage=0;
  var start=0,last=0,tokens=0,urgentTokens=0,work=0,capturing=false,captureTimer=null,captureRows=null;
  function safe(fn){try{return fn();}catch(error){errors=Math.min(10000000,errors+1);return null;}}
  function clock(){return globalThis.performance.now();}
  function number(x){return typeof x==="number" && Number.isFinite(x) && Math.abs(x)<=10000000?Math.round(x):-1;}
  function elapsed(){return Math.min(10000000,Math.max(0,Math.round(clock()-start)));}
  function row(kind,time,family,scope,label,flags,a,b,c){var out=[];out.push(kind,time,family,scope,label,flags,number(a),number(b),number(c));return out;}
  function append(value,urgent){var buffer=urgent?priority:ordinary,limit=config[urgent?12:11];if(buffer.length<limit)buffer.push(value);else if(urgent){buffer[priorityAt]=value;priorityAt=(priorityAt+1)%limit;}else{buffer[ordinaryAt]=value;ordinaryAt=(ordinaryAt+1)%limit;}}
  function admit(family,urgent){
    if(!active || capturing || !(config[0]&(1<<family)))return false;
    var time=clock(),delta=Math.max(0,time-last);last=time;
    tokens=Math.min(config[8],tokens+delta*config[8]/1000);urgentTokens=Math.min(config[9],urgentTokens+delta*config[9]/1000);work=Math.max(0,work-delta*config[6]/1000);
    if(work>=config[6] || (urgent?urgentTokens:tokens)<1){if(urgent)urgentSkipped=Math.min(10000000,urgentSkipped+1);else skipped=Math.min(10000000,skipped+1);return false;}
    if(urgent)urgentTokens--;else tokens--;return true;
  }
  function observe(family,s,line,flags,a,b,c,urgent){
    if(!s || !s[13] || !admit(family,urgent))return;
    var began=clock();safe(function(){append(row(urgent?2:1,elapsed(),family,s[0],label(s,line,true),flags,a,b,c),urgent);});
    var cost=Math.max(0,clock()-began)*1000;work+=cost;if(cost>config[7])work=config[6];
  }
  function bytes(key){if(typeof key!=="string" || key.length>256)return 0;var n=0;for(var i=0;i<key.length;i++){var c=key.charCodeAt(i);n+=c<128?1:c<2048?2:3;if(n>256)return 0;}return n;}
  function remember(map,key,value){var n=bytes(key);if(!n || map.has(key))return;while(aliases.length && (aliases.length>=config[13] || aliasBytes+n>config[14])){var old=aliases.shift();if(old[0].get(old[1])===old[2])old[0].delete(old[1]);aliasBytes-=old[3];evicted=Math.min(10000000,evicted+1);}if(n>config[14])return;map.set(key,value);var item=[];item.push(map,key,value,n);aliases.push(item);aliasBytes+=n;}
  function label(s,line,create){
    if(!line || typeof line!=="object")return 0;
    var id=bytes(line.id)?line.id:null,nonce=bytes(line.clientNonce)?line.clientNonce:null;
    var value=(id && s[9].get(id)) || (nonce && s[10].get(nonce)) || s[11].get(line);
    if(!value && create && labels<10000000)value=++labels;
    if(value && create){if(id)remember(s[9],id,value);if(nonce)remember(s[10],nonce,value);if(!s[11].has(line)){if(s[12]>=256){s[11]=new WeakMap();s[12]=0;evicted=Math.min(10000000,evicted+1);}s[12]++;s[11].set(line,value);}}
    return value || 0;
  }
  function method(target,key,family,specific){
    safe(function(){var descriptor=null,depth=0;while(target && depth++<4){descriptor=Object.getOwnPropertyDescriptor(target,key);if(descriptor)break;target=Object.getPrototypeOf(target);}if(!descriptor || !descriptor.writable || typeof descriptor.value!=="function" || hooks.length>=16 || !(config[0]&((1<<family)|(family===1?4:0))))return;
      for(var i=0;i<hooks.length;i++)if(hooks[i][0]===target && hooks[i][1]===key)return;
      var original=descriptor.value,copy=Object.assign({},descriptor);
      copy.value=function(){var s=specific || clients.get(this);if(!active || !s || !s[13])return original.apply(this,arguments);
        var args=arguments,result,failed=false;
        try{result=original.apply(this,args);return result;}catch(error){failed=true;throw error;}finally{
          safe(function(){var line=family===0?result:args[0],own=!!(line && line.isUnpublished),f=own?1:0;if(family===0 && args[0] && args[0].sentByCurrentUser)f|=1;
            observe(family,s,line,f,failed?3:result===null?1:2,0,0,failed || !!(f&1) || family===5 || family===6);
            if(family===1 && own)observe(2,s,line,1,failed?3:2,0,0,true);
          });
        }
      };Object.defineProperty(target,key,copy);var item=[];item.push(target,key,original,copy.value,descriptor,specific);hooks.push(item);coverage|=1<<family;if(family===1)coverage|=4;
    });
  }
  function attach(s){
    if(!active || !s[3] || s[13])return;s[13]=true;s[9]=new Map();s[10]=new Map();s[11]=new WeakMap();s[12]=0;
    safe(function(){var state=s[1].getState(),client=state._tmiClient;s[6]=client;if(client){clients.set(client,clients.has(client) && clients.get(client)!==s?null:s);method(client,"translateChatMessage",0,null);method(client,"emitLine",1,null);method(client,"onChannelPointsRewardEvent",5,null);}method(state,"pushRewardRedemption",6,s);
      if(typeof s[1].subscribe==="function")s[5]=s[1].subscribe(function(state){if(!active || !s[13])return;s[7]=Math.min(10000000,s[7]+1);safe(function(){var client=state && state._tmiClient;if(client!==s[6]){if(s[6])clients.delete(s[6]);s[6]=client;if(client)clients.set(client,clients.has(client) && clients.get(client)!==s?null:s);method(client,"translateChatMessage",0,null);method(client,"emitLine",1,null);method(client,"onChannelPointsRewardEvent",5,null);}observe(4,s,null,0,Array.isArray(state && state.lines)?state.lines.length:-1,0,0,false);});});
    });coverage|=256;if(typeof s[5]==="function")coverage|=16;observe(8,s,null,0,1,0,0,true);
  }
  function detach(s){s[13]=false;for(var i=hooks.length-1;i>=0;i--)if(hooks[i][5]===s){var h=hooks.splice(i,1)[0];safe(function(){var d=Object.getOwnPropertyDescriptor(h[0],h[1]);if(d && d.value===h[3])Object.defineProperty(h[0],h[1],h[4]);});}if(typeof s[5]==="function")safe(s[5]);s[5]=null;if(s[6])clients.delete(s[6]);s[6]=null;s[8]=null;s[9]=null;s[10]=null;s[11]=null;s[12]=0;}
  function stop(){active=false;capturing=false;if(captureTimer!==null)globalThis.clearTimeout(captureTimer);captureTimer=null;captureRows=null;lists.forEach(detach);for(var i=hooks.length-1;i>=0;i--){var h=hooks[i];safe(function(){var d=Object.getOwnPropertyDescriptor(h[0],h[1]);if(d && d.value===h[3])Object.defineProperty(h[0],h[1],h[4]);});}hooks=[];clients=new WeakMap();aliases=[];aliasBytes=0;ordinary=[];priority=[];ordinaryAt=0;priorityAt=0;}
  function forget(record){record[14]++;if(active)observe(8,record,null,0,0,0,0,true);detach(record);var at=lists.indexOf(record);if(at>=0)lists.splice(at,1);if(record[2] && refs.get(record[2])===record)refs.delete(record[2]);record[1]=null;record[3]=null;}
  function forward(ref,context,args){if(typeof ref==="function")return ref.apply(context,args);if(ref)ref.current=args[0];}
  function register(record,node){if(!node){forget(record);return;}if(lists.indexOf(record)<0){if(lists.length>=2){forget(record);return;}lists.push(record);}record[14]++;record[3]=node;if(active)attach(record);}
  function renderList(type,props){var store=this,copy=props;safe(function(){var ref=props && props.ref;if(!store || typeof store.getState!=="function" || !ref || (typeof ref!=="object" && typeof ref!=="function"))return;
    var record=refs.get(ref);if(!record || record[1]!==store){if(next>=10000000)return;record=[];record.push(++next,store,ref,null,null,null,null,0,null,null,null,null,0,false,0);
      record[4]=function(node){var value=forward(record[2],this,arguments);safe(function(){register(record,node);});var mounted=record[14];if(typeof value==="function")return function(){try{return value.apply(this,arguments);}finally{safe(function(){if(record[14]===mounted)forget(record);});}};return value;};refs.set(ref,record);}
    copy=Object.assign({},props);copy.ref=record[4];});return nativeJSX(type,copy);}
  function ordered(buffer,at){return buffer.slice(at).concat(buffer.slice(0,at));}
  // Comparison uses only the already admitted identity fields. No renderer or
  // mutating LegendList accessor is called. -1 means identity is incomparable.
  function relation(a,b){
    if(!a || !b || typeof a!=="object" || typeof b!=="object")return -1;
    if(a===b)return 1;
    var ai=bytes(a.id)?a.id:null,bi=bytes(b.id)?b.id:null,an=bytes(a.clientNonce)?a.clientNonce:null,bn=bytes(b.clientNonce)?b.clientNonce:null;
    if(ai && bi && ai===bi || an && bn && an===bn)return 1;
    return ai && bi || an && bn?0:-1;
  }
  function identityFlags(line){return !line || typeof line!=="object"?64:bytes(line.id) || bytes(line.clientNonce)?0:512;}
  function snapshot(rows){
    var began=clock(),budget=Math.min(config[6],config[7]),used=0,contexts=[];
    function expired(){return (clock()-began)*1000>=budget;}
    // Context slots: 0 scope,1 store state,2 list state,3 store lines,4 list data,
    // 5 revision,6 mount,7 store length,8 list length,9/10 visible first/last,
    // 11 targets,12 snapshot flags,13/14 visible/margin counts,15 failed reads,
    // 16 store reads,17 full store scan,18 valid range,19 entry limit reached.
    if(!lists.length){rows.push(row(10,elapsed(),8,0,0,4,-1,-1,0));rows.push(row(6,elapsed(),8,0,0,2,0,0,0));return;}
    for(var j=0;j<lists.length && j<config[2];j++){
      var scope=lists[j],state=null,list=null,lines=null,data=null,status=0,revision=scope[7],mount=scope[14];
      if(!expired())safe(function(){if(scope[3] && typeof scope[3].getState==="function"){list=scope[3].getState();data=list.data;}});else status|=4;
      if(!list || !Array.isArray(data))status|=2;
      var length=Array.isArray(data)?data.length:0,storeLength=Array.isArray(lines)?lines.length:0,first=-1,last=-1;safe(function(){if(list){first=list.start;last=list.end;}});
      var valid=!!list && Array.isArray(data) && Number.isInteger(first) && Number.isInteger(last) && (length===0?(first===0 || first===-1) && last===-1:first>=0 && last>=first && last<length);
      rows.push(row(4,elapsed(),8,scope[0],0,status,Array.isArray(data)?length:-1,first,last));
      rows.push(row(7,elapsed(),8,scope[0],0,status,list?list.scroll:-1,list?list.scrollLength:-1,list?list.contentLength:-1));
      var c=[];c.push(scope,state,list,lines,data,revision,mount,storeLength,length,valid?first:-1,valid?last:-1,[],status,0,0,0,0,false,valid,false);contexts.push(c);
    }
    function sample(c,index,flags){
      if(used>=config[3]){c[19]=true;return false;}if(expired()){c[12]|=4;return false;}used++;
      var target=safe(function(){
        var item=c[4][index],line=item && (item.line || item),key=item && item.key,height=-1,position=-1,measurement=1024;
        // has() distinguishes an unmeasured row from a measured height of zero.
        safe(function(){var sizes=c[2].sizes;if(sizes && typeof sizes.has==="function" && typeof sizes.get==="function" && (typeof key==="string" || typeof key==="number")){
          if(!sizes.has(key))measurement=1;
          else{var raw=sizes.get(key);measurement=4;if(typeof raw==="number" && Number.isFinite(raw) && Math.abs(raw)<=10000){height=Math.round(raw*1000);measurement=raw<0?4:raw===0?2:0;}}
        }});
        safe(function(){if(typeof c[2].positionAtIndex==="function")position=number(c[2].positionAtIndex(index));});
        var value=row(9,elapsed(),8,c[0][0],label(c[0],line,true),flags|measurement|identityFlags(line)|32,index,height,position),record=[];
        record.push(line,value,false,true);rows.push(value);return record;
      });
      if(!target){c[15]++;return true;}
      c[11].push(target);if(flags&128)c[13]++;if(flags&256)c[14]++;return true;
    }
    // Every admitted viewport precedes any margin or fallback, including when
    // two lists share the same fixed entry/work allowance.
    for(var a=0;a<contexts.length;a++){
      var c=contexts[a];if(!c[18] || !c[8])continue;
      for(var k=c[9];k<=c[10];k++)if(!sample(c,k,128))break;
    }
    for(var b=0;b<contexts.length;b++){
      var c=contexts[b];if(!c[18] || !c[8] || c[13]!==c[10]-c[9]+1)continue;
      // Two neighbours per side, nearest first. Never replace a visible row.
      for(var distance=1;distance<=2;distance++){
        if(c[9]-distance>=0 && !sample(c,c[9]-distance,256))break;
        if(c[10]+distance<c[8] && !sample(c,c[10]+distance,256))break;
      }
    }
    for(var f=0;f<contexts.length;f++){
      var c=contexts[f];if(c[18] || !Array.isArray(c[4]))continue;
      // Unavailable range is explicit; a bounded tail is context, not viewport.
      var allowance=Math.floor((config[3]-used)/2);
      for(var k=Math.max(0,c[8]-allowance);k<c[8];k++)if(!sample(c,k,0))break;
    }
    // Remaining work is a bounded store tail. Absence is asserted only after
    // a complete, stable and identity-comparable scan of the other side.
    for(var t=0;t<contexts.length;t++){
      var c=contexts[t],storeRows=[];
      if(!expired())safe(function(){c[1]=c[0][1].getState();c[3]=c[1].lines;});else c[12]|=4;
      if(!c[1] || !Array.isArray(c[3]))c[12]|=1;c[7]=Array.isArray(c[3])?c[3].length:0;
      rows.push(row(3,elapsed(),4,c[0][0],0,c[12],Array.isArray(c[3])?c[7]:-1,c[1] && c[1].paused?1:0,c[5]));
      var allowance=Math.floor((config[3]-used)/(contexts.length-t)),start=Math.max(0,c[7]-allowance),scanOK=Array.isArray(c[3]),fullList=c[11].length===c[8] && !(c[12]&2) && !c[15];
      if(scanOK)for(var i=start;i<c[7];i++){
        if(used>=config[3] || expired()){c[12]|=4;scanOK=false;break;}used++;
        var projected=safe(function(){
          var entry=c[3][i],line=entry && (entry.line || entry),matched=false,comparable=true,associated=0;
          for(var n=0;n<c[11].length;n++){
            if(expired()){comparable=false;scanOK=false;c[12]|=4;break;}
            var target=c[11][n],same=relation(line,target[0]);
            if(same===1){target[2]=true;matched=true;associated=target[1][4];}
            if(same<0){target[3]=false;comparable=false;}
          }
          var value=row(8,elapsed(),4,c[0][0],associated || label(c[0],line,true),identityFlags(line)|(identityFlags(line)&64?32:matched?8:fullList && comparable?16:32),i,0,0);
          rows.push(value);storeRows.push(value);return true;
        });
        if(projected)c[16]++;else scanOK=false;
      }
      c[17]=scanOK && start===0 && c[16]===c[7];
      var changed=c[0][7]!==c[5] || c[0][14]!==c[6] || Array.isArray(c[3]) && c[3].length!==c[7] || Array.isArray(c[4]) && c[4].length!==c[8];
      if(changed){c[12]|=8;for(var r=0;r<storeRows.length;r++)storeRows[r][5]=(storeRows[r][5]&~24)|32;}
      for(var n=0;n<c[11].length;n++){var target=c[11][n];target[1][5]=(target[1][5]&~32)|(changed || !target[1][4]?32:target[2]?8:c[17] && target[3]?16:32);}
      var visible=c[18]?(c[8]?c[10]-c[9]+1:0):0,margin=c[18] && c[8]?Math.min(2,c[9])+Math.min(2,c[8]-c[10]-1):0;
      var rangeFlags=!c[18]?4:c[13]===visible && c[14]===margin && !c[15] && !changed?1:2;
      if(c[18] && c[14]<margin)rangeFlags|=8;if(!c[18] && c[11].length)rangeFlags|=16;if(!c[8] && Array.isArray(c[4]))rangeFlags|=32;if(changed)rangeFlags|=64;if(c[12]&4 || c[19])rangeFlags|=128;
      if(c[16]<c[7] || c[11].length<c[8])c[12]|=32;
      rows.push(row(10,elapsed(),8,c[0][0],0,rangeFlags,c[9],c[10],c[13]));
      rows.push(row(6,elapsed(),8,c[0][0],0,c[12],Math.round((clock()-began)*1000),c[16],c[11].length));
    }
  }
  function capture(g,seq){
    capturing=true;var rows=ordered(ordinary,ordinaryAt).concat(ordered(priority,priorityAt));
    // First transfer contains frozen history before any current-state read.
    var header=row(0,elapsed(),0,0,0,0,skipped,urgentSkipped,evicted);rows.unshift(header);
    var part=0,wire=0,began=clock(),snapshotDone=false,maxParts=Math.max(1,1+Math.floor((config[5]-100)*config[10]/1000));
    function send(){captureTimer=null;if(g!==generation || seq!==sequence || !capturing)return;
      var remaining=rows.length,chunk=rows.splice(0,64),final=snapshotDone && rows.length===0;
      if(!final && (part+1>=maxParts || clock()-began>=config[5]-100)){final=true;rows=[];chunk.push(row(6,elapsed(),0,0,0,16,remaining,0,0));}
      var packet=[];packet.push(2,part,final?1:0,chunk);var payload=JSON.stringify(packet);wire+=payload.length;
      var accepted=payload.length<=8192 && wire<=config[15] && safe(function(){return bridge.report(epoch,g,seq,payload);});
      part++;
      if(!accepted){capturing=false;captureRows=null;bridge.ack(epoch,g,seq,2,false);stop();return;}
      if(!snapshotDone){snapshotDone=true;safe(function(){snapshot(rows);});rows.push(row(5,elapsed(),0,0,0,coverage,errors,aliasBytes,labels));}
      if(final){capturing=false;captureRows=null;bridge.ack(epoch,g,seq,2,true);if(!config[1])stop();return;}
      captureRows=rows;captureTimer=globalThis.setTimeout(send,Math.ceil(1000/config[10]));
    }
    send();
  }
  function valid(parameters){
    if(!Array.isArray(parameters) || parameters.length!==16)return false;
    var ceilings=[];ceilings.push(1023,1,2,128,12,2000,10000,2000,8,4,4,256,64,256,65536,65536);
    for(var i=0;i<16;i++)if(!Number.isInteger(parameters[i]) || parameters[i]<(i===1?0:1) || parameters[i]>ceilings[i])return false;return true;
  }
  function command(operation,g,seq,parameters){
    if(!epoch)return;if(operation===0 && g===0 && seq===0){bridge.ack(epoch,0,0,0,true);return;}
    if(!Number.isInteger(g) || !Number.isInteger(seq) || g<generation || g===generation && seq<=sequence)return;
    if(operation===3){generation=g;sequence=seq;stop();bridge.ack(epoch,g,seq,3,true);return;}
    if(operation===1 && !active && valid(parameters)){generation=g;sequence=seq;config=parameters;start=clock();last=start;tokens=config[8];urgentTokens=config[9];work=0;labels=0;skipped=0;urgentSkipped=0;evicted=0;errors=0;coverage=0;active=true;lists.forEach(attach);bridge.ack(epoch,g,seq,1,true);return;}
    if(operation===2 && active && !capturing){generation=g;sequence=seq;capture(g,seq);return;}
    bridge.ack(epoch,g,seq,operation,false);
  }
  var methods={};methods.command=command;globalThis.RN$registerCallableModule(name,function(){return methods;});epoch=bridge.ready(1,7);return epoch?renderList:null;
  }catch(error){try{if(bridge && typeof bridge.startup==="function")bridge.startup(256);}catch(ignored){}return null;}
}
