/* Included after the actual upstream C implementation, in one host TU. */
static struct zmk_behavior_binding actions[]={
  {.behavior_dev="none"}, {.behavior_dev="bt",.param1=0,.param2=0}};
static const struct behavior_tap_dance_config recovery={400,2,actions};
static const struct device dev={&recovery};
static struct zmk_behavior_binding key={.behavior_dev="clear_selected_bt"};
static unsigned clear_count,selected=2,last_cleared=99;
static const struct device *zmk_behavior_get_binding(const char *name) { (void)name;return &dev; }
static int zmk_behavior_invoke_binding(struct zmk_behavior_binding *b,struct zmk_behavior_binding_event e,bool down) {
  (void)e;
  if (down && !strcmp(b->behavior_dev,"bt")) {
    assert(b->param1==0 && b->param2==0);
    clear_count++;last_cleared=selected;
  } else assert(!strcmp(b->behavior_dev,"none") || !down);
  return 0;
}
static void advance(int64_t at) {
  for (unsigned i=0;i<CONFIG_ZMK_BEHAVIOR_TAP_DANCE_MAX_HELD;i++) {
    struct k_work_delayable *w=&active_tap_dances[i].release_timer;
    if (w->pending && w->due<=at) { now_ms=w->due;w->pending=false;w->work.handler(&w->work); }
  }
  now_ms=at;
}
static void edge(bool down,int64_t at) {
  advance(at);
  struct zmk_behavior_binding_event e={.position=28,.timestamp=at};
  if (down) on_tap_dance_binding_pressed(&key,e);
  else on_tap_dance_binding_released(&key,e);
}
static void finish(int64_t at) {
  advance(at);
  for (unsigned i=0;i<CONFIG_ZMK_BEHAVIOR_TAP_DANCE_MAX_HELD;i++)
    assert(active_tap_dances[i].position==ZMK_BHV_TAP_DANCE_POSITION_FREE);
}
int main(void) {
  behavior_tap_dance_init(&dev);
  edge(true,0);edge(false,10);finish(500);assert(clear_count==0);
  edge(true,1000);advance(2000);edge(false,2010);finish(2500);assert(clear_count==0);
  edge(true,3000);edge(false,3010);edge(true,3200);assert(clear_count==1 && last_cleared==2);
  edge(false,3210);finish(3700);
  edge(true,4000);edge(false,4010);advance(4500);edge(true,4600);edge(false,4610);finish(5100);assert(clear_count==1);
  edge(true,6000);edge(false,6010);
  advance(6100);zmk_event_t other={.position=16,.state=true,.timestamp=6100};
  tap_dance_position_state_changed_listener(&other);selected=4;
  edge(true,6200);edge(false,6210);finish(6700);assert(clear_count==1);
  edge(true,7000);edge(false,7010);edge(true,7100);edge(false,7110);finish(7600);
  assert(clear_count==2 && last_cleared==4);
  puts("Pinned ZMK tap dance: single, hold, slow taps and interrupted taps do not clear; double tap dispatches selected-profile clear once");
  return 0;
}
