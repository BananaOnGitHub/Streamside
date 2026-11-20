#pragma once
#include <stdint.h>
#include <objc/objc.h>
#if !__has_attribute(swiftcall) || !__has_attribute(swift_context) || !__has_attribute(swift_indirect_result)
#error Clang Swift ABI support is required
#endif
#define SW __attribute__((swiftcall))
#define CTX __attribute__((swift_context))
#define OUT __attribute__((swift_indirect_result))
typedef struct { const void *value; uintptr_t state; } Response;
typedef struct { uintptr_t a,b; } Words2;
typedef struct { uintptr_t a,b,c; } Words3;
typedef SW Response (*Meta)(uintptr_t);
typedef SW Response (*GenericMeta)(uintptr_t,const void*);
typedef SW Response (*PairMeta)(uintptr_t,const void*,const void*);
typedef SW void (*Getter)(void * OUT,const void * CTX);
typedef SW Words2 (*StringGetter)(const void * CTX);
typedef SW id (*Map)(const void*,void * CTX);
typedef SW id (*Bridge)(const void*,const void*);
typedef SW id (*PromiseObjC)(Map,void*,Map,void*,const void*,const void*,const void*,const void * CTX);
typedef SW void (*CurrentRequest)(void * OUT,id CTX);
typedef SW void (*FollowRequest)(void * OUT,intptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,id CTX);
typedef SW void (*Destroy)(void*,const void*);
typedef SW unsigned (*GetTag)(const void*,unsigned,const void*);
typedef SW void (*StoreTag)(void*,unsigned,unsigned,const void*);

/* Inspected Twitch 32 feed ABI; all use swiftcall, not guessed C layouts. */
typedef SW void (*PersonalRequest)(void * OUT,uintptr_t,uintptr_t,uint8_t,uintptr_t,id CTX);
typedef SW uintptr_t (*SectionsGetter)(uintptr_t,uintptr_t);
typedef SW void (*ItemGetter)(void * OUT,const void*,const void * CTX);
typedef SW Words3 (*ThumbnailsGetter)(const void * CTX);
typedef SW void (*ThumbnailGetter)(void * OUT,uint8_t,uintptr_t,uintptr_t,uintptr_t);
typedef SW uintptr_t (*ArrayGetter)(const void * CTX);
typedef SW intptr_t (*IntegerGetter)(const void * CTX);
typedef SW uint8_t (*BoolGetter)(const void * CTX);

/* Twitch 32 generated query and native Apollo convenience overload. Verified
 * direct value lowering; the client is two words, not a Swift object layout. */
typedef SW Words2 (*ApolloClientGetter)(id CTX);
typedef SW uintptr_t (*PlaybackParamsInit)(uintptr_t,uint8_t,uint8_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uint8_t);
typedef SW uintptr_t (*PlaybackQueryInit)(uintptr_t,uintptr_t,uintptr_t,const void * CTX);
typedef SW void (*PlaybackFetch)(void * OUT,uintptr_t,uint8_t,uintptr_t,uintptr_t,const void*,const void*);
typedef SW uintptr_t (*PlaybackField)(uintptr_t);
typedef SW Words2 (*PlaybackString)(uintptr_t);

/* CCL query consumes String X0/X1, metatype swiftself X20. */
typedef SW uintptr_t (*LabelsQueryInit)(uintptr_t,uintptr_t,const void * CTX);

/* Twitch 32 generated profile and native mutation adapters. */
typedef SW Response (*Meta3)(uintptr_t,const void*,const void*,const void*);
typedef SW Response (*PackedMeta)(uintptr_t,const void*const*);
typedef SW void (*NilValue)(void* OUT,const void*);
typedef SW uintptr_t (*ProfileInit)(uintptr_t,uintptr_t,uint8_t,uintptr_t,uint8_t,uintptr_t,uint8_t,const void* CTX);
typedef SW uintptr_t (*FollowInput)(uint8_t,uintptr_t,uintptr_t);
typedef SW uintptr_t (*NotifyInput)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uint8_t);
typedef SW void (*EnumInit)(void* OUT,uintptr_t,uintptr_t,const void*,const void*);
typedef SW void (*Unwrap)(void* OUT,const void*,const void* CTX);
typedef SW void (*MutationMap)(void* OUT,const void*,void* CTX);
typedef SW void (*Perform)(void* OUT,uintptr_t,id,MutationMap,void*,uintptr_t,uintptr_t,const void*,const void*,const void*,const void*,const void*);
