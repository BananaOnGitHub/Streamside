#include "TASPrivacy.h"

#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAS_LABEL_SLOTS 512
#define TAS_MAX_LABEL_KEY 8192

typedef struct {
    char *key;
    uint64_t identifier;
} TASLabel;

static TASLabel g_channels[TAS_LABEL_SLOTS];
static TASLabel g_resources[TAS_LABEL_SLOTS];
static size_t g_next_channel;
static size_t g_next_resource;
static pthread_mutex_t g_label_lock = PTHREAD_MUTEX_INITIALIZER;

extern uint32_t arc4random_uniform(uint32_t upper_bound);

static uint64_t random_identifier(TASLabel *entries) {
    uint64_t value;
    bool collision;
    do {
        value = ((uint64_t)arc4random_uniform(UINT32_MAX) << 32) |
                arc4random_uniform(UINT32_MAX);
        collision = value == 0;
        for (size_t i = 0; i < TAS_LABEL_SLOTS && !collision; i++) {
            collision = entries[i].key && entries[i].identifier == value;
        }
    } while (collision);
    return value;
}

static void label(const char *key, const char *kind, TASLabel *entries,
                  size_t *next, char *output, size_t capacity) {
    if (!output || !capacity) return;
    if (!key || !key[0]) {
        snprintf(output, capacity, "%s-none", kind);
        return;
    }
    size_t length = 0;
    while (length <= TAS_MAX_LABEL_KEY && key[length]) length++;
    if (length > TAS_MAX_LABEL_KEY) {
        snprintf(output, capacity, "%s-oversize", kind);
        return;
    }
    pthread_mutex_lock(&g_label_lock);
    size_t slot = TAS_LABEL_SLOTS;
    for (size_t i = 0; i < TAS_LABEL_SLOTS; i++) {
        if (entries[i].key && strcmp(entries[i].key, key) == 0) {
            slot = i;
            break;
        }
        if (slot == TAS_LABEL_SLOTS && !entries[i].key) slot = i;
    }
    if (slot == TAS_LABEL_SLOTS) slot = (*next)++ % TAS_LABEL_SLOTS;
    if (!entries[slot].key || strcmp(entries[slot].key, key) != 0) {
        char *copy = strdup(key);
        if (!copy) {
            pthread_mutex_unlock(&g_label_lock);
            snprintf(output, capacity, "%s-unavailable", kind);
            return;
        }
        free(entries[slot].key);
        entries[slot].key = copy;
        entries[slot].identifier = random_identifier(entries);
    }
    snprintf(output, capacity, "%s-%016llx", kind,
             (unsigned long long)entries[slot].identifier);
    pthread_mutex_unlock(&g_label_lock);
}

void tas_label_channel(const char *channel, char *output, size_t capacity) {
    label(channel, "channel", g_channels, &g_next_channel, output, capacity);
}

void tas_label_url(const char *url, char *output, size_t capacity) {
    /* Only a label leaves this function. Full URLs stay in process memory. */
    label(url, url && strstr(url, ".m3u8") ? "playlist" : "resource",
          g_resources, &g_next_resource, output, capacity);
}
