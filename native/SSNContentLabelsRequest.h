#pragma once
#include "SSNSwiftABI.h"
/* Main thread; +1 native promise of localized, enabled CCL names only. */
#ifdef __OBJC__
id ssn_content_labels_request(id channel) __attribute__((ns_returns_retained));
#else
id ssn_content_labels_request(id channel);
#endif
