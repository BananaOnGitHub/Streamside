function exerciseStartup(install){
 var masks=[],original=bridge.startup,clock=global.performance,register=global.RN$registerCallableModule;
 bridge.startup=function(mask){masks.push(mask);};
 global.performance=null;check(install()===null && masks.pop()===127,"missing clock reported without collection");global.performance=clock;
 global.RN$registerCallableModule=null;check(install()===null && masks.pop()===239,"missing command registration reported");
 global.RN$registerCallableModule=function(){throw {private:"PRIVATE-exception"};};check(install()===null && masks.pop()===256,"bootstrap exception bounded to code");
 global.RN$registerCallableModule=register;bridge.startup=original;
}
