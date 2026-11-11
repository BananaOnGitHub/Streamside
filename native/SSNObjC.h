#pragma once
#include <objc/message.h>
#include <objc/runtime.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
extern id objc_retain(id);
extern void objc_release(id);
typedef struct { double x,y,width,height; } SSNRect;
typedef struct { double top,left,bottom,right; } SSNInsets;
static inline SEL ss(const char *s) { return sel_registerName(s); }
static inline id c(const char *name) { return (id)objc_getClass(name); }
static inline id m0(id o,const char *s) { return ((id(*)(id,SEL))objc_msgSend)(o,ss(s)); }
static inline id m1(id o,const char *s,id a) { return ((id(*)(id,SEL,id))objc_msgSend)(o,ss(s),a); }
static inline void v0(id o,const char *s) { ((void(*)(id,SEL))objc_msgSend)(o,ss(s)); }
static inline void v1(id o,const char *s,id a) { ((void(*)(id,SEL,id))objc_msgSend)(o,ss(s),a); }
static inline id ns(const char *s) { return m1(c("NSString"),"stringWithUTF8String:",(id)s); }
static inline bool kind(id o,const char *name) { return o&&((BOOL(*)(id,SEL,Class))objc_msgSend)(o,ss("isKindOfClass:"),objc_getClass(name)); }
static inline bool responds(id o,const char *name) { return ((BOOL(*)(id,SEL,SEL))objc_msgSend)(o,ss("respondsToSelector:"),ss(name)); }
static inline uintptr_t num(id o,const char *s) { return ((uintptr_t(*)(id,SEL))objc_msgSend)(o,ss(s)); }
static inline id at(id a,uintptr_t i) { return ((id(*)(id,SEL,uintptr_t))objc_msgSend)(a,ss("objectAtIndex:"),i); }
static inline void put(id d,const char *key,id value) { if(value) ((void(*)(id,SEL,id,id))objc_msgSend)(d,ss("setObject:forKey:"),value,ns(key)); }
static inline id get(id d,const char *key) { return m1(d,"objectForKey:",ns(key)); }
static inline bool method_is(Class cls,const char *selector,const char *encoding,bool meta) {
    Method m=meta?class_getClassMethod(cls,ss(selector)):class_getInstanceMethod(cls,ss(selector));
    return m && !strcmp(method_getTypeEncoding(m),encoding);
}
