#ifndef TAS_RN_COMPOSER_UI_H
#define TAS_RN_COMPOSER_UI_H
#include <objc/objc.h>
#include <stdint.h>
#include <stddef.h>
void tas_rn_composer_ui_retry_hooks(void);
void tas_rn_composer_ui_image(uint64_t number,id data,id response,id error);
void tas_rn_composer_ui_status(char *buffer,size_t capacity);
#endif
