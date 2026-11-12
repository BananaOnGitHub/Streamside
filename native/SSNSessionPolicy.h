#pragma once
#include <stdbool.h>
/* Notification indices match the exact inspected TwitchIdentity name getters.
 * Information/availability may repeat on restoration; credentials are boundaries.
 * Unknown events fail closed. No token contents or account layouts are inspected. */
enum { SSN_USER_UPDATED, SSN_USER_AVAILABLE, SSN_USER_LOGIN, SSN_USER_LOGOUT, SSN_USER_TOKEN_CHANGED, SSN_ACCOUNT_EVENT_COUNT };
static inline bool ssn_preserve_account_event(unsigned event,bool same_verified_authorization) {
    return same_verified_authorization && (event==SSN_USER_UPDATED || event==SSN_USER_AVAILABLE);
}
