#pragma once
#include <objc/objc.h>
#include "SSNProfileDiagnostics.h"
id ssn_profile_request(id channel,unsigned operation,id setting);
id ssn_profile_unbox(id object);
id ssn_profile_notification_string(id object); // retained
id ssn_profile_normalize(id object);
