#pragma once
#include "SSNSwiftABI.h"
/* ARC callers must consume the retained result. In plain C, id is the runtime
 * typedef and Clang rejects Objective-C ownership attributes on it. */
#ifdef __OBJC__
#define SSN_PLAYBACK_RETAINED __attribute__((ns_returns_retained))
#else
#define SSN_PLAYBACK_RETAINED
#endif
/* Main thread only. Retained TWLPromise, containing only a private media-token
 * dictionary. Neither this promise nor its contents may enter SwiftUI/reports. */
id ssn_playback_request(id channel) SSN_PLAYBACK_RETAINED;
/* Same inspected constructor/lowering; limited native VAFT player/platform pairs. */
id ssn_playback_request_variant(id channel,id player,id platform) SSN_PLAYBACK_RETAINED;
bool ssn_playback_authorized(void);

#undef SSN_PLAYBACK_RETAINED
