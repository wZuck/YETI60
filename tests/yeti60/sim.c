/* Host simulation of the actual portable control core. SPDX-License-Identifier: MIT */
#include "core.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
struct sim { enum yeti_mode pins[64]; uint64_t now,afe_on,discharged,released,bat_on; unsigned adc_reads,frame_reads,reports,events; int fail_at; bool reject_report,reenter; uint16_t sample[5][15]; uint8_t report[8];enum yeti_link link;struct yeti_core *core; };
static bool high(enum yeti_mode m){return m==Y_HIGH;}
static void gpio(void *ctx,uint8_t pin,enum yeti_mode mode) {
 struct sim *s=ctx;assert(pin<64);s->events++;
 bool controlled=pin==PIN_APLEX_OUT_PIN_0||pin==PIN_ADC;
 for(unsigned i=0;i<5;i++)controlled|=pin==yeti_rows[i];
 for(unsigned i=0;i<3;i++)controlled|=pin==yeti_sel[i];
 for(unsigned i=0;i<2;i++)controlled|=pin==yeti_en[i];
 if(controlled&&mode!=Y_HIZ){assert(high(s->pins[PIN_AFE_EN]));assert(s->now-s->afe_on>=5000);}
 for(unsigned i=0;i<3;i++)if(pin==yeti_sel[i]&&mode!=Y_HIZ)assert((s->pins[yeti_en[0]]==Y_HIGH||s->pins[yeti_en[0]]==Y_HIZ)&&(s->pins[yeti_en[1]]==Y_HIGH||s->pins[yeti_en[1]]==Y_HIZ));
 s->pins[pin]=mode;
 if(pin==PIN_AFE_EN&&mode==Y_HIGH)s->afe_on=s->now;
 if(pin==PIN_BAT_MEAS_EN&&mode==Y_HIGH)s->bat_on=s->now;
 if(pin==PIN_APLEX_OUT_PIN_0&&mode==Y_OD_LOW)s->discharged=s->now;
 if(pin==PIN_APLEX_OUT_PIN_0&&mode==Y_OD_RELEASE){assert(s->now-s->discharged>=10);s->released=s->now;}
 unsigned raised=0;for(unsigned i=0;i<5;i++)raised+=high(s->pins[yeti_rows[i]]);assert(raised<=1);
}
static void delay(void *ctx,uint32_t us){((struct sim*)ctx)->now+=us;}
static int adc(void *ctx,uint8_t ain,uint32_t acquisition) {
 struct sim *s=ctx;assert(acquisition==40);s->adc_reads++;s->now+=acquisition;
 if(ain==YETI_BAT_AIN){assert(high(s->pins[PIN_BAT_MEAS_EN]));assert(s->now-s->bat_on>=50000);return 2389;}
 assert(ain==2&&ain==YETI_ADC_AIN);assert(high(s->pins[PIN_AFE_EN]));
 unsigned c=s->frame_reads/5,r=s->frame_reads%5;assert(c<15);unsigned channel=0;
 for(unsigned i=0;i<3;i++)channel|=(unsigned)high(s->pins[yeti_sel[i]])<<i;
 assert(channel==yeti_channels[c]);assert(s->pins[yeti_en[c/8]]==Y_LOW);assert(s->pins[yeti_en[1-c/8]]==Y_HIGH);
 for(unsigned i=0;i<5;i++)assert(high(s->pins[yeti_rows[i]])==(i==r));
 assert(s->pins[PIN_APLEX_OUT_PIN_0]==Y_OD_RELEASE);assert(s->now-s->released>=5);
 if(s->reenter){uint32_t mv;assert(yeti_battery_mv(s->core,&mv)==-1);assert(yeti_scan(s->core)==-1);}
 unsigned index=s->frame_reads++;if(s->fail_at>=0&&(int)index==s->fail_at)return -1;
 return s->sample[r][c];
}
static bool report(void *ctx,enum yeti_link link,const uint8_t data[8]) {
 struct sim*s=ctx;s->reports++;if(s->reject_report)return false;memcpy(s->report,data,8);s->link=link;return true;
}
static void init(struct yeti_core *core,struct sim *sim) {
 memset(core,0,sizeof(*core));memset(sim,0,sizeof(*sim));sim->fail_at=-1;sim->core=core;
 struct yeti_hal h={sim,gpio,delay,adc,report};struct yeti_config c={0};
 c.debounce_frames=2;c.afe_settle_us=5000;c.mux_settle_us=3;c.discharge_us=10;c.charge_us=5;c.acquisition_us=40;
 for(unsigned r=0;r<5;r++)for(unsigned col=0;col<15;col++){c.low[r][col]=1500;c.high[r][col]=2000;c.usage[r][col]=(uint8_t)(4+r*15+col);sim->sample[r][col]=1000;}
 assert(yeti_init(core,&h,&c)==0);
}
static void scan(struct yeti_core *c,struct sim *s){s->frame_reads=0;assert(yeti_scan(c)==0);assert(s->frame_reads==75);for(unsigned i=0;i<5;i++)assert(s->pins[yeti_rows[i]]==Y_LOW);assert(s->pins[yeti_en[0]]==Y_HIGH&&s->pins[yeti_en[1]]==Y_HIGH);}
static void single_keys(void) {
 struct yeti_core c;struct sim s;init(&c,&s);assert(yeti_power(&c,true)==0);s.reenter=true;
 for(unsigned r=0;r<5;r++)for(unsigned col=0;col<15;col++) {
  s.sample[r][col]=2500;scan(&c,&s);assert(c.matrix[r]==0);scan(&c,&s);assert(c.matrix[r]==(1u<<col));
  s.sample[r][col]=1000;scan(&c,&s);assert(c.matrix[r]==(1u<<col));scan(&c,&s);assert(c.matrix[r]==0);
 }
 printf("single-keys: 75 positions, 300 frames, %u ADC reads; mux/row/OD/timing/reentrancy invariants pass\n",s.adc_reads);
}
static void noise(void) {
 struct yeti_core c;struct sim s;init(&c,&s);assert(yeti_power(&c,true)==0);uint32_t rng=0x59455449;unsigned transitions=0;
 for(unsigned frame=0;frame<2000;frame++) {
  for(unsigned r=0;r<5;r++)for(unsigned col=0;col<15;col++){rng=rng*1664525u+1013904223u;s.sample[r][col]=(uint16_t)(1500+(rng%501));}
  scan(&c,&s);for(unsigned r=0;r<5;r++)assert(c.matrix[r]==0);
 }
 s.sample[0][0]=2500;scan(&c,&s);s.sample[0][0]=1800;scan(&c,&s);assert(c.matrix[0]==0);
 s.sample[0][0]=2500;scan(&c,&s);scan(&c,&s);assert(c.matrix[0]==1);transitions++;
 for(unsigned i=0;i<10;i++){s.sample[0][0]=1500;scan(&c,&s);assert(c.matrix[0]==1);}
 s.sample[0][0]=1499;scan(&c,&s);scan(&c,&s);assert(c.matrix[0]==0);transitions++;
 printf("noise: 2000 frames of hysteresis-band samples; no false presses; %u expected transitions\n",transitions);
}
static void failures(void) {
 struct yeti_core c;struct sim s;init(&c,&s);assert(yeti_scan(&c)==-1);assert(s.adc_reads==0);assert(yeti_power(&c,true)==0);
 s.sample[0][0]=2500;scan(&c,&s);scan(&c,&s);assert(c.matrix[0]);s.fail_at=37;s.frame_reads=0;assert(yeti_scan(&c)==-2);
 for(unsigned r=0;r<5;r++)assert(!c.matrix[r]&&s.pins[yeti_rows[r]]==Y_LOW);
 assert(s.pins[yeti_en[0]]==Y_HIGH&&s.pins[yeti_en[1]]==Y_HIGH);assert(s.pins[PIN_APLEX_OUT_PIN_0]==Y_OD_LOW);
 unsigned count=s.adc_reads;assert(yeti_power(&c,false)==0);assert(yeti_scan(&c)==-1);assert(count==s.adc_reads);
 for(unsigned r=0;r<5;r++)assert(s.pins[yeti_rows[r]]==Y_HIZ);assert(s.pins[PIN_AFE_EN]==Y_LOW);
 struct yeti_config invalid=c.cfg;invalid.low[4][14]=invalid.high[4][14];struct yeti_core fresh={0};assert(yeti_init(&fresh,&c.hal,&invalid)==-1);assert(!fresh.initialized);
 puts("faults: invalid configuration, ADC fault, atomic frame abort, key release and AFE high-Z shutdown pass");
}
static void power_hid(void) {
 struct yeti_core c;struct sim s;init(&c,&s);assert(yeti_connections(&c,Y_USB_POWERED,500,true)==0);assert(s.pins[PIN_CHG_EN1]==Y_LOW&&s.pins[PIN_CHG_EN2]==Y_LOW&&s.pins[PIN_CHG_CE_N]==Y_HIGH);assert(c.link==Y_BLE);
 assert(yeti_power(&c,true)==0);s.sample[0][0]=2500;scan(&c,&s);scan(&c,&s);assert(s.report[2]==4);
 assert(yeti_connections(&c,Y_USB_CONFIGURED,500,true)==0);assert(c.link==Y_USB&&s.report[2]==4);assert(s.pins[PIN_CHG_EN1]==Y_HIGH&&s.pins[PIN_CHG_EN2]==Y_LOW&&s.pins[PIN_CHG_CE_N]==Y_LOW);
 assert(yeti_connections(&c,Y_USB_SUSPENDED,500,true)==0);assert(c.link==Y_BLE&&s.report[2]==4);assert(s.pins[PIN_CHG_EN1]==Y_HIGH&&s.pins[PIN_CHG_EN2]==Y_HIGH&&s.pins[PIN_CHG_CE_N]==Y_HIGH);
 assert(yeti_connections(&c,Y_USB_CONFIGURED,100,false)==0);assert(s.pins[PIN_CHG_EN1]==Y_LOW&&s.pins[PIN_CHG_EN2]==Y_LOW);
 for(unsigned col=0;col<8;col++)s.sample[1][col]=2500;scan(&c,&s);scan(&c,&s);for(unsigned i=2;i<8;i++)assert(s.report[i]==1);
 s.reject_report=true;memset(s.sample,0,sizeof(s.sample));scan(&c,&s);scan(&c,&s);assert(c.dirty);s.reject_report=false;scan(&c,&s);assert(!c.dirty);for(unsigned i=0;i<8;i++)assert(s.report[i]==0);
 uint32_t mv=0;assert(yeti_battery_mv(&c,&mv)==0);assert(mv>=4199&&mv<=4202);assert(s.pins[PIN_BAT_MEAS_EN]==Y_LOW);scan(&c,&s);
 printf("power-hid: USB100/USB500/suspend, BLE-USB held-key handover, rollover, send retry and battery %u mV pass\n",mv);
}
int main(void){single_keys();noise();failures();power_hid();puts("YETI60 host simulation passed; transport, ADC and GPIO are mocked, not nRF peripheral emulation.");return 0;}
