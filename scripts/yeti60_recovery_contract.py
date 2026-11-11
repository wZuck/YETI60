"""Read the resolved devicetree, not just a keymap text/symbol presence."""
import struct


def bindings(tree, prop):
    cells=struct.unpack('>'+str(len(prop.value)//4)+'I',prop.value)
    result=[];i=0
    while i<len(cells):
        node=tree.phandle2node[cells[i]]
        count=node.props['#binding-cells'].to_num()
        result.append((node,tuple(cells[i+1:i+1+count])))
        i+=count+1
    assert i==len(cells)
    return result


def check_recovery_dts(tree):
    clear=tree.get_node('/behaviors/clear_selected_bt')
    assert clear.props['compatible'].to_string()=='zmk,behavior-tap-dance'
    assert clear.props['tapping-term-ms'].to_num()==400
    actions=bindings(tree,clear.props['bindings'])
    assert len(actions)==2
    assert actions[0][0].props['compatible'].to_string()=='zmk,behavior-none' and actions[0][1]==()
    assert actions[1][0].props['compatible'].to_string()=='zmk,behavior-bluetooth'
    # Frozen ZMK bt.h: BT_CLR_CMD=0; BT_CLR_ALL_CMD=4 is forbidden here.
    assert actions[1][1]==(0,0),'Recovery must clear only the selected profile'
    base=bindings(tree,tree.get_node('/keymap/base').props['bindings'])
    fn=bindings(tree,tree.get_node('/keymap/fn').props['bindings'])
    assert len(base)==len(fn)==60
    assert base[28][0].props['compatible'].to_string()=='zmk,behavior-key-press'
    assert base[28][1]==(0x7002a,),'Base Backspace must remain Backspace'
    assert fn[28]==(clear,()),'Fn+Backspace must use guarded recovery'
    for slot in range(5):
        node,args=fn[16+slot]
        assert node.props['compatible'].to_string()=='zmk,behavior-bluetooth' and args==(3,slot)
    return dict(gesture='Fn + double-tap Backspace',window_ms=400,
                single_tap='none',hold='none',clears='selected BLE profile only',
                base_Backspace_preserved=True,profile_slots=5,
                calibration_settings_erase_binding=False)
