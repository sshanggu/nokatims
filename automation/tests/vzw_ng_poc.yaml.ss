# Verizon 100G testbed da   xi ta file


topology:
    name:  'NG_POC'

ixia:
    chassis:     '135.228.0.151'
    server:      '135.228.2.128'
    port:        '8020'
    name:        'ixia_poc'
    #pattern:     'North-South-EDN-VC'

nodes:

    crs: 
        mgmt_ip: 135.228.0.202
        system_ip: 1.1.1.202
        netconf: True
        ports:
            #to_bl_1: '1/1/c12/1'
            to_bl_1: '1/1/c10/1'
            to_bl_2: '1/2/c12/1'
            nc_p1: '1/2/c1/1'
            nc_p2: '1/2/c1/2'
            nc_p3: '1/2/c1/3'
            nc_p4: '1/2/c1/4'
    bl_1:
        mgmt_ip: 135.228.0.203
        system_ip: 1.1.1.203
        ports:
            to_ense_vxlan: '1/1/c1/1'
            to_spine_1: '1/1/c3/1' 
            to_spine_2: '1/1/c5/1' 
            to_vxlan_spine_1: '1/1/c10/1' 
            to_vxlan_spine_2: '1/1/c10/2' 
            to_mls_1: 'lag-83'
        services:
            ran_vprn:
                id: 1
                type: 'vprn'
                def_nh: '2001:4888:2015:6203:172:19::'
                #def_nh: 'evi-1005'
    
    bl_2:
        mgmt_ip: 135.228.0.112
        system_ip: 1.1.1.112
        ports:
            to_ense_vxlan: '1/1/c7/1'
            to_spine_1: '1/1/c2/1' 
            to_spine_2: '1/1/c1/1' 
            to_vxlan_spine_1: '1/1/c9/1' 
            to_vxlan_spine_2: '1/1/c9/2' 
            to_mls_2: 'lag-93'
        services:
            ran_vprn:
                id: 1
                type: 'vprn'
                def_nh: '2001:4888:2015:6073:172:19:0:2'
                #def_nh: 'evi-1005'


    spine_1:
        mgmt_ip:   135.228.0.113
        system_ip: 1.1.1.113
        ports:
            #to_bl_1:    '1/1/c1/1' 
            to_bl_1:    '1/1/c5/1' 
            to_bl_2:    '1/1/c2/1' 
            to_al_1:    '1/1/c3/1' 
            to_al_2:    '1/1/c4/1' 
            to_al_4_1:  '1/2/c6/3' 
            to_al_4_2:  '1/2/c6/4' 

    spine_2:
        mgmt_ip:   135.228.0.114
        system_ip: 1.1.1.114
        ports:
            #to_bl_1:    '1/1/c1/1' 
            to_bl_1:    '1/1/c5/1' 
            to_bl_2:    '1/1/c2/1' 
            to_al_1:    '1/1/c3/1' 
            to_al_2:    '1/1/c4/1' 
            to_al_4_1:  '1/2/c6/3' 
            to_al_4_2:  '1/2/c6/4' 

    al_1:
        mgmt_ip:   135.228.0.115
        system_ip: 1.1.1.115
        ports:
            to_spine_1:  '1/1/c1/1' 
            to_spine_2:  '1/1/c2/1' 
            to_hub_1:    '1/1/c3/1' 
        services:
            ran_vprn:
                id: 1
                type: vprn
    al_2:
        mgmt_ip:   135.228.0.74
        system_ip: 1.1.1.74
        ports:
            to_spine_1:  '1/1/c1/1' 
            to_spine_2:  '1/1/c2/1' 
            to_hub_2:    '1/1/c3/1' 
        services:
            ran_vprn:
                id: 1
                type: vprn

    al_4:
        mgmt_ip:   135.228.1.83
        system_ip: 1.1.1.83
        ports:
            to_spine_1_1:  '1/3/1' 
            to_spine_1_2:  '1/3/2' 
            to_spine_2_1:  '1/3/3' 
            to_spine_2_2:  '1/3/4' 
            to_vc_1_1:     '1/1/4' 
        services:
            ran_vprn:
                id: 1

    al_3:
        #mgmt_ip:   135.228.1.75
        mgmt_ip:   192.168.100.75
        system_ip: 1.1.2.74
        ports:
            to_spine_1_1:  '1/1/1' 
            to_spine_1_2:  '1/1/2' 
            to_spine_2_1:  '1/1/3' 
            to_spine_2_2:  '1/1/4' 
            to_vc_1_1:     '1/3/2' 
        services:
            ran_vprn:
                id: 1
                type: vprn

    hub_1:
        mgmt_ip:   135.228.0.73
        system_ip: 1.1.1.73
        ports:
            to_al_1:  '1/1/c1/1' 
            to_hub_2: '1/1/c2/1' 
            to_ca_1:  '1/2/c1/1' 
            to_wbx:   '1/1/c3/1' 
        services:
            ran_vprn:
                id: 1
                type: vprn
                def_nh: 'ran-evi-101'

    hub_2:
        mgmt_ip:   135.228.0.72
        system_ip: 1.1.1.72
        ports:
            to_al_2:  '1/1/c1/1' 
            to_hub_1: '1/1/c2/1' 
            to_ca_1:  '1/2/c1/1' 
            to_wbx:   '1/1/c3/1' 
        services:
            ran_vprn:
                id: 1
                type: vprn
                def_nh: 'ran-evi-101'
    ca_1:
        mgmt_ip:   192.168.100.107 
        system_ip: 192.168.0.107 
        ports:
            to_hub_1:  '1/1/c49/1' 
            to_hub_2:  '1/1/c52/1' 
            #to_wbx:    '1/1/c3/1' 
        services:
            ran_vprn:
                id: 1
                type: vprn
    imn_102:
        mgmt_ip: 192.168.100.102

    imn_105:
        mgmt_ip: 192.168.100.105

    vc:
        mgmt_ip: 192.168.100.103
        ports:
            uplink_1:  '1/1/51' 
            uplink_2:  '2/1/51' 

    ixr6:
        mgmt_ip: 135.228.1.97
        ports:
            to_vc_sn_1_1_A: '2/1/1'
            to_vc_sn_1_1_S: '2/1/7'
            to_vc_sn_1_2_A: '2/1/2'
            to_vc_sn_1_2_S: '2/1/8'
        services:
            edn_vpls_411:
                id: 411
            edn_vpls_412:
                id: 412

    ixrs_110:
        mgmt_ip: 135.228.0.110
        ports:
            to_bl1_1: '1/1/c49/1'
            to_bl2_1: '1/1/c50/1'

    ixrs_127:
        mgmt_ip: 135.228.0.127
        ports:
            to_bl1_1: '1/1/c49/1'
            to_bl2_1: '1/1/c50/1'

    wbx32:
        mgmt_ip: 135.228.0.78
        services:
            edn_vpls_411:
                id: 411
            edn_vpls_412:
                id: 412

# SR-7s VXLAN POC
    vxlan_spine_1:
        mgmt_ip:   135.228.0.33
        system_ip: 10.33.1.1
        ports:
            to_bl_1:    '4/1/5' 
            to_bl_2:    '4/1/10' 
            to_vxlan_al_1:   'lag-14' 

    vxlan_spine_2:
        mgmt_ip:   135.228.0.34
        system_ip: 10.34.1.1
        ports:
            to_bl_1:    '4/1/2' 
            to_bl_2:    '4/1/10' 
            to_vxlan_al_1:   'lag-14' 

    vxlan_al_1:
        mgmt_ip:   135.228.1.225
        system_ip: 1.1.1.225
        ports:
            #to_vxlan_spine_1: '1/2/c12/1' 
            #to_vxlan_spine_2: '1/2/c12/2' 
            #to_ixia:          '1/1/c1/1' 
            #visp_1_inside:    '1/1/c2/1' 
            #visp_1_outside:   '1/1/c2/1' 
            #fw_1_inside:      '1/1/c2/1' 
            #fw_1_outside:     '1/1/c2/1' 
            #visp_2_inside:    '1/1/c3/1' 
            #visp_2_outside:   '1/1/c3/1' 
            #fw_2_inside:      '1/1/c3/1' 
            #fw_2_outside:     '1/1/c3/1' 
        services:
            visp_1:
                id: 1000
                type: vpls
                saps:
                    inside: '1/1/c2/1:1'
                    outside: '1/1/c2/1:2'
            visp_2:
                id: 2000
                type: vpls
                saps:
                    inside: '1/1/c3/1:1'
                    outside: '1/1/c3/1:2'
            fw_1:
                id: 1100
                type: vpls
                saps:
                    inside: '1/1/c2/1:3'
                    outside: '1/1/c2/1:4'
            fw_2:
                id: 2100
                type: vpls
                saps:
                    inside: '1/1/c3/1:3'
                    outside: '1/1/c3/1:4'
