#ifndef SS_COMPOSER_H
#define SS_COMPOSER_H
#include <stddef.h>
void ss_composer_retry_hooks(void);
void ss_composer_status(char *buffer, size_t capacity);
/* 0 automatic, 1 colon, 2 off; takes effect immediately. */
int ss_composer_suggestion_mode(void);
void ss_composer_set_suggestion_mode(int mode);
#endif
