"""Compile the production conservative freshness parser (not a reimplementation)."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
PROGRAM=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include "TASHTTPCache.h"
int main(void) {
    double value,lifetime,date;
    assert(image_cache_date("Thu, 01 Jan 1970 00:00:00 GMT",&value) && value==0);
    assert(image_cache_date("Sun, 06 Nov 1994 08:49:37 GMT",&value) && value==784111777);
    assert(image_cache_date("Thu, 29 Feb 2024 00:00:00 GMT",&value));
    const char *invalid_dates[]={"Fri, 29 Feb 2024 00:00:00 GMT","Sun, 29 Feb 2023 00:00:00 GMT",
        "Sun, 31 Feb 2024 00:00:00 GMT","Sun, 06 Nov 1994 24:49:37 GMT","Sun, 06 Nov 1994 08:60:37 GMT",
        "Sun, 06 Nov 1994 08:49:60 GMT","Sun, 06 Nov 1994 08:49:37 UTC","Sunday, 06-Nov-94 08:49:37 GMT","garbage",NULL};
    for(unsigned i=0;i<sizeof(invalid_dates)/sizeof(*invalid_dates);i++)assert(!image_cache_date(invalid_dates[i],&value));
    const char *stamp="Sun, 06 Nov 1994 08:49:37 GMT",*expiry="Sun, 06 Nov 1994 09:49:37 GMT";
    assert(image_cache_lifetime("public, max-age=3600, must-revalidate",stamp,NULL,&lifetime,&date) && lifetime==3600);
    assert(image_cache_lifetime(" MAX-AGE = \"3600\" , immutable",stamp,NULL,&lifetime,&date) && lifetime==3600);
    assert(image_cache_lifetime("private",stamp,expiry,&lifetime,&date) && lifetime==3600);
    assert(image_cache_lifetime("s-maxage=1, max-age=3600, stale-while-revalidate=30",stamp,NULL,&lifetime,&date) && lifetime==3600);
    assert(image_cache_lifetime(NULL,stamp,expiry,&lifetime,&date) && lifetime==3600);
    const char *invalid[]={"max-age=0","max-age=-1","max-age=garbage","max-age=99999999999999999",
        "max-age=3600, no-cache","no-cache=\"ETag\", max-age=3600","no-store, max-age=3600",
        "max-age=3600, private=\"Content-Type\"","max-age=3600, MAX-AGE=3600","max-age=3600, x-unknown=1","max-age=3600,",NULL};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(*invalid);i++)assert(!image_cache_lifetime(invalid[i],stamp,NULL,&lifetime,&date));
    assert(!image_cache_lifetime("max-age=3600",NULL,NULL,&lifetime,&date));
    unsigned reason;
    assert(image_cache_lifetime_at_reason("max-age=3600",NULL,NULL,784111777,&lifetime,&date,&reason) && lifetime==3600 && date==784111777);
    assert(image_cache_lifetime_at_reason(NULL,NULL,expiry,784111777,&lifetime,&date,&reason) && lifetime==3600);
    assert(!image_cache_lifetime_at_reason("max-age=3600","bad",NULL,784111777,&lifetime,&date,&reason) && reason==IMAGE_CACHE_DATE_INVALID);
    assert(!image_cache_lifetime_at_reason("max-age=3600",NULL,NULL,NAN,&lifetime,&date,&reason) && reason==IMAGE_CACHE_DATE_MISSING);
    assert(!image_cache_lifetime_at_reason("max-age=3600, no-cache",NULL,NULL,784111777,&lifetime,&date,&reason));
    assert(!image_cache_lifetime(NULL,expiry,stamp,&lifetime,&date));
    assert(image_cache_seconds("2147483647",&value) && value==2147483647);
    assert(!image_cache_seconds("2147483648",&value));assert(!image_cache_seconds("1 2",&value));
    assert(!image_cache_seconds("NaN",&value));assert(!image_cache_seconds(NULL,&value));
    return 0;
}
'''
class HTTPCacheTests(unittest.TestCase):
    def test_freshness_parser(self):
        zig=os.environ.get('ZIG') or shutil.which('zig')
        self.assertTrue(zig)
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'cache.c';binary=Path(folder)/'cache';source.write_text(PROGRAM)
            built=subprocess.run([zig,'cc','-Wall','-Wextra','-Werror','-I',str(ROOT/'src'),str(source),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            ran=subprocess.run([binary],capture_output=True,text=True,timeout=10)
            self.assertEqual(ran.returncode,0,ran.stderr)
