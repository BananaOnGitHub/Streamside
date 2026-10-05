#ifndef TAS_EMOTE_IMAGE_PROBE_H
#define TAS_EMOTE_IMAGE_PROBE_H
#include "TASEmoteProbe.h"
#include <objc/runtime.h>
#if TAS_EMOTE_DIAGNOSTIC
void tas_image_probe_install(void);
void tas_image_probe_response(uint64_t number,id data);
void tas_image_probe_origin(id image,char *buffer,size_t capacity);
void tas_image_probe_assignment(uint64_t number,unsigned layer,id image,const char *decision);
void tas_image_probe_status(char *buffer,size_t capacity);
const char *tas_image_probe_caller(void *address);
#endif
#endif
