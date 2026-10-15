#ifndef TAS_CHAT_TRACE_H
#define TAS_CHAT_TRACE_H
#include "TASDiagnosticPolicy.h"
#include <stddef.h>
#include <stdbool.h>
#ifndef TAS_CHAT_TRACE_DIAGNOSTIC
#define TAS_CHAT_TRACE_DIAGNOSTIC 0
#endif
#if TAS_CHAT_TRACE_DIAGNOSTIC
bool tas_chat_trace_packet(const char *packet);
void tas_chat_trace_status(char *buffer,size_t capacity);
#else
static inline bool tas_chat_trace_packet(const char *p){(void)p;return false;}
static inline void tas_chat_trace_status(char *b,size_t n){if(n)b[0]=0;}
#endif
#endif
