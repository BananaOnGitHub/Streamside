#pragma once
#include "SSNSwiftABI.h"
/* Main thread only. Retained TWLPromise, containing only a private media-token
 * dictionary. Neither this promise nor its contents may enter SwiftUI/reports. */
id ssn_playback_request(id channel) __attribute__((ns_returns_retained));
/* Same inspected constructor/lowering; limited native VAFT player/platform pairs. */
id ssn_playback_request_variant(id channel,id player,id platform) __attribute__((ns_returns_retained));
bool ssn_playback_authorized(void);
