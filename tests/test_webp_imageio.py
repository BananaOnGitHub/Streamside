"""Real ImageIO WebP decode on Apple hosts; does not claim iOS UI acceptance."""
import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
@unittest.skipUnless(platform.system()=='Darwin' and shutil.which('xcrun'),'Apple ImageIO/Xcode required')
class AppleWebPTests(unittest.TestCase):
    def test_animation_count_canvas_and_lossless_frame_pixels(self):
        source=r'''
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <CoreGraphics/CoreGraphics.h>
#include <assert.h>
#include "webp_fixture.h"
int main(void){@autoreleasepool{
 for(unsigned fixture=0;fixture<2;fixture++){
 NSData *data=[NSData dataWithBytes:fixture?webp_alpha:webp_pixels length:fixture?sizeof(webp_alpha):sizeof(webp_pixels)];
 NSDictionary *options=@{(id)kCGImageSourceShouldCache:@NO};
 CGImageSourceRef source=CGImageSourceCreateWithData((__bridge CFDataRef)data,(__bridge CFDictionaryRef)options);
 assert(source && CGImageSourceGetCount(source)==3);
 const unsigned char expected[3][3]={{255,0,0},{0,128,0},{0,0,255}};
 for(size_t i=0;i<3;i++){
  CGImageRef frame=CGImageSourceCreateImageAtIndex(source,i,(__bridge CFDictionaryRef)options);
  assert(frame && CGImageGetWidth(frame)==4 && CGImageGetHeight(frame)==3);
  unsigned char rgba[4*3*4]={0};CGColorSpaceRef cs=CGColorSpaceCreateDeviceRGB();
  CGContextRef ctx=CGBitmapContextCreate(rgba,4,3,8,16,cs,kCGImageAlphaPremultipliedLast|kCGBitmapByteOrder32Big);
  CGContextDrawImage(ctx,CGRectMake(0,0,4,3),frame);
  if(!fixture){for(unsigned pixel=0;pixel<12;pixel++){for(unsigned c=0;c<3;c++)assert(rgba[pixel*4+c]==expected[i][c]);assert(rgba[pixel*4+3]==255);}}
  else {
   unsigned sums[4]={0};for(unsigned pixel=0;pixel<12;pixel++)for(unsigned c=0;c<4;c++)sums[c]+=rgba[pixel*4+c];
   assert(sums[0]==(i<2?255:0) && sums[1]==(i==1?128:0) && sums[2]==(i==2?255:0) && sums[3]==(i==1?510:255));
  }
  CGContextRelease(ctx);CGColorSpaceRelease(cs);CGImageRelease(frame);
 }
 CFRelease(source);
 }return 0;
}}
'''
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'test.m').write_text(source)
            subprocess.run(['xcrun','clang','-fobjc-arc','-framework','Foundation','-framework','ImageIO','-framework','CoreGraphics','-I',str(ROOT/'tests/native'),str(p/'test.m'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)
