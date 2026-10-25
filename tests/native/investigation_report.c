#include "TASInvestigationReport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){
 const char seed[]="[3,0,1,[[0,0,0,0,0,0,0,0,0],[1,1,0,1,1,0,2,0,0],[1,2,0,1,2,0,2,0,0],[1,3,0,1,3,0,2,0,0],[1,4,0,1,4,0,2,0,0],[1,5,0,1,5,0,2,0,0],[1,6,0,1,6,0,2,0,0],[1,7,0,1,7,0,2,0,0],[1,8,0,1,8,0,2,0,0],[1,9,0,1,9,0,2,0,0],[1,10,0,1,10,0,2,0,0],[8,20,4,1,10,32,9,0,0],[8,20,4,1,9,32,8,0,0],[8,20,4,1,8,32,7,0,0],[9,20,8,1,8,136,7,34000,240],[3,20,4,1,0,0,10,0,1],[11,21,4,1,0,11,3,7,9]]]";
 unsigned char input[8193];unsigned random=1;char report[65536];
 for(unsigned trial=0;trial<20000;trial++){
  size_t n=trial%2?sizeof(seed)-1:trial%sizeof(input);memset(input,' ',n);memcpy(input,seed,n<sizeof(seed)-1?n:sizeof(seed)-1);
  for(unsigned k=0;k<1+trial%8 && n;k++){random=random*1664525U+1013904223U;size_t at=random%n;random=random*1664525U+1013904223U;input[at]=(unsigned char)(random>>24);}
  tas_inv_report_accept(2,trial+1,input,n,trial*250ULL);assert(tas_inv_report_format(report,sizeof(report))<sizeof(report));
 }
 assert(tas_inv_report_accept(3,20001,seed,sizeof(seed)-1,6000000));assert(tas_inv_report_complete(3,20001));
 assert(tas_inv_report_format(report,sizeof(report))>0);assert(strstr(report,"selected=8")!=NULL);
 puts("20,000 bounded numeric report mutations passed under sanitizers");return 0;
}
