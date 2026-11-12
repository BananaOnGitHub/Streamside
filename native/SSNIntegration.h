#pragma once
#include "SSNObjC.h"
void *ssn_resolve(const char *name);
void ssn_integration_start(void);
void ssn_ui_attach(id window);
void ssn_ui_changed(void);
void ssn_account_refresh(void);
bool ssn_account_refreshing(void);
id ssn_account_info(void);
id ssn_followed_channels(void);
void ssn_account_changed(void);

/* Validated Objective-C adapter; donor owns the Swift account dispatch. */
id ssn_logout_target(void);
