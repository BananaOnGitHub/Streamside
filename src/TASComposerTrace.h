#ifndef TAS_COMPOSER_TRACE_H
#define TAS_COMPOSER_TRACE_H
#include <objc/objc.h>
#include <stddef.h>
#ifndef TAS_RN_COMPOSER_DIAGNOSTIC
#define TAS_RN_COMPOSER_DIAGNOSTIC 0
#endif
enum { TAS_CT_LAYOUT=1,TAS_CT_EDIT_PRE,TAS_CT_EDIT_POST,TAS_CT_CHANGE_PRE,TAS_CT_CHANGE_POST,
       TAS_CT_SELECT_PRE,TAS_CT_SELECT_POST,TAS_CT_VALUE_PRE,TAS_CT_VALUE_POST,
       TAS_CT_WINDOW,TAS_CT_SHEET_OPEN,TAS_CT_POLL,TAS_CT_KEYBOARD,
       TAS_CT_SHEET_CLOSED=14,TAS_CT_SHEET_READY=15,TAS_CT_JS_STATE=20,TAS_CT_JS_SURFACE,TAS_CT_JS_STRIP,TAS_CT_JS_INPUT,TAS_CT_JS_UNMOUNT };
#if TAS_RN_COMPOSER_DIAGNOSTIC
#include "TASDiagnosticPolicy.h"
void tas_composer_trace_native(id owner,id editor,unsigned event);
#define TAS_CT_CAPTURE(owner,editor,event) do { if(tas_diag_wants(TAS_DIAG_COMPOSER,TAS_DIAG_DETAILED)) tas_composer_trace_native(owner,editor,event); } while(0)
void tas_composer_trace_js(unsigned event,unsigned session,double x,double y,double width,double height);
void tas_composer_trace_report(char *buffer,size_t capacity);
void tas_composer_trace_clear(void);
void tas_composer_trace_sheet_closed(void);
#else
#define TAS_CT_CAPTURE(owner,editor,event) ((void)0)
static inline void tas_composer_trace_native(id owner,id editor,unsigned event){(void)owner;(void)editor;(void)event;}
static inline void tas_composer_trace_js(unsigned event,unsigned session,double x,double y,double w,double h){(void)event;(void)session;(void)x;(void)y;(void)w;(void)h;}
static inline void tas_composer_trace_clear(void){}
static inline void tas_composer_trace_sheet_closed(void){}
#endif
#endif
