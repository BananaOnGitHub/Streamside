#include "TASInvestigation.h"
#include "TASInvestigationRegistry.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void) {
    TASInvManifest out,zero={0};
    assert(tas_inv_parse(tas_inv_manifest_bytes,sizeof(tas_inv_manifest_bytes),&out));
    unsigned char input[TAS_INV_MANIFEST_BYTES];unsigned random=1;
    for(unsigned trial=0;trial<20000;trial++) {
        size_t n=trial%3?sizeof(tas_inv_manifest_bytes):(trial%TAS_INV_MANIFEST_BYTES);
        memcpy(input,tas_inv_manifest_bytes,n<sizeof(tas_inv_manifest_bytes)?n:sizeof(tas_inv_manifest_bytes));
        for(size_t i=sizeof(tas_inv_manifest_bytes);i<n;i++)input[i]=' ';
        for(unsigned k=0;k<1+trial%8&&n;k++){random=random*1664525U+1013904223U;size_t at=random%n;random=random*1664525U+1013904223U;input[at]=(unsigned char)(random>>24);}
        memset(&out,0xa5,sizeof(out));
        if(!tas_inv_parse(input,n,&out))assert(!memcmp(&out,&zero,sizeof(out)));
    }
    puts("20,000 bounded malformed/truncated manifest cases passed under sanitizers");
    return 0;
}
