#pragma once
#include <objc/objc.h>
#include <stdint.h>
#include <stdbool.h>
#include "SSNProfileDiagnostics.h"
id ssn_profile_request(id channel,unsigned operation,id setting);
id ssn_profile_avatar_request(uint32_t user_id);
id ssn_chat_send_request(id channel,id message);
id ssn_chat_cheer_request(id channel,bool global);
id ssn_chat_send_result(id object); // retained
id ssn_profile_unbox(id object);
id ssn_profile_notification_string(id object); // retained
id ssn_profile_normalize(id object);
id ssn_profile_unbox_panel(id object); // retained
id ssn_profile_unbox_panel_list(id object); // retained
unsigned ssn_profile_panel_stage(id result);
