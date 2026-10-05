"""Read-only container metadata parsing, including adversarial lengths."""
import unittest
import test_composer as composer

MODEL = r'''
#include <assert.h>
#include "TASEmoteWire.h"
static void u32(unsigned char *p,uint32_t n) { for (unsigned i=0;i<4;i++) p[i]=(unsigned char)(n>>(i*8)); }
int main(void) {
    unsigned char gif[40]={'G','I','F','8','9','a',1,0,1,0,0,0,0};
    unsigned char image[]={0x2c,0,0,0,0,1,0,1,0,0,2,1,0,0};
    memcpy(gif+13,image,sizeof(image));gif[27]=0x3b;
    TASWireInfo r=tas_wire_info(gif,28);assert(r.complete && r.frames==1 && !r.animated);
    unsigned char animated[42];memcpy(animated,gif,27);memcpy(animated+27,image,14);animated[41]=0x3b;
    r=tas_wire_info(animated,sizeof(animated));assert(r.complete && r.frames==2 && r.animated);
    for (size_t i=0;i<sizeof(animated);i++) assert(!tas_wire_info(animated,i).complete);
    gif[10]=255;assert(!tas_wire_info(gif,28).complete);
    unsigned char webp[76]={0};memcpy(webp,"RIFF",4);memcpy(webp+8,"WEBP",4);
    memcpy(webp+12,"VP8L",4);u32(webp+16,1);webp[20]=1;u32(webp+4,14);
    r=tas_wire_info(webp,22);assert(r.complete && r.frames==1 && !r.animated);
    memset(webp+12,0,64);memcpy(webp+12,"VP8X",4);u32(webp+16,10);webp[20]=2;
    memcpy(webp+30,"ANIM",4);u32(webp+34,6);memcpy(webp+44,"ANMF",4);u32(webp+48,16);u32(webp+4,60);
    r=tas_wire_info(webp,68);assert(r.complete && r.frames==1 && r.animated);
    for (size_t i=0;i<68;i++) assert(!tas_wire_info(webp,i).complete);
    webp[20]=0;assert(!tas_wire_info(webp,68).complete);webp[20]=2;
    u32(webp+48,UINT32_MAX);assert(!tas_wire_info(webp,68).complete);
    assert(!tas_wire_info(NULL,SIZE_MAX).complete);
    /* Many bounded malformed inputs exercise every prefix under sanitizers. */
    unsigned char fuzz[128];uint32_t seed=1;
    for (unsigned k=0;k<10000;k++) {
        for (unsigned i=0;i<128;i++) { seed=seed*1664525U+1013904223U;fuzz[i]=(unsigned char)(seed>>24); }
        if (k%3==0) memcpy(fuzz,"GIF89a",6);
        if (k%3==1) { memcpy(fuzz,"RIFF",4);memcpy(fuzz+8,"WEBP",4);u32(fuzz+4,120); }
        r=tas_wire_info(fuzz,k%129);assert(r.frames>=-1 && r.animated>=-1 && r.animated<=1);
    }
    return 0;
}
'''

class WireMetadataTests(unittest.TestCase):
    def test_gif_webp_metadata_truncation_overflow_and_fuzz(self):
        composer.ComposerTests().compile_run(MODEL, ["cc", "-std=c11", "-fsanitize=address,undefined"])

if __name__ == "__main__":
    unittest.main()
