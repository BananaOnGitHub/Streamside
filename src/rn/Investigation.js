/* Fixed built-in adapter. No downloaded source, periodic work or React hooks.
 * This function is grafted into factory 4900's additional environment slot.
 * The donor's own list JSX call passes chatStore as this; its component type,
 * keys, hook sequence, callbacks and original JSX function remain intact. */
function install() {
  var name=String.fromCharCode(83,116,114,101,97,109,115,105,100,101,73,110,118,101,115,116,105,103,97,116,105,111,110);
  var modules=__r(16).default, nativeJSX=__r(245).jsx;
  var bridge=modules && modules[name];
  if (!bridge || typeof bridge.ready!=="function" || typeof bridge.ack!=="function" || typeof nativeJSX!=="function" || typeof global.RN$registerCallableModule!=="function" || typeof WeakMap!=="function") return null;
  var refs=new WeakMap(),lists=[],next=0,epoch=0;
  function safe(fn) { try { return fn(); } catch (error) { return null; } }
  function forget(record) {
    var at=lists.indexOf(record);if(at>=0)lists.splice(at,1);
    if(record[2] && refs.get(record[2])===record)refs.delete(record[2]);
    record[1]=null;record[3]=null;
  }
  function forward(ref,context,args) {
    if(typeof ref==="function")return ref.apply(context,args);
    if(ref)ref.current=args[0];
  }
  function register(record,node) {
    if(!node){forget(record);return;}
    if(lists.indexOf(record)<0){if(lists.length>=2){forget(record);return;}lists.push(record);}
    record[3]=node;
  }
  function renderList(type,props) {
    var store=this,copy=props;
    safe(function(){
      var ref=props && props.ref;
      if(!store || typeof store.getState!=="function" || !ref || (typeof ref!=="object" && typeof ref!=="function"))return;
      var record=refs.get(ref);
      if(!record || record[1]!==store){
        if(next>=10000000)return;
        record=[];record.push(++next,store,ref,null,null);
        record[4]=function(node){
          var value=forward(record[2],this,arguments);
          safe(function(){register(record,node);});
          if(typeof value==="function")return function(){try{return value.apply(this,arguments);}finally{safe(function(){forget(record);});}};
          return value;
        };
        refs.set(ref,record);
      }
      copy=Object.assign({},props);copy.ref=record[4];
    });
    return nativeJSX(type,copy);
  }
  function command(operation,generation,sequence,parameters) {
    if(!epoch)return;
    /* Only the startup probe is enabled in checkpoint B. Event and snapshot
     * commands are admitted only after their compiled adapters are installed. */
    if(operation===0 && generation===0 && sequence===0){bridge.ack(epoch,0,0,0,true);return;}
    bridge.ack(epoch,generation,sequence,operation,false);
  }
  var methods={};methods.command=command;
  global.RN$registerCallableModule(name,function(){return methods;});
  epoch=bridge.ready(1,0);
  return epoch?renderList:null;
}
