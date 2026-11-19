"""Reversible service-route trial using the existing end runs and connector poses."""

from e73_corner_harness_paths import chain, paths
from interconnect_geometry import line, offset_path, s_bend


USB_TRIAL = {
    'early_descent_y_mm': -108.8,
    'crossing_z_mm': -4.73,
    'return_to_front_run_y_mm': -124,
    'twist_rear_turns': 3.06,
    'twist_down_turns': .69,
}
POWER_TRIAL = {'crossing_y_mm': -118, 'return_x_mm': 182}


def end_of_line(route, axis, coordinate):
    (index,) = [i for i, part in enumerate(route)
                if part['kind'] == 'line' and abs(part['end'][axis]-coordinate) < 1e-6]
    return index


def trial_paths(spec, exits, delta):
    stock, usb = paths(spec, exits, delta)
    u, p = spec['usb'], spec['power']
    trial = USB_TRIAL
    departure = end_of_line(usb, 1, u['drop_y'])
    old_run = usb[departure+3]  # The original descent comprises two tangent arcs.
    assert old_run['kind'] == 'line' and old_run['start'][2] == u['front_z']
    turn_end = usb[departure]['start']
    descent_start = (turn_end[0], trial['early_descent_y_mm'], turn_end[2])
    dive, low, _ = s_bend(descent_start, (0, -1, 0),
                          trial['crossing_z_mm']-turn_end[2], u['bend_radius'])
    rise_start = (low[0], trial['return_to_front_run_y_mm'], low[2])
    rise, high, _ = s_bend(rise_start, (0, -1, 0), u['front_z']-low[2], u['bend_radius'])
    assert low[1] > rise_start[1] and high[1] > old_run['end'][1]
    usb = chain(usb[:departure], [line(turn_end, descent_start)], dive,
                [line(low, rise_start)], rise, [line(high, old_run['end'])],
                usb[departure+4:])
    stock['usb'] = {str(pin): offset_path(usb, offset)
                    for pin, offset in enumerate([1.5, .5, -.5, -1.5], 1)}

    y = p['rear_y']
    z = p['high_z']+delta
    dy = POWER_TRIAL['crossing_y_mm']-y
    start = (p['cross_start_x'], y, z)
    travel = (-1, 0, 0)
    normal = (0, 1, 0)
    forward, at, _ = s_bend(start, travel, dy, p['side_radius'], normal)
    return_start = (POWER_TRIAL['return_x_mm'], at[1], z)
    back, end, _ = s_bend(return_start, travel, -dy, p['side_radius'], normal)
    middle = chain(forward, [line(at, return_start)], back,
                   [line(end, (p['low_start_x'], y, z))])
    for pin, offset in [('1', .5), ('2', -.5)]:
        path = stock['power'][pin]
        first = end_of_line(path, 0, p['cross_start_x'])
        last = end_of_line(path, 0, p['low_start_x'])
        stock['power'][pin] = chain(path[:first+1], offset_path(middle, offset), path[last+1:])
    return stock, usb
