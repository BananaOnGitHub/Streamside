#include "TASInvestigationReport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
 const char seed[]="[1,0,1,[[0,0,0,0,0,0,0,0,0]]]";
 unsigned char input[8193];unsigned random=1;char report[65536];
 for(unsigned trial=0;trial<20000;trial++){
  size_t n=trial%2?sizeof(seed)-1:trial%sizeof(input);memset(input,' ',n);memcpy(input,seed,n<sizeof(seed)-1?n:sizeof(seed)-1);
  for(unsigned k=0;k<1+trial%8 && n;k++){random=random*1664525U+1013904223U;size_t at=random%n;random=random*1664525U+1013904223U;input[at]=(unsigned char)(random>>24);}
  tas_inv_report_accept(2,trial+1,input,n,trial*250ULL);assert(tas_inv_report_format(report,sizeof(report))<sizeof(report));
 }
 assert(tas_inv_report_accept(3,20001,seed,sizeof(seed)-1,6000000));assert(tas_inv_report_complete(3,20001));
 puts("20,000 bounded numeric report mutations passed under sanitizers");return 0;
}
