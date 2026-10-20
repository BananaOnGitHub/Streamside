function exerciseStartup(install){
 var masks=[],original=bridge.startup,clock=globalThis.performance,register=globalThis.RN$registerCallableModule;
 bridge.startup=function(mask){masks.push(mask);};
 globalThis.performance=null;check(install()===null && masks.pop()===127,"missing clock reported without collection");globalThis.performance=clock;
 globalThis.RN$registerCallableModule=null;check(install()===null && masks.pop()===239,"missing command registration reported");
 globalThis.RN$registerCallableModule=function(){throw {private:"PRIVATE-exception"};};check(install()===null && masks.pop()===256,"bootstrap exception bounded to code");
 globalThis.RN$registerCallableModule=register;bridge.startup=original;
}
