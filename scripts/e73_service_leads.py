"""Shapes for the E73 plug service trial, with clearance for axial cable feed."""

import math

from e73_corner_harness_paths import chain, length
from e73_service_route import USB_TRIAL, trial_paths
from interconnect_geometry import line, offset_path, s_bend


PARK_TRAVEL = {'J2': 4.5, 'J4': 4.0}
PARK_DROP = .45
BATTERY_BOW_START = 162.6
BATTERY_BOW_RADIUS = 6.2
BATTERY_GUIDE_STATIONS = [186, 189]


def trial_spec(spec):
    return dict(spec, usb=dict(spec['usb'],
                               twist_rear_turns=USB_TRIAL['twist_rear_turns'],
                               twist_down_turns=USB_TRIAL['twist_down_turns']))


def position_exits(exits, battery_axial, battery_down, usb_axial, usb_down):
    j2x, j2y, j2z = exits['J2']
    j4x, j4y, j4z = exits['J4']
    return dict(exits,
                J2=[j2x, j2y+PARK_TRAVEL['J2']*battery_axial, j2z-PARK_DROP*battery_down],
                J4=[j4x-PARK_TRAVEL['J4']*usb_axial, j4y, j4z-PARK_DROP*usb_down])


def battery_launch(stock, spec, original_exit, new_exit, bow):
    """Combine the Z ramp and pin fan-out in one two-arc bend.

    The intermediate bow is outside both proposed stationary guide channels.
    Beyond the bow the path at each channel is the same in every state.
    """
    out = {}
    station = BATTERY_BOW_START
    rear_y = spec['rear_y']
    rear_z = spec['rear_z']
    direction = (1, 0, 0)
    sideways = (0, 1, 0)
    depart, tips, _ = s_bend((station, rear_y, rear_z), direction, -bow,
                             BATTERY_BOW_RADIUS, sideways)
    return_path, main_resume, _ = s_bend(tips, direction, bow, BATTERY_BOW_RADIUS, sideways)
    assert main_resume[0] < BATTERY_GUIDE_STATIONS[0]-1
    first_corner_end = original_exit[0]+spec['radius']
    second_corner_start = spec['side_x']-spec['radius']
    for pin, lateral, housing_offset in zip(('1', '2', '3'), spec['lateral_offsets'],
                                             spec['header_lateral_offsets']):
        path = stock[pin]
        (main,) = [i for i, part in enumerate(path)
                   if part['kind'] == 'line' and abs(part['start'][0]-first_corner_end) < 1e-6
                   and abs(part['end'][0]-second_corner_start) < 1e-6]
        start = (new_exit[0]-housing_offset, new_exit[1], new_exit[2])
        turn_start = path[main-1]['start']
        transition = (turn_start[0]-start[0], 0, turn_start[2]-start[2])
        displacement = math.hypot(*transition)
        run = turn_start[1]-start[1]
        assert run > 0
        radius = (run**2+displacement**2)/(4*displacement)
        assert radius >= 4, ('Battery launch radius', pin, radius)
        lead_in, landed, _ = s_bend(start, (0, 1, 0), displacement, radius, transition)
        assert math.dist(landed, turn_start) < 1e-6

        middle = chain([line((first_corner_end, rear_y, rear_z), (station, rear_y, rear_z))],
                       depart, return_path, [line(main_resume, (second_corner_start, rear_y, rear_z))])
        out[pin] = chain(lead_in, [path[main-1]], offset_path(middle, lateral), path[main+1:])
    return out


def flex_routes(params, exits, shifted, delta):
    """Fit the candidate's existing free lengths at new connector poses."""
    stock, original_usb = trial_paths(params, exits, delta)
    unchanged_battery = dict(shifted, J2=exits['J2'])
    _, moved_usb = trial_paths(params, unchanged_battery, delta)
    # A millimetre further forward adds a millimetre on each U-loop leg.
    loop_displacement = (length(original_usb)-length(moved_usb))/2
    params = dict(params, usb=dict(params['usb'], front_y=params['usb']['front_y']-loop_displacement))
    routes, centre = trial_paths(params, unchanged_battery, delta)
    assert abs(length(original_usb)-length(centre)) < 1e-6

    battery = params['battery']
    x, y, z = shifted['J2']
    latest_exit = (x, y, z+delta)
    old_exit = (exits['J2'][0], exits['J2'][1], exits['J2'][2]+delta)
    make = lambda end, bow: battery_launch(stock['battery'], battery, old_exit, end, bow)
    installed_battery = make(old_exit, 0)
    wanted = length(installed_battery['2'])
    lo, hi = 0., 7.
    if old_exit == latest_exit:
        bow = 0.
        routes['battery'] = installed_battery
    else:
        assert length(make(latest_exit, lo)['2']) <= wanted <= length(make(latest_exit, hi)['2'])
        for _ in range(36):
            mid = (lo+hi)/2
            if length(make(latest_exit, mid)['2']) > wanted:
                hi = mid
            else:
                lo = mid
        bow = (lo+hi)/2
        routes['battery'] = make(latest_exit, bow)
        assert abs(length(routes['battery']['2'])-wanted) < 1e-6
    return routes, centre, {'USB_front_loop_displacement_mm': loop_displacement,
                            'battery_bow_displacement_mm': bow}
