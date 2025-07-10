# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT

# Put here only the dependencies required to run the module.
# Development and test requirements should go to the corresponding files.
"""MFD-Ethtool examples of usage."""

from mfd_connect import SSHConnection
from mfd_ethtool import Ethtool

conn = SSHConnection(username="your_username", password="your_password", ip="x.x.x.x") # create mfd-connect connection
ethtool_obj = Ethtool(connection=conn) # instantiate mfd-ethtool object
print(ethtool_obj.get_version())
print(ethtool_obj.execute_ethtool_command(device_name="intf1", namespace="NS1"))
dev_info = ethtool_obj.get_standard_device_info(device_name="intf1")
print(dev_info.supported_ports)
print(dev_info.supports_auto_negotiation)
pause_options = ethtool_obj.get_pause_options(device_name="intf1")
print(pause_options.autonegotiate)
print(ethtool_obj.set_pause_options(device_name="intf1", param_name="autoneg", param_value="off", namespace="NS1"))
coalesce_options = ethtool_obj.get_coalesce_options(device_name="intf1")
print(coalesce_options.adaptive_tx)
print(ethtool_obj.set_coalesce_options(device_name="intf1", param_name="rx-usecs", param_value="1", namespace="NS1"))
ring_params = ethtool_obj.get_ring_parameters(device_name="intf1")
print(ring_params.preset_max_rx)
print(ring_params.current_hw_rx)
print(ethtool_obj.set_ring_parameters(device_name="intf1", param_name="rx", param_value="512"))
drv_info = ethtool_obj.get_driver_information(device_name="intf1")
print(drv_info.firmware_version)
features = ethtool_obj.get_protocol_offload_and_feature_state(device_name="intf1")
print(features.rx_checksumming, features.tx_checksumming)
print(ethtool_obj.set_protocol_offload_and_feature_state(device_name="intf1", param_name="tso", param_value="on"))
channel_params = ethtool_obj.get_channel_parameters(device_name="intf1", namespace="NS1")
print(channel_params.preset_max_rx)
print(channel_params.current_hw_rx)
print(ethtool_obj.set_channel_parameters(device_name="intf1", param_name="combined", param_value="2", namespace="NS1"))
print(
    ethtool_obj.get_receive_network_flow_classification(
        device_name="intf1", param_name="rx-flow-hash", param_value="tcp4"
    )
)
print(
    ethtool_obj.set_receive_network_flow_classification(device_name="intf1", params="flow-type ip4 proto 1 action -1")
)
print(ethtool_obj.show_visible_port_identification(device_name="intf1", duration=5))
print(ethtool_obj.change_eeprom_settings(device_name="intf1", params="offset 0x12 value 0x41"))
print(ethtool_obj.do_eeprom_dump(device_name="intf1"))
print(ethtool_obj.restart_negotiation(device_name="intf1"))
stats = ethtool_obj.get_adapter_statistics(device_name="inf1")
print(stats.rx_packets)
print(ethtool_obj.get_statistics_xonn_xoff(device_name="eth1"))
print(ethtool_obj.execute_self_test(device_name="intf1", test_mode="offline"))
print(ethtool_obj.change_generic_options(device_name="intf1", param_name="autoneg", param_value="on"))
priv_flags_output = ethtool_obj.get_private_flags(device_name="intf1")
print(priv_flags_output.priv_flags["flag_name"])
print(ethtool_obj.set_private_flags(device_name="intf1", flag_name="legacy-rx", flag_value="on"))
print(ethtool_obj.get_rss_indirection_table(device_name="intf1"))
print(ethtool_obj.set_rss_indirection_table(device_name="intf1", param_name="equal", param_value="20"))
print(ethtool_obj.flash_firmware_image(device_name="intf1", file="gtp.pkgo", region=100))
print(ethtool_obj.unload_ddp_profile(device_name="intf1", region=100))
fec_settings = ethtool_obj.get_fec_settings(device_name="intf1")
print(fec_settings.active_fec_encodings)
print(ethtool_obj.set_fec_settings(device_name="intf1", setting_name="encoding", setting_value="on"))
print(ethtool_obj.do_register_dump(device_name="intf1"))
print(ethtool_obj.get_time_stamping_capabilities(device_name="intf1"))
print(ethtool_obj.get_perm_hw_address(device_name="intf1"))
print(ethtool_obj.dump_module_eeprom(device_name="intf1"))
eee_settings = ethtool_obj.get_eee_settings(device_name="intf1")
print(eee_settings.eee_status)
print(ethtool_obj.set_eee_settings(device_name="intf1", param_name="eee", param_value="on"))
print(ethtool_obj.set_phy_tunable(device_name="intf1", params="downshift on count 2"))
print(ethtool_obj.reset_components(device_name="intf1", param_name="phy"))
print(ethtool_obj.get_dump(device_name="intf1", params="data file.bin"))
print(ethtool_obj.set_dump(device_name="intf1", params="3"))
