#pragma once
#include "SSNSwiftABI.h"
/* Owned adapter. All returned Swift storage remains opaque and runtime-owned. */
const void *ssn_feed_promise_type(PairMeta promise,const void *error);
void ssn_feed_request(void *out,id graph);
id SW ssn_feed_map(const void *value,void *context CTX);
id ssn_user_dictionary(const void *value);
