/* Deterministic policy fixtures. Provider policy shapes sampled from public
 * image GET responses on 2026-10-09; identities, URLs and bodies omitted.
 * @now/@future/@expiry are generated relative to the fixture's wall clock.
 * This matrix drives the production annotation callback, not a second parser. */
typedef struct {
    const char *name,*control,*date,*expires,*age;
    unsigned rejection;
} AnnotationCase;
static const AnnotationCase annotation_cases[]={
    {"7TV policy", "public, max-age=31536000, s-maxage=86400, immutable", "@now", NULL, "63726", IMAGE_CACHE_ACCEPTED},
    {"BTTV repeated field combined", "max-age=15552000, public,max-age=15552000,immutable", "@now", "@expiry", "22945", IMAGE_CACHE_MAX_AGE_DUPLICATE},
    {"FFZ policy", "public, max-age=86400", "@now", NULL, "3948", IMAGE_CACHE_ACCEPTED},
    {"Expires only", NULL, "@now", "@expiry", NULL, IMAGE_CACHE_ACCEPTED},
    {"private explicit expiry", "private", "@now", "@expiry", NULL, IMAGE_CACHE_ACCEPTED},
    {"quoted and mixed case", " MAX-AGE = \"3600\" , immutable", "@now", NULL, "1", IMAGE_CACHE_ACCEPTED},
    {"max-age precedes invalid Expires", "max-age=3600", "@now", "bad", NULL, IMAGE_CACHE_ACCEPTED},
    {"fresh must-revalidate", "public, max-age=3600, must-revalidate", "@now", NULL, NULL, IMAGE_CACHE_ACCEPTED},
    {"well-formed stale extensions", "max-age=3600, stale-while-revalidate=30, stale-if-error=60", "@now", NULL, NULL, IMAGE_CACHE_ACCEPTED},
    {"missing Date", "max-age=3600", NULL, NULL, NULL, IMAGE_CACHE_DATE_MISSING},
    {"empty Date", "max-age=3600", "", NULL, NULL, IMAGE_CACHE_DATE_INVALID},
    {"obsolete Date", "max-age=3600", "Sunday, 06-Nov-94 08:49:37 GMT", NULL, NULL, IMAGE_CACHE_DATE_INVALID},
    {"wrong weekday", "max-age=3600", "Mon, 06 Nov 1994 08:49:37 GMT", NULL, NULL, IMAGE_CACHE_DATE_INVALID},
    {"future Date", "max-age=3600", "@future", NULL, NULL, IMAGE_CACHE_DATE_FUTURE},
    {"invalid Age", "max-age=3600", "@now", NULL, "invalid", IMAGE_CACHE_AGE_INVALID},
    {"Age overflow", "max-age=3600", "@now", NULL, "2147483648", IMAGE_CACHE_AGE_INVALID},
    {"empty Age", "max-age=3600", "@now", NULL, "", IMAGE_CACHE_AGE_INVALID},
    {"invalid max-age", "max-age=bad", "@now", NULL, NULL, IMAGE_CACHE_MAX_AGE_INVALID},
    {"max-age overflow", "max-age=2147483648", "@now", NULL, NULL, IMAGE_CACHE_MAX_AGE_INVALID},
    {"conflicting max-age", "max-age=3600, max-age=60", "@now", NULL, NULL, IMAGE_CACHE_MAX_AGE_DUPLICATE},
    {"no-cache", "max-age=3600, no-cache", "@now", NULL, NULL, IMAGE_CACHE_NO_CACHE},
    {"qualified no-cache", "no-cache=\"ETag\", max-age=3600", "@now", NULL, NULL, IMAGE_CACHE_NO_CACHE},
    {"no-store", "max-age=3600, no-store", "@now", NULL, NULL, IMAGE_CACHE_NO_STORE},
    {"invalid extension delta", "max-age=3600, s-maxage=bad", "@now", NULL, NULL, IMAGE_CACHE_EXTENSION_INVALID},
    {"qualified private", "max-age=3600, private=\"Content-Type\"", "@now", NULL, NULL, IMAGE_CACHE_DIRECTIVE_UNSUPPORTED},
    {"unknown extension", "max-age=3600, x-unknown=1", "@now", NULL, NULL, IMAGE_CACHE_DIRECTIVE_UNSUPPORTED},
    {"trailing comma", "max-age=3600,", "@now", NULL, NULL, IMAGE_CACHE_DIRECTIVE_UNSUPPORTED},
    {"missing Expires/heuristic", NULL, "@now", NULL, NULL, IMAGE_CACHE_EXPIRES_MISSING},
    {"invalid Expires", NULL, "@now", "bad", NULL, IMAGE_CACHE_EXPIRES_INVALID},
    {"zero freshness", "max-age=0, must-revalidate", "@now", NULL, NULL, IMAGE_CACHE_LIFETIME_INVALID},
    {"nonpositive Expires", NULL, "@now", "@now", NULL, IMAGE_CACHE_LIFETIME_INVALID},
    {"Date checked before duplicate", "max-age=1, max-age=2", "bad", NULL, "bad", IMAGE_CACHE_DATE_INVALID},
    {"duplicate checked before Age", "max-age=1, max-age=2", "@now", NULL, "bad", IMAGE_CACHE_MAX_AGE_DUPLICATE}
};
