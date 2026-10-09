// Actual Hermes-98 bytecode and JSI host-function entry. No JS source evaluator.
#include "hermes/hermes.h"
#include "jsi/jsi.h"
#include <dlfcn.h>
#include <fstream>
#include <iostream>
#include <iterator>
#include <cmath>
using namespace facebook;
class FileBuffer final : public jsi::Buffer {
  std::string bytes_;
 public:
  explicit FileBuffer(const char *path) { std::ifstream f(path,std::ios::binary); if(!f)throw std::runtime_error("Cannot read bytecode"); bytes_.assign(std::istreambuf_iterator<char>(f),{}); }
  size_t size() const override { return bytes_.size(); }
  const uint8_t *data() const override { return reinterpret_cast<const uint8_t*>(bytes_.data()); }
};
int main(int argc,char **argv) {
 if(argc<3)return 2;
 void *adapter=dlopen(argv[1],RTLD_NOW);if(!adapter){std::cerr<<dlerror()<<'\n';return 2;}
 auto observe=reinterpret_cast<double(*)(double,double,const char*,double,double)>(dlsym(adapter,"ss_observe"));
 auto report=reinterpret_cast<const char*(*)()>(dlsym(adapter,"ss_report"));
 if(!observe||!report)return 2;
 try {
 auto runtime=facebook::hermes::makeHermesRuntime();auto &r=*runtime;
 r.global().setProperty(r,"_runtimeGlobal",r.global());
 r.global().setProperty(r,"_observeNative",jsi::Function::createFromHostFunction(r,jsi::PropNameID::forAscii(r,"_observeNative"),5,
  [observe](jsi::Runtime &rt,const jsi::Value &,const jsi::Value *v,size_t n)->jsi::Value {
   if(n!=5||!v[0].isNumber()||!v[1].isNumber()||!v[3].isNumber()||!v[4].isNumber())return jsi::Value::undefined();
   std::string s=v[2].isString()?v[2].asString(rt).utf8(rt):std::string();
   double result=observe(v[0].asNumber(),v[1].asNumber(),v[2].isString()?s.c_str():nullptr,v[3].asNumber(),v[4].asNumber());
   return std::isnan(result)?jsi::Value::undefined():jsi::Value(result);
  }));
 r.global().setProperty(r,"_diagnosticReport",jsi::Function::createFromHostFunction(r,jsi::PropNameID::forAscii(r,"_diagnosticReport"),0,
  [report](jsi::Runtime &rt,const jsi::Value &,const jsi::Value *,size_t)->jsi::Value{return jsi::String::createFromUtf8(rt,report());}));
 for(int i=2;i<argc;i++) {auto buffer=std::make_shared<FileBuffer>(argv[i]); auto prepared=r.prepareJavaScript(buffer,argv[i]);r.evaluatePreparedJavaScript(prepared);}
 std::cout<<report();
 }catch(const jsi::JSIException &e){std::cerr<<e.what()<<'\n';return 1;}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}
 return 0;
}
