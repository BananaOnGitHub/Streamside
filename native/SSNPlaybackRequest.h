#pragma once
#include "SSNSwiftABI.h"
/* Main thread only. Retained TWLPromise, containing only a private media-token
 * dictionary. Neither this promise nor its contents may enter SwiftUI/reports. */
id ssn_playback_request(id channel);
bool ssn_playback_authorized(void);
