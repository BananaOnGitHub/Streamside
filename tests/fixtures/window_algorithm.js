/* Test-only dependencies for the unchanged donor RN factory 350.
 * Babel array destructuring is identity here; feature flags are explicit.
 * Both overlap search and render-window calculation execute donor bytecode. */
var windowExports = {};
function windowRequire(id) {
  if (id === 0) return function (x) { return x && x.__esModule ? x : {default:x}; };
  if (id === 1) return function (x) { return x; };
  return {fixVirtualizeListCollapseWindowSize:function () { return _runtimeGlobal._windowFeature; }};
}
buildLocalEcho(_runtimeGlobal, windowRequire, null, null, {exports:windowExports}, windowExports, [0,1,2]);
_runtimeGlobal._windowAlgorithms = windowExports;
_runtimeGlobal._windowFeature = false;
