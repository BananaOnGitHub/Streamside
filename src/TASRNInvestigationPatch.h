#ifndef TAS_RN_INVESTIGATION_PATCH_H
#define TAS_RN_INVESTIGATION_PATCH_H
#include "TASInvestigation.h"
#include "TASRNInvestigationFunctionalPayload.h"
#include "TASRNInvestigationOriginalPayload.h"
#include "TASRNStripPatch.h"
typedef struct {
    uint32_t old_offset, new_offset, old_size, old_width, opcode, target;
} TASInvBranch;
#include "TASRNInvestigationLayout.h"

/* Only the exact original or complete five-stage predecessor is admitted.
 * The existing ChatMessageList memo/export and React hook sequence are retained.
 * Startup adds one factory environment slot and a scoped JSX/ref seam. */
static inline bool tas_inv_inner_copy(unsigned char *out, const unsigned char *input) {
    size_t source = 0, target = 0, branch = 0;
    bool inserted = false;
    const size_t count = sizeof(tas_inv_branches) / sizeof(tas_inv_branches[0]);
    while (source < TAS_INV_INNER_OLD_SIZE) {
        if (source == TAS_INV_INNER_JOIN && !inserted) {
            memcpy(out + target, tas_inv_inner_extra, sizeof(tas_inv_inner_extra));
            target += sizeof(tas_inv_inner_extra);
            inserted = true;
        }
        if (branch < count && tas_inv_branches[branch].old_offset == source) {
            const TASInvBranch *b = &tas_inv_branches[branch++];
            if (target != b->new_offset)
                return false;
            out[target] = (unsigned char)b->opcode;
            int32_t distance = (int32_t)b->target - (int32_t)target;
            memcpy(out + target + 1, &distance, 4);
            size_t tail = b->old_size - 1 - b->old_width;
            memcpy(out + target + 5, input + source + 1 + b->old_width, tail);
            target += 5 + tail;
            source += b->old_size;
        } else {
            size_t end =
                branch < count ? tas_inv_branches[branch].old_offset : TAS_INV_INNER_OLD_SIZE;
            if (!inserted && end > TAS_INV_INNER_JOIN)
                end = TAS_INV_INNER_JOIN;
            if (end <= source)
                return false;
            memcpy(out + target, input + source, end - source);
            target += end - source;
            source = end;
        }
    }
    return inserted && target == TAS_INV_INNER_NEW_SIZE;
}
static inline unsigned char *tas_rn_investigation_patch(const unsigned char *body, size_t length,
                                                        TASRNSHA1 sha1, TASInvSHA256 sha256,
                                                        size_t *result_length) {
    if (result_length)
        *result_length = 0;
    if (!body || !sha1 || !sha256 || !result_length || length < 128)
        return NULL;
    unsigned char digest[32];
    const unsigned char *payload = NULL;
    const uint32_t *infos = NULL;
    size_t payload_size = 0;
    uint32_t base = 0, added = 0;
    const unsigned char *expected = NULL;
    if (length == TAS_INV_ORIGINAL_SIZE) {
        base = TAS_RN_INV_ORIGINAL_BASE;
        added = TAS_RN_INV_ORIGINAL_FUNCTIONS;
        payload = tas_rn_inv_original_payload;
        payload_size = sizeof(tas_rn_inv_original_payload);
        infos = tas_rn_inv_original_infos;
        expected = tas_inv_original_sha256;
    } else if (length == TAS_INV_FUNCTIONAL_SIZE) {
        base = TAS_RN_INV_FUNCTIONAL_BASE;
        added = TAS_RN_INV_FUNCTIONAL_FUNCTIONS;
        payload = tas_rn_inv_functional_payload;
        payload_size = sizeof(tas_rn_inv_functional_payload);
        infos = tas_rn_inv_functional_infos;
        expected = tas_inv_functional_sha256;
    } else
        return NULL;
    if (tas_rn_u32(body + 32) != length || tas_rn_u32(body + 40) != base ||
        !sha256(body, length, digest) || memcmp(digest, expected, 32) ||
        !sha1(body, (uint32_t)length - 20, digest) || memcmp(digest, body + length - 20, 20))
        return NULL;
    const size_t table_end = 128U + base * 12U, delta = added * 12U;
    size_t old_info[2], old_start[2];
    const uint32_t ids[2] = {4900, 22318};
    for (unsigned k = 0; k < 2; k++) {
        const unsigned char *header = body + 128U + ids[k] * 12U;
        if (header[11] != 32)
            return NULL;
        old_info[k] = (tas_rn_u32(header) & 0xffffffU) | ((tas_rn_u32(header + 4) >> 14) << 24);
        if (old_info[k] > length - 60)
            return NULL;
        old_start[k] = tas_rn_u32(body + old_info[k]);
        if (body[old_info[k] + 36] & 24)
            return NULL;
    }
    if (tas_rn_u32(body + old_info[0] + 12) != 382 || tas_rn_u32(body + old_info[0] + 28) != 22 ||
        body[old_start[0]] != 64 || body[old_start[0] + 2] != 19 ||
        tas_rn_u32(body + old_info[1] + 12) != TAS_INV_INNER_OLD_SIZE ||
        tas_rn_u32(body + old_info[1] + 28) != 91)
        return NULL;
    const unsigned char factory_extra[] = {132, 6, 1,  base & 255, base >> 8, 108, 6,   6, 1,
                                           55,  3, 19, 6,          174,       4,   119, 6};
    const size_t payload_start = (length - 20 + delta + 3) & ~(size_t)3;
    const size_t factory_start = payload_start + payload_size,
                 factory_info = (factory_start + 382 + sizeof(factory_extra) + 3) & ~(size_t)3;
    const size_t inner_start = factory_info + 40 + 16,
                 inner_info = (inner_start + TAS_INV_INNER_NEW_SIZE + 3) & ~(size_t)3,
                 count = inner_info + 40 + 20;
    unsigned char *copy = calloc(1, count);
    if (!copy)
        return NULL;
    memcpy(copy, body, table_end);
    memcpy(copy + table_end + delta, body + table_end, length - 20 - table_end);
    for (unsigned i = 0; i < base; i++) {
        const unsigned char *old = body + 128U + i * 12U;
        unsigned char *header = copy + 128U + i * 12U;
        uint32_t word = tas_rn_u32(old), offset = word & 0x01ffffffU;
        if (old[11] & 32) {
            uint32_t info = (word & 0xffffffU) | ((tas_rn_u32(old + 4) >> 14) << 24);
            if (info < table_end || info > length - 60)
                goto refused;
            uint32_t start = tas_rn_u32(body + info), size = tas_rn_u32(body + info + 12);
            if (start < table_end || start > length - 20 || size > length - 20 - start)
                goto refused;
            tas_rn_put32(copy + info + delta, start + (uint32_t)delta);
            info += (uint32_t)delta;
            tas_rn_put32(header, info & 0xffffffU);
            tas_rn_put32(header + 4, (info >> 24) << 14);
        } else {
            if (offset < table_end || offset > length - 20 || offset + delta >= 0x02000000U)
                goto refused;
            tas_rn_put32(header, (word & 0xfe000000U) | (offset + (uint32_t)delta));
        }
    }
    tas_rn_put32(copy + 108, tas_rn_u32(body + 108) + (uint32_t)delta);
    memcpy(copy + payload_start, payload, payload_size);
    for (unsigned i = 0; i < added; i++) {
        uint32_t info = (uint32_t)payload_start + infos[i];
        unsigned char *header = copy + table_end + i * 12U;
        tas_rn_put32(header, info & 0xffffffU);
        tas_rn_put32(header + 4, (info >> 24) << 14);
        header[11] = 32;
        tas_rn_put32(copy + info, tas_rn_u32(copy + info) + (uint32_t)payload_start);
    }
    memcpy(copy + factory_start, body + old_start[0], 0x116);
    memcpy(copy + factory_start + 0x116, factory_extra, sizeof(factory_extra));
    memcpy(copy + factory_start + 0x116 + sizeof(factory_extra), body + old_start[0] + 0x116,
           382 - 0x116);
    copy[factory_start + 2] = 20;
    memcpy(copy + factory_info, body + old_info[0], 40);
    tas_rn_put32(copy + factory_info, (uint32_t)factory_start);
    tas_rn_put32(copy + factory_info + 12, 382 + sizeof(factory_extra));
    tas_rn_put32(copy + factory_info + 28, 33);
    copy[factory_info + 36] |= 8;
    tas_rn_put32(copy + factory_info + 40, 1);
    tas_rn_put32(copy + factory_info + 44, 0x116);
    tas_rn_put32(copy + factory_info + 48, 0x116 + 13);
    tas_rn_put32(copy + factory_info + 52, 0x116 + 15);
    if (!tas_inv_inner_copy(copy + inner_start, body + old_start[1]))
        goto refused;
    memcpy(copy + inner_info, body + old_info[1], 40);
    tas_rn_put32(copy + inner_info, (uint32_t)inner_start);
    tas_rn_put32(copy + inner_info + 12, TAS_INV_INNER_NEW_SIZE);
    for (unsigned k = 0; k < 2; k++) {
        uint32_t info = (uint32_t)(k ? inner_info : factory_info);
        unsigned char *header = copy + 128U + ids[k] * 12U;
        memset(header, 0, 12);
        tas_rn_put32(header, info & 0xffffffU);
        tas_rn_put32(header + 4, (info >> 24) << 14);
        header[11] = 32;
    }
    tas_rn_put32(copy + 40, base + added);
    tas_rn_put32(copy + 32, (uint32_t)count);
    if (!sha1(copy, (uint32_t)count - 20, copy + count - 20))
        goto refused;
    *result_length = count;
    return copy;
refused:
    free(copy);
    return NULL;
}
#endif
