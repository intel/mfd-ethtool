# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Tests for `mfd_ethtool` package."""

import re
from textwrap import dedent
from dataclasses import asdict, dataclass

import pytest
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess
from mfd_typing import OSName

from mfd_ethtool import Ethtool
from mfd_ethtool.exceptions import EthtoolNotAvailable, EthtoolException, EthtoolExecutionError
from mfd_ethtool.structures import GetReceiveNetworkFlowClassification, SetReceiveNetworkFlowClassification


@dataclass
class ChannelParams:
    current_hw_tx: list
    current_hw_rx: list


class TestMfdEthtool:
    @pytest.fixture()
    def ethtool(self, mocker):
        mocker.patch("mfd_ethtool.Ethtool.check_if_available", mocker.create_autospec(Ethtool.check_if_available))
        mocker.patch(
            "mfd_ethtool.Ethtool.get_version", mocker.create_autospec(Ethtool.get_version, return_value="4.15")
        )
        mocker.patch(
            "mfd_ethtool.Ethtool._get_tool_exec_factory",
            mocker.create_autospec(Ethtool._get_tool_exec_factory, return_value="ethtool"),
        )
        conn = mocker.create_autospec(SSHConnection)
        conn.get_os_name.return_value = OSName.LINUX
        ethtool = Ethtool(connection=conn)
        mocker.stopall()
        return ethtool

    def test_check_if_available(self, ethtool):
        ethtool._connection.execute_command.return_value.return_code = 0
        ethtool.check_if_available()

    def test_check_if_available_when_tool_not_found(self, ethtool):
        ethtool._connection.execute_command.side_effect = EthtoolNotAvailable(returncode=1, cmd="")
        with pytest.raises(EthtoolNotAvailable):
            ethtool.check_if_available()

    def test_get_version(self, ethtool):
        output = dedent("""ethtool version 4.15""")
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0
        )
        assert ethtool.get_version() == "4.15"

    def test_get_version_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(args="", stdout="", return_code=0)
        with pytest.raises(EthtoolException, match="Ethtool version not found."):
            ethtool.get_version()

    def test_execute_ethtool_command(self, ethtool):
        output = dedent(
            """\
        Settings for enp2s0:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: pumbg
        Wake-on: g
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.execute_ethtool_command(device_name="enp2s0") == output

    def test_execute_ethtool_command_with_namespace(self, ethtool):
        ethtool.execute_ethtool_command(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_execute_ethtool_command_with_execution_error(self, ethtool):
        ethtool._connection.execute_command.side_effect = EthtoolExecutionError(returncode=1, cmd="ethtool enp2s0")
        with pytest.raises(EthtoolExecutionError):
            ethtool.execute_ethtool_command(device_name="enp2s0")

    def test_execute_ethtool_command_error_in_output_expected_rc(self, ethtool):
        output = ""
        error = "Cannot set device ring parameters: Invalid argument\n"
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=81, stderr=error
        )
        assert (
            ethtool.execute_ethtool_command(device_name="enp2s0", option="-G", params="tx 1", succeed_codes={0, 80, 81})
            == output
        )

    def test_execute_ethtool_command_with_error_in_output_and_rc_0(self, ethtool):
        output = dedent(
            """\
        Settings for enp2s0:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
            """
        )
        error = "Cannot get wake-on-lan settings: Operation not permitted"
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=error
        )
        with pytest.raises(EthtoolException, match=f"Error while running ethtool command: {error}"):
            ethtool.execute_ethtool_command(device_name="enp2s0")

    def test_get_standard_device_info(self, ethtool):
        output = dedent(
            """\
        Settings for enp2s0:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: pumbg
        Wake-on: g
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
            """
        )
        expected_output_dict = {
            "supported_ports": ["TP"],
            "supported_link_modes": [
                "10baseT/Half",
                "10baseT/Full",
                "100baseT/Half",
                "100baseT/Full",
                "1000baseT/Full",
            ],
            "supported_pause_frame_use": ["Symmetric"],
            "supports_auto_negotiation": ["Yes"],
            "supported_fec_modes": ["Not reported"],
            "advertised_link_modes": [
                "10baseT/Half",
                "10baseT/Full",
                "100baseT/Half",
                "100baseT/Full",
                "1000baseT/Full",
            ],
            "advertised_pause_frame_use": ["Symmetric"],
            "advertised_auto_negotiation": ["Yes"],
            "advertised_fec_modes": ["Not reported"],
            "speed": ["1000Mb/s"],
            "duplex": ["Full"],
            "port": ["Twisted Pair"],
            "auto_negotiation": ["on"],
            "mdi_x": ["off (auto)"],
            "current_message_level": ["0x00000007 (7)", "drv probe link"],
            "link_detected": ["yes"],
            "phyad": ["1"],
            "transceiver": ["internal"],
            "supports_wake_on": ["pumbg"],
            "wake_on": ["g"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_standard_device_info(device_name="enp2s0")) == expected_output_dict

    def test_get_standard_device_info_with_namespace(self, ethtool):
        output = dedent(
            """\
        Settings for enp2s0:
        Supported ports: [ TP ]
        Supported link modes:   10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Supported pause frame use: Symmetric
        Supports auto-negotiation: Yes
        Supported FEC modes: Not reported
        Advertised link modes:  10baseT/Half 10baseT/Full
                                100baseT/Half 100baseT/Full
                                1000baseT/Full
        Advertised pause frame use: Symmetric
        Advertised auto-negotiation: Yes
        Advertised FEC modes: Not reported
        Speed: 1000Mb/s
        Duplex: Full
        Port: Twisted Pair
        PHYAD: 1
        Transceiver: internal
        Auto-negotiation: on
        MDI-X: off (auto)
        Supports Wake-on: pumbg
        Wake-on: g
        Current message level: 0x00000007 (7)
                               drv probe link
        Link detected: yes
            """
        )
        expected_output_dict = {
            "supported_ports": ["TP"],
            "supported_link_modes": [
                "10baseT/Half",
                "10baseT/Full",
                "100baseT/Half",
                "100baseT/Full",
                "1000baseT/Full",
            ],
            "supported_pause_frame_use": ["Symmetric"],
            "supports_auto_negotiation": ["Yes"],
            "supported_fec_modes": ["Not reported"],
            "advertised_link_modes": [
                "10baseT/Half",
                "10baseT/Full",
                "100baseT/Half",
                "100baseT/Full",
                "1000baseT/Full",
            ],
            "advertised_pause_frame_use": ["Symmetric"],
            "advertised_auto_negotiation": ["Yes"],
            "advertised_fec_modes": ["Not reported"],
            "speed": ["1000Mb/s"],
            "duplex": ["Full"],
            "port": ["Twisted Pair"],
            "auto_negotiation": ["on"],
            "mdi_x": ["off (auto)"],
            "current_message_level": ["0x00000007 (7)", "drv probe link"],
            "link_detected": ["yes"],
            "phyad": ["1"],
            "transceiver": ["internal"],
            "supports_wake_on": ["pumbg"],
            "wake_on": ["g"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_standard_device_info(device_name="enp2s0", namespace="NS1")) == expected_output_dict
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_show_dev_info_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_standard_device_info(device_name="enp2s0")

    def test_get_pause_options(self, ethtool):
        output = dedent(
            """\
        Pause parameters for enp2s0:
        Autonegotiate:  on
        RX:             on
        TX:             on
            """
        )
        expected_output = {
            "autonegotiate": ["on"],
            "rx": ["on"],
            "tx": ["on"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="'ethtool -a enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_pause_options(device_name="enp2s0")) == expected_output

    def test_get_pause_options_with_namespace(self, ethtool):
        output = dedent(
            """\
        Pause parameters for enp2s0:
        Autonegotiate:  on
        RX:             on
        TX:             on
            """
        )
        expected_output = {
            "autonegotiate": ["on"],
            "rx": ["on"],
            "tx": ["on"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="'ethtool -a enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_pause_options(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -a enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_pause_options_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -a enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_pause_options(device_name="enp2s0")

    def test_set_pause_options(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -A enp2s0 autoneg off", stdout="", return_code=0, stderr=""
        )
        ethtool.set_pause_options(device_name="enp2s0", param_name="autoneg", param_value="off")

    def test_set_pause_options_with_namespace(self, ethtool):
        ethtool.set_pause_options(device_name="enp2s0", param_name="autoneg", param_value="off", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -A enp2s0 autoneg off",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_coalesce_options(self, ethtool):
        output = dedent(
            """\
        Coalesce parameters for enp2s0:
        Adaptive RX: off  TX: off
        stats-block-usecs: 0
        sample-interval: 0
        pkt-rate-low: 0
        pkt-rate-high: 0

        rx-usecs.nic: 0
        rx-frames: 0
        rx-usecs-irq: 0
        rx-frames-irq: 0

        tx-usecs: 0
        tx-frames: 0
        tx-usecs-irq: 0
        tx-frames-irq: 0

        rx-usecs-low: 0
        rx-frame-low: 0
        tx-usecs-low: 0
        tx-frame-low: 0

        rx-usecs-high: 0
        rx-frame-high: 0
        tx-usecs-high: 0
        tx-frame-high: 0
        CQE mode RX: n/a  TX: n/a
        """
        )
        expected_output = {
            "adaptive_rx": ["off"],
            "adaptive_tx": ["off"],
            "stats_block_usecs": ["0"],
            "sample_interval": ["0"],
            "pkt_rate_low": ["0"],
            "pkt_rate_high": ["0"],
            "rx_usecs_nic": ["0"],
            "rx_frames": ["0"],
            "rx_usecs_irq": ["0"],
            "rx_frames_irq": ["0"],
            "tx_usecs": ["0"],
            "tx_frames": ["0"],
            "tx_usecs_irq": ["0"],
            "tx_frames_irq": ["0"],
            "rx_usecs_low": ["0"],
            "rx_frame_low": ["0"],
            "tx_usecs_low": ["0"],
            "tx_frame_low": ["0"],
            "rx_usecs_high": ["0"],
            "rx_frame_high": ["0"],
            "tx_usecs_high": ["0"],
            "tx_frame_high": ["0"],
            "cqe_mode_rx": ["n/a"],
            "cqe_mode_tx": ["n/a"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -c enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_coalesce_options(device_name="enp2s0")) == expected_output

    def test_get_coalesce_options_with_namespace(self, ethtool):
        output = dedent(
            """\
        Coalesce parameters for enp2s0:
        Adaptive RX: off  TX: off
        stats-block-usecs: 0
        sample-interval: 0
        pkt-rate-low: 0
        pkt-rate-high: 0

        rx-usecs.nic: 0
        rx-frames: 0
        rx-usecs-irq: 0
        rx-frames-irq: 0

        tx-usecs: 0
        tx-frames: 0
        tx-usecs-irq: 0
        tx-frames-irq: 0

        rx-usecs-low: 0
        rx-frame-low: 0
        tx-usecs-low: 0
        tx-frame-low: 0

        rx-usecs-high: 0
        rx-frame-high: 0
        tx-usecs-high: 0
        tx-frame-high: 0
                """
        )
        expected_output = {
            "adaptive_rx": ["off"],
            "adaptive_tx": ["off"],
            "stats_block_usecs": ["0"],
            "sample_interval": ["0"],
            "pkt_rate_low": ["0"],
            "pkt_rate_high": ["0"],
            "rx_usecs_nic": ["0"],
            "rx_frames": ["0"],
            "rx_usecs_irq": ["0"],
            "rx_frames_irq": ["0"],
            "tx_usecs": ["0"],
            "tx_frames": ["0"],
            "tx_usecs_irq": ["0"],
            "tx_frames_irq": ["0"],
            "rx_usecs_low": ["0"],
            "rx_frame_low": ["0"],
            "tx_usecs_low": ["0"],
            "tx_frame_low": ["0"],
            "rx_usecs_high": ["0"],
            "rx_frame_high": ["0"],
            "tx_usecs_high": ["0"],
            "tx_frame_high": ["0"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -c enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_coalesce_options(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -c enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_coalesce_options_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -c enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_coalesce_options(device_name="enp2s0")

    def test_set_coalesce_options(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -C enp2s0 rx-usecs 1", stdout="", return_code=0, stderr=""
        )
        ethtool.set_coalesce_options(device_name="enp2s0", param_name="rx-usecs", param_value="1")

    def test_set_coalesce_options_with_namespace(self, ethtool):
        ethtool.set_coalesce_options(device_name="enp2s0", param_name="rx-usecs", param_value="1", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -C enp2s0 rx-usecs 1",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_ring_parameters(self, ethtool):
        output = dedent(
            """\
        Ring parameters for enp2s0:
        Pre-set maximums:
        RX:             4096
        RX Mini:        0
        RX Jumbo:       0
        TX:             4096
        Current hardware settings:
        RX:             256
        RX Mini:        0
        RX Jumbo:       0
        TX:             256
            """
        )
        expected_output = {
            "preset_max_rx": ["4096"],
            "preset_max_rx_mini": ["0"],
            "preset_max_rx_jumbo": ["0"],
            "preset_max_tx": ["4096"],
            "current_hw_rx": ["256"],
            "current_hw_rx_mini": ["0"],
            "current_hw_rx_jumbo": ["0"],
            "current_hw_tx": ["256"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_ring_parameters(device_name="enp2s0")) == expected_output

    def test_get_ring_parameters_with_namespace(self, ethtool):
        output = dedent(
            """\
        Ring parameters for enp2s0:
        Pre-set maximums:
        RX:             4096
        RX Mini:        0
        RX Jumbo:       0
        TX:             4096
        Current hardware settings:
        RX:             256
        RX Mini:        0
        RX Jumbo:       0
        TX:             256
            """
        )
        expected_output = {
            "preset_max_rx": ["4096"],
            "preset_max_rx_mini": ["0"],
            "preset_max_rx_jumbo": ["0"],
            "preset_max_tx": ["4096"],
            "current_hw_rx": ["256"],
            "current_hw_rx_mini": ["0"],
            "current_hw_rx_jumbo": ["0"],
            "current_hw_tx": ["256"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_ring_parameters(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -g enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_ring_parameters_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -g enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_ring_parameters(device_name="enp2s0")

    def test_set_ring_parameters(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -G enp2s0 rx 512", stdout="", return_code=0, stderr=""
        )
        ethtool.set_ring_parameters(device_name="eno1", param_name="rx", param_value="512")

    def test_set_ring_parameters_with_namespace(self, ethtool):
        ethtool.set_ring_parameters(device_name="enp2s0", param_name="rx", param_value="512", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -G enp2s0 rx 512",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_driver_information(self, ethtool):
        output = dedent(
            """\
        driver: igb
        version: 5.4.0-k
        firmware-version: 3.16.0
        expansion-rom-version:
        bus-info: 0000:02:00.0
        supports-statistics: yes
        supports-test: yes
        supports-eeprom-access: yes
        supports-register-dump: yes
        supports-priv-flags: yes
            """
        )
        expected_output = {
            "driver": ["igb"],
            "version": ["5.4.0-k"],
            "firmware_version": ["3.16.0"],
            "expansion_rom_version": [""],
            "bus_info": ["0000:02:00.0"],
            "supports_statistics": ["yes"],
            "supports_test": ["yes"],
            "supports_eeprom_access": ["yes"],
            "supports_register_dump": ["yes"],
            "supports_priv_flags": ["yes"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_driver_information(device_name="enp2s0")) == expected_output

    def test_get_driver_information_with_namespace(self, ethtool):
        output = dedent(
            """\
        driver: igb
        version: 5.4.0-k
        firmware-version: 3.16.0
        expansion-rom-version:
        bus-info: 0000:02:00.0
        supports-statistics: yes
        supports-test: yes
        supports-eeprom-access: yes
        supports-register-dump: yes
        supports-priv-flags: yes
            """
        )
        expected_output = {
            "driver": ["igb"],
            "version": ["5.4.0-k"],
            "firmware_version": ["3.16.0"],
            "expansion_rom_version": [""],
            "bus_info": ["0000:02:00.0"],
            "supports_statistics": ["yes"],
            "supports_test": ["yes"],
            "supports_eeprom_access": ["yes"],
            "supports_register_dump": ["yes"],
            "supports_priv_flags": ["yes"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_driver_information(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -i enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_driver_information_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -i enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_driver_information(device_name="enp2s0")

    def test_get_protocol_offload_and_feature_stat(self, ethtool):
        output = dedent(
            """\
        Features for enp2s0:
        rx-checksumming: on
        tx-checksumming: on
                tx-checksum-ipv4: off [fixed]
                tx-checksum-ip-generic: on
                tx-checksum-ipv6: off [fixed]
                tx-checksum-fcoe-crc: off [fixed]
                tx-checksum-sctp: on
        scatter-gather: on
                tx-scatter-gather: on
                tx-scatter-gather-fraglist: off [fixed]
        tcp-segmentation-offload: on
                tx-tcp-segmentation: on
                tx-tcp-ecn-segmentation: off [fixed]
                tx-tcp-mangleid-segmentation: off
                tx-tcp6-segmentation: on
        udp-fragmentation-offload: off
        generic-segmentation-offload: on
        generic-receive-offload: on
        large-receive-offload: off [fixed]
        rx-vlan-offload: on
        tx-vlan-offload: on
        ntuple-filters: off
        receive-hashing: on
        highdma: on [fixed]
        rx-vlan-filter: on [fixed]
        vlan-challenged: off [fixed]
        tx-lockless: off [fixed]
        netns-local: off [fixed]
        tx-gso-robust: off [fixed]
        tx-fcoe-segmentation: off [fixed]
        tx-gre-segmentation: on
        tx-gre-csum-segmentation: on
        tx-ipxip4-segmentation: on
        tx-ipxip6-segmentation: on
        tx-udp_tnl-segmentation: on
        tx-udp_tnl-csum-segmentation: on
        tx-gso-partial: on
        tx-sctp-segmentation: off [fixed]
        tx-esp-segmentation: off [fixed]
        fcoe-mtu: off [fixed]
        tx-nocache-copy: off
        loopback: off [fixed]
        rx-fcs: off [fixed]
        rx-all: off
        tx-vlan-stag-hw-insert: off [fixed]
        rx-vlan-stag-hw-parse: off [fixed]
        rx-vlan-stag-filter: off [fixed]
        l2-fwd-offload: off [fixed]
        hw-tc-offload: off [fixed]
        esp-hw-offload: off [fixed]
        esp-tx-csum-hw-offload: off [fixed]
        rx-udp_tunnel-port-offload: off [fixed]
            """
        )
        expected_output = {
            "rx_checksumming": ["on"],
            "tx_checksumming": ["on"],
            "tx_checksum_ipv4": ["off [fixed]"],
            "tx_checksum_ip_generic": ["on"],
            "tx_checksum_ipv6": ["off [fixed]"],
            "tx_checksum_fcoe_crc": ["off [fixed]"],
            "tx_checksum_sctp": ["on"],
            "scatter_gather": ["on"],
            "tx_scatter_gather": ["on"],
            "tx_scatter_gather_fraglist": ["off [fixed]"],
            "tcp_segmentation_offload": ["on"],
            "tx_tcp_segmentation": ["on"],
            "tx_tcp_ecn_segmentation": ["off [fixed]"],
            "tx_tcp_mangleid_segmentation": ["off"],
            "tx_tcp6_segmentation": ["on"],
            "udp_fragmentation_offload": ["off"],
            "generic_segmentation_offload": ["on"],
            "generic_receive_offload": ["on"],
            "large_receive_offload": ["off [fixed]"],
            "rx_vlan_offload": ["on"],
            "tx_vlan_offload": ["on"],
            "ntuple_filters": ["off"],
            "receive_hashing": ["on"],
            "highdma": ["on [fixed]"],
            "rx_vlan_filter": ["on [fixed]"],
            "vlan_challenged": ["off [fixed]"],
            "tx_lockless": ["off [fixed]"],
            "netns_local": ["off [fixed]"],
            "tx_gso_robust": ["off [fixed]"],
            "tx_fcoe_segmentation": ["off [fixed]"],
            "tx_gre_segmentation": ["on"],
            "tx_gre_csum_segmentation": ["on"],
            "tx_ipxip4_segmentation": ["on"],
            "tx_ipxip6_segmentation": ["on"],
            "tx_udp_tnl_segmentation": ["on"],
            "tx_udp_tnl_csum_segmentation": ["on"],
            "tx_gso_partial": ["on"],
            "tx_sctp_segmentation": ["off [fixed]"],
            "tx_esp_segmentation": ["off [fixed]"],
            "fcoe_mtu": ["off [fixed]"],
            "tx_nocache_copy": ["off"],
            "loopback": ["off [fixed]"],
            "rx_fcs": ["off [fixed]"],
            "rx_all": ["off"],
            "tx_vlan_stag_hw_insert": ["off [fixed]"],
            "rx_vlan_stag_hw_parse": ["off [fixed]"],
            "rx_vlan_stag_filter": ["off [fixed]"],
            "l2_fwd_offload": ["off [fixed]"],
            "hw_tc_offload": ["off [fixed]"],
            "esp_hw_offload": ["off [fixed]"],
            "esp_tx_csum_hw_offload": ["off [fixed]"],
            "rx_udp_tunnel_port_offload": ["off [fixed]"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -k enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_protocol_offload_and_feature_state(device_name="enp2s0")) == expected_output

    def test_get_protocol_offload_and_feature_state_with_namespace(self, ethtool):
        output = dedent(
            """\
        Features for enp2s0:
        rx-checksumming: on
        tx-checksumming: on
                tx-checksum-ipv4: off [fixed]
                tx-checksum-ip-generic: on
                tx-checksum-ipv6: off [fixed]
                tx-checksum-fcoe-crc: off [fixed]
                tx-checksum-sctp: on
        scatter-gather: on
                tx-scatter-gather: on
                tx-scatter-gather-fraglist: off [fixed]
        tcp-segmentation-offload: on
                tx-tcp-segmentation: on
                tx-tcp-ecn-segmentation: off [fixed]
                tx-tcp-mangleid-segmentation: off
                tx-tcp6-segmentation: on
        udp-fragmentation-offload: off
        generic-segmentation-offload: on
        generic-receive-offload: on
        large-receive-offload: off [fixed]
        rx-vlan-offload: on
        tx-vlan-offload: on
        ntuple-filters: off
        receive-hashing: on
        highdma: on [fixed]
        rx-vlan-filter: on [fixed]
        vlan-challenged: off [fixed]
        tx-lockless: off [fixed]
        netns-local: off [fixed]
        tx-gso-robust: off [fixed]
        tx-fcoe-segmentation: off [fixed]
        tx-gre-segmentation: on
        tx-gre-csum-segmentation: on
        tx-ipxip4-segmentation: on
        tx-ipxip6-segmentation: on
        tx-udp_tnl-segmentation: on
        tx-udp_tnl-csum-segmentation: on
        tx-gso-partial: on
        tx-sctp-segmentation: off [fixed]
        tx-esp-segmentation: off [fixed]
        fcoe-mtu: off [fixed]
        tx-nocache-copy: off
        loopback: off [fixed]
        rx-fcs: off [fixed]
        rx-all: off
        tx-vlan-stag-hw-insert: off [fixed]
        rx-vlan-stag-hw-parse: off [fixed]
        rx-vlan-stag-filter: off [fixed]
        l2-fwd-offload: off [fixed]
        hw-tc-offload: off [fixed]
        esp-hw-offload: off [fixed]
        esp-tx-csum-hw-offload: off [fixed]
        rx-udp_tunnel-port-offload: off [fixed]
            """
        )
        expected_output = {
            "rx_checksumming": ["on"],
            "tx_checksumming": ["on"],
            "tx_checksum_ipv4": ["off [fixed]"],
            "tx_checksum_ip_generic": ["on"],
            "tx_checksum_ipv6": ["off [fixed]"],
            "tx_checksum_fcoe_crc": ["off [fixed]"],
            "tx_checksum_sctp": ["on"],
            "scatter_gather": ["on"],
            "tx_scatter_gather": ["on"],
            "tx_scatter_gather_fraglist": ["off [fixed]"],
            "tcp_segmentation_offload": ["on"],
            "tx_tcp_segmentation": ["on"],
            "tx_tcp_ecn_segmentation": ["off [fixed]"],
            "tx_tcp_mangleid_segmentation": ["off"],
            "tx_tcp6_segmentation": ["on"],
            "udp_fragmentation_offload": ["off"],
            "generic_segmentation_offload": ["on"],
            "generic_receive_offload": ["on"],
            "large_receive_offload": ["off [fixed]"],
            "rx_vlan_offload": ["on"],
            "tx_vlan_offload": ["on"],
            "ntuple_filters": ["off"],
            "receive_hashing": ["on"],
            "highdma": ["on [fixed]"],
            "rx_vlan_filter": ["on [fixed]"],
            "vlan_challenged": ["off [fixed]"],
            "tx_lockless": ["off [fixed]"],
            "netns_local": ["off [fixed]"],
            "tx_gso_robust": ["off [fixed]"],
            "tx_fcoe_segmentation": ["off [fixed]"],
            "tx_gre_segmentation": ["on"],
            "tx_gre_csum_segmentation": ["on"],
            "tx_ipxip4_segmentation": ["on"],
            "tx_ipxip6_segmentation": ["on"],
            "tx_udp_tnl_segmentation": ["on"],
            "tx_udp_tnl_csum_segmentation": ["on"],
            "tx_gso_partial": ["on"],
            "tx_sctp_segmentation": ["off [fixed]"],
            "tx_esp_segmentation": ["off [fixed]"],
            "fcoe_mtu": ["off [fixed]"],
            "tx_nocache_copy": ["off"],
            "loopback": ["off [fixed]"],
            "rx_fcs": ["off [fixed]"],
            "rx_all": ["off"],
            "tx_vlan_stag_hw_insert": ["off [fixed]"],
            "rx_vlan_stag_hw_parse": ["off [fixed]"],
            "rx_vlan_stag_filter": ["off [fixed]"],
            "l2_fwd_offload": ["off [fixed]"],
            "hw_tc_offload": ["off [fixed]"],
            "esp_hw_offload": ["off [fixed]"],
            "esp_tx_csum_hw_offload": ["off [fixed]"],
            "rx_udp_tunnel_port_offload": ["off [fixed]"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -k enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert (
            asdict(ethtool.get_protocol_offload_and_feature_state(device_name="enp2s0", namespace="NS1"))
            == expected_output
        )
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -k enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_protocol_offload_and_feature_state_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -k enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_protocol_offload_and_feature_state(device_name="enp2s0")

    def test_set_protocol_offload_and_feature_state(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -K enp2s0 tso on", stdout="", return_code=0, stderr=""
        )
        ethtool.set_protocol_offload_and_feature_state(device_name="enp2s0", param_name="tso", param_value="on")

    def test_set_protocol_offload_and_feature_state_with_namespace(self, ethtool):
        ethtool.set_protocol_offload_and_feature_state(
            device_name="enp2s0", param_name="tso", param_value="on", namespace="NS1"
        )
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -K enp2s0 tso on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_channel_parameters(self, ethtool):
        output = dedent(
            """\
        Channel parameters for enp2s0:
        Pre-set maximums:
        RX:             0
        TX:             0
        Other:          1
        Combined:       4
        Current hardware settings:
        RX:             0
        TX:             0
        Other:          1
        Combined:       4
            """
        )
        expected_output = {
            "preset_max_rx": ["0"],
            "preset_max_tx": ["0"],
            "preset_max_other": ["1"],
            "preset_max_combined": ["4"],
            "current_hw_rx": ["0"],
            "current_hw_tx": ["0"],
            "current_hw_other": ["1"],
            "current_hw_combined": ["4"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -l enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_channel_parameters(device_name="enp2s0")) == expected_output

    def test_get_channel_parameters_with_namespace(self, ethtool):
        output = dedent(
            """\
        Channel parameters for enp2s0:
        Pre-set maximums:
        RX:             0
        TX:             0
        Other:          1
        Combined:       4
        Current hardware settings:
        RX:             0
        TX:             0
        Other:          1
        Combined:       4
            """
        )
        expected_output = {
            "preset_max_rx": ["0"],
            "preset_max_tx": ["0"],
            "preset_max_other": ["1"],
            "preset_max_combined": ["4"],
            "current_hw_rx": ["0"],
            "current_hw_tx": ["0"],
            "current_hw_other": ["1"],
            "current_hw_combined": ["4"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -l enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_channel_parameters(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -l enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_channel_parameters_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -l enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_channel_parameters(device_name="enp2s0")

    def test_set_channel_parameters(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -L enp2s0 combined 2", stdout="", return_code=0, stderr=""
        )
        ethtool.set_channel_parameters(device_name="enp2s0", param_name="combined", param_value="2")

    def test_set_channel_parameters_rx(self, ethtool, mocker):
        current_tx = 100
        rx = 10
        device_name = "eth1"
        channel_params = ChannelParams(current_hw_rx=[20], current_hw_tx=[current_tx])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)

        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command
        ethtool.set_channel_parameters(device_name=device_name, param_name="rx", param_value=rx)
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} rx {rx} tx {current_tx}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_channel_parameters_tx(self, ethtool, mocker):
        current_rx = 100
        tx = 10
        device_name = "eth1"
        channel_params = ChannelParams(current_hw_tx=[tx], current_hw_rx=[current_rx])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)

        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command
        ethtool.set_channel_parameters(device_name=device_name, param_name="tx", param_value=tx)
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} tx {tx} rx {current_rx}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize("param_name, param_value", [("other", 10), ("combined", 10)])
    def test_set_channel_parameters_other_combined(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters(device_name=device_name, param_name=param_name, param_value=param_value)
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} {param_name} {param_value}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_channel_parameters_rx_tx_pass(self, ethtool, mocker):
        device_name = "eth1"
        param_name = "rx tx"
        param_value = "10 20"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters(device_name=device_name, param_name=param_name, param_value=param_value)
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} rx 10 tx 20",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_channel_parameters_rx_tx_error(self, ethtool, mocker):
        device_name = "eth1"
        param_name = "rx tx"
        param_value = "1020"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command
        with pytest.raises(EthtoolException):
            ethtool.set_channel_parameters(device_name=device_name, param_name=param_name, param_value=param_value)

    def test_set_channel_parameters_error(self, ethtool):
        with pytest.raises(EthtoolException):
            ethtool.set_channel_parameters(device_name="device_name", param_name="so wroong", param_value=1)

    def test_set_channel_parameters_with_namespace(self, ethtool):
        ethtool.set_channel_parameters(device_name="enp2s0", param_name="combined", param_value="2", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -L enp2s0 combined 2",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize("param_name, param_value", [("rx", "10"), ("tx", "10")])
    def test_set_channel_parameters_ice_idpf_aligned(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        channel_params = ChannelParams(current_hw_tx=["0"], current_hw_rx=["0"])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} {param_name} {param_value}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_channel_parameters_ice_idpf_aligned_combined_rx(self, ethtool, mocker):
        device_name = "eth1"
        param_name = "combined rx"
        param_value = "10 10"
        channel_params = ChannelParams(current_hw_tx=["0"], current_hw_rx=["0"])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} combined 10 rx 10",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_channel_parameters_ice_idpf_aligned_combined_tx(self, ethtool, mocker):
        device_name = "eth1"
        param_name = "combined tx"
        param_value = "10 10"
        channel_params = ChannelParams(current_hw_tx=["0"], current_hw_rx=["0"])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} combined 10 tx 10",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize(
        "param_name, param_value", [("rx", "10"), ("tx", "10"), ("combined rx", "10 10"), ("combined tx", "10 10")]
    )
    def test_set_channel_parameters_ice_idpf_aligned_index_error(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        channel_params = ChannelParams(current_hw_tx=[], current_hw_rx=[])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        with pytest.raises(EthtoolException):
            ethtool.set_channel_parameters_ice_idpf_aligned(
                device_name=device_name, param_name=param_name, param_value=param_value
            )

    @pytest.mark.parametrize(
        "param_name, param_value",
        [
            ("rx", "10"),
            ("tx", "10"),
            ("combined rx tx", "20 10 3"),
            ("rx tx", "24 21"),
            ("combined rx tx", "20 3 10"),
            ("combined", "0"),
            ("combined rx", "10"),
            ("combined tx", "10"),
        ],
    )
    def test_set_channel_parameters_ice_idpf_aligned_error(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        channel_params = ChannelParams(current_hw_tx=["10"], current_hw_rx=["10"])
        ethtool.get_channel_parameters = mocker.Mock(return_value=channel_params)
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        with pytest.raises(EthtoolException):
            ethtool.set_channel_parameters_ice_idpf_aligned(
                device_name=device_name, param_name=param_name, param_value=param_value
            )

    @pytest.mark.parametrize("param_name, param_value", [("rx tx", "10 0"), ("rx tx", "0 10")])
    def test_set_channel_parameters_ice_idpf_aligned_both(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        rx_value, tx_value = param_value.strip().split(" ")
        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} rx {rx_value} tx {tx_value}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize("param_name, param_value", [("combined rx tx", "20 10 0"), ("combined rx tx", "20 0 10")])
    def test_set_channel_parameters_ice_idpf_aligned_combined(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        combined_value, rx_value, tx_value = param_value.strip().split(" ")
        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} combined {combined_value} rx {rx_value} tx {tx_value}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize("param_name, param_value", [("other", 10), ("combined", 10)])
    def test_set_channel_parameters_ice_idpf_aligned_other_combined(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command

        ethtool.set_channel_parameters_ice_idpf_aligned(
            device_name=device_name, param_name=param_name, param_value=param_value
        )
        mock_execute_command.assert_called_with(
            f"ethtool -L {device_name} {param_name} {param_value}",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    @pytest.mark.parametrize(
        "param_name, param_value",
        [("rx tx", "1020"), ("combined rx tx", "1020"), ("combined", "0"), ("blah blah", "20")],
    )
    def test_set_channel_parameters_ice_idpf_alligned_rx_tx_error(self, ethtool, mocker, param_name, param_value):
        device_name = "eth1"
        mock_execute_command = mocker.Mock(
            return_value=ConnectionCompletedProcess(return_code=0, args="", stderr="", stdout="")
        )
        ethtool._connection.execute_command = mock_execute_command
        with pytest.raises(EthtoolException):
            ethtool.set_channel_parameters_ice_idpf_aligned(
                device_name=device_name, param_name=param_name, param_value=param_value
            )

    def test_get_receive_network_flow_classification(self, ethtool):
        output = dedent(
            """\
        4 RX rings available
        Total 0 rules

            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -u enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.get_receive_network_flow_classification(device_name="enp2s0") == output

    def test_get_receive_network_flow_classification_n(self, ethtool):
        output = dedent(
            """\
        64 RX rings available
        Total 0 rules

            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -n enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert (
            ethtool.get_receive_network_flow_classification(
                device_name="enp2s0", option=GetReceiveNetworkFlowClassification.N
            )
            == output
        )

    def test_get_receive_network_flow_classification_n_rx_flow_hash(self, ethtool):
        output = dedent(
            """\
        64 RX rings available
        Total 0 rules

            """
        )
        # ethtool -n ethX rx-flow-hash <transport_protocol><ip_version>
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -n enp2s0 rx-flow-hash tcp4", stdout=output, return_code=0, stderr=""
        )
        assert (
            ethtool.get_receive_network_flow_classification(
                device_name="enp2s0",
                param_name="rx-flow-hash",
                param_value="tcp4",
                option=GetReceiveNetworkFlowClassification.N,
            )
            == output
        )

    def test_get_receive_network_flow_classification_not_supported_option(self, ethtool):
        with pytest.raises(EthtoolException, match=re.escape("Incorrect option for ethtool command: unknown")):
            ethtool.get_receive_network_flow_classification(device_name="enp2s0", option="unknown")

    def test_get_receive_network_flow_classification_with_namespace(self, ethtool):
        ethtool.get_receive_network_flow_classification(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -u enp2s0  ", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_receive_network_flow_classification_with_parameters(self, ethtool):
        output = dedent(
            """\
        TCP over IPV4 flows use these fields for computing Hash flow key:
        IP SA
        IP DA
        L4 bytes 0 & 1 [TCP/UDP src port]
        L4 bytes 2 & 3 [TCP/UDP dst port]

            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -u enp2s0 rx-flow-hash tcp4", stdout=output, return_code=0, stderr=""
        )
        assert (
            ethtool.get_receive_network_flow_classification(
                device_name="enp2s0", param_name="rx-flow-hash", param_value="tcp4"
            )
            == output
        )

    def test_set_receive_network_flow_classification(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -U enp2s0 flow-type ip4 proto 1 action -1", stdout="", return_code=0, stderr=""
        )
        ethtool.set_receive_network_flow_classification(device_name="enp2s0", params="flow-type ip4 proto 1 action -1")

    def test_set_receive_network_flow_classification_with_namespace(self, ethtool):
        ethtool.set_receive_network_flow_classification(
            device_name="enp2s0", params="flow-type ip4 proto 1 action -1", namespace="NS1"
        )
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -U enp2s0 flow-type ip4 proto 1 action -1",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_receive_network_flow_classification_N_option(self, ethtool):
        ethtool.set_receive_network_flow_classification(
            device_name="enp2s0", option=SetReceiveNetworkFlowClassification.N, params="flow-type proto 1 ip4 sdfn"
        )
        # ethtool -N ethX rx-flow-hash <transport_protocol> <ip_version> sdfn
        ethtool._connection.execute_command.assert_called_with(
            "ethtool -N enp2s0 flow-type proto 1 ip4 sdfn",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_receive_network_flow_classification_not_supported_option(self, ethtool):
        with pytest.raises(EthtoolException, match=re.escape("Incorrect option for ethtool command: unknown")):
            ethtool.set_receive_network_flow_classification(
                device_name="enp2s0", params="some params", option="unknown"
            )

    def test_show_visible_port_identification(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -p eno1 5", stdout="", return_code=0, stderr=""
        )
        ethtool.show_visible_port_identification(device_name="enp2s0", duration=5)

    def test_show_visible_port_identification_with_namespace(self, ethtool):
        ethtool.show_visible_port_identification(device_name="enp2s0", duration=5, namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -p enp2s0 5", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_change_eeprom_settings(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -E enp2s0 offset 0x12 value 0x41", stdout="", return_code=0, stderr=""
        )
        ethtool.change_eeprom_settings(device_name="enp2s0", params="offset 0x12 value 0x41")

    def test_change_eeprom_settings_with_namespace(self, ethtool):
        ethtool.change_eeprom_settings(device_name="enp2s0", params="offset 0x12 value 0x41", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -E enp2s0 offset 0x12 value 0x41",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_do_eeprom_dump(self, ethtool):
        output = dedent(
            """\
        Offset          Values
        ------          ------
        0x0012:         00 00 2f 40 00 00 ff ff 33 15 86 80 67 b3 02 80
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -e enp2s0 length 16 offset 0x12", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.do_eeprom_dump(device_name="enp2s0") == output

    def test_do_eeprom_dump_with_namespace(self, ethtool):
        ethtool.do_eeprom_dump(device_name="enp2s0", params="length 16 offset 0x12", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -e enp2s0 length 16 offset 0x12",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_restart_negotiation(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -r enp2s0", stdout="", return_code=0, stderr=""
        )
        ethtool.restart_negotiation(device_name="enp2s0")

    def test_restart_negotiation_with_namespace(self, ethtool):
        ethtool.restart_negotiation(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -r enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_adapter_statistics(self, ethtool):
        output = dedent(
            """\
        NIC statistics:
            rx_packets: 52924116
            tx_packets: 6831559
            rx_bytes.nic: 23486721711
            tx_bytes.nic: 1592747875
            rx_broadcast: 17950853
            tx_broadcast: 83
            rx_multicast: 15401567
            tx_multicast: 46633
            multicast: 15401567
            collisions: 0
            rx_crc_errors: 0
            rx_no_buffer_count: 0
            rx_missed_errors: 0
            tx_aborted_errors: 0
            tx_carrier_errors: 0
            tx_window_errors: 0
            tx_abort_late_coll: 0
            tx_deferred_ok: 0
            tx_single_coll_ok: 0
            tx_multi_coll_ok: 0
            tx_timeout_count: 0
            rx_long_length_errors: 0
            rx_short_length_errors: 0
            rx_align_errors: 0
            tx_tcp_seg_good: 439677
            tx_tcp_seg_failed: 0
            rx_flow_control_xon: 0
            rx_flow_control_xoff: 0
            tx_flow_control_xon: 0
            tx_flow_control_xoff: 0
            rx_long_byte_count: 23486721711
            tx_dma_out_of_sync: 0
            tx_smbus: 0
            rx_smbus: 0
            dropped_smbus: 0
            os2bmc_rx_by_bmc: 0
            os2bmc_tx_by_bmc: 0
            os2bmc_tx_by_host: 0
            os2bmc_rx_by_host: 0
            tx_hwtstamp_timeouts: 0
            tx_hwtstamp_skipped: 0
            rx_hwtstamp_cleared: 0
            rx_errors: 0
            tx_errors: 0
            tx_dropped: 0
            rx_length_errors: 0
            rx_over_errors: 0
            rx_frame_errors: 0
            rx_fifo_errors: 0
            tx_fifo_errors: 0
            tx_heartbeat_errors: 0
            tx_queue_0_packets: 11813
            tx_queue_0_bytes: 1156810
            tx_queue_0_restart: 0
            tx_queue_1_packets: 23062
            tx_queue_1_bytes: 2655140
            tx_queue_1_restart: 2655140
            tx_queue_2_packets: 80570
            tx_queue_2_bytes: 39314035
            tx_queue_2_restart: 0
            tx_queue_3_packets: 5004
            tx_queue_3_bytes: 524010
            tx_queue_3_restart: 0
            rx_queue_0_packets: 578994
            rx_queue_0_bytes: 51734607
            rx_queue_0_drops: 0
            rx_queue_0_csum_err: 0
            rx_queue_0_alloc_failed: 0
            rx_queue_1_packets: 162272
            rx_queue_1_bytes: 79319788
            rx_queue_1_drops: 0
            rx_queue_1_csum_err: 0
            rx_queue_1_alloc_failed: 0
            rx_queue_2_packets: 67292
            rx_queue_2_bytes: 5850192
            rx_queue_2_drops: 0
            rx_queue_2_csum_err: 0
            rx_queue_2_alloc_failed: 0
            rx_queue_3_packets: 99976
            rx_queue_3_bytes: 16451118
            rx_queue_3_drops: 0
            rx_queue_3_csum_err: 0
            rx_queue_3_alloc_failed: 0
            """
        )
        expected_output = {
            "rx_packets": ["52924116"],
            "tx_packets": ["6831559"],
            "rx_bytes_nic": ["23486721711"],
            "tx_bytes_nic": ["1592747875"],
            "rx_broadcast": ["17950853"],
            "tx_broadcast": ["83"],
            "rx_multicast": ["15401567"],
            "tx_multicast": ["46633"],
            "multicast": ["15401567"],
            "collisions": ["0"],
            "rx_crc_errors": ["0"],
            "rx_no_buffer_count": ["0"],
            "rx_missed_errors": ["0"],
            "tx_aborted_errors": ["0"],
            "tx_carrier_errors": ["0"],
            "tx_window_errors": ["0"],
            "tx_abort_late_coll": ["0"],
            "tx_deferred_ok": ["0"],
            "tx_single_coll_ok": ["0"],
            "tx_multi_coll_ok": ["0"],
            "tx_timeout_count": ["0"],
            "rx_long_length_errors": ["0"],
            "rx_short_length_errors": ["0"],
            "rx_align_errors": ["0"],
            "tx_tcp_seg_good": ["439677"],
            "tx_tcp_seg_failed": ["0"],
            "rx_flow_control_xon": ["0"],
            "rx_flow_control_xoff": ["0"],
            "tx_flow_control_xon": ["0"],
            "tx_flow_control_xoff": ["0"],
            "rx_long_byte_count": ["23486721711"],
            "tx_dma_out_of_sync": ["0"],
            "tx_smbus": ["0"],
            "rx_smbus": ["0"],
            "dropped_smbus": ["0"],
            "os2bmc_rx_by_bmc": ["0"],
            "os2bmc_tx_by_bmc": ["0"],
            "os2bmc_tx_by_host": ["0"],
            "os2bmc_rx_by_host": ["0"],
            "tx_hwtstamp_timeouts": ["0"],
            "tx_hwtstamp_skipped": ["0"],
            "rx_hwtstamp_cleared": ["0"],
            "rx_errors": ["0"],
            "tx_errors": ["0"],
            "tx_dropped": ["0"],
            "rx_length_errors": ["0"],
            "rx_over_errors": ["0"],
            "rx_frame_errors": ["0"],
            "rx_fifo_errors": ["0"],
            "tx_fifo_errors": ["0"],
            "tx_heartbeat_errors": ["0"],
            "tx_queue_0_packets": ["11813"],
            "tx_queue_0_bytes": ["1156810"],
            "tx_queue_0_restart": ["0"],
            "tx_queue_1_packets": ["23062"],
            "tx_queue_1_bytes": ["2655140"],
            "tx_queue_1_restart": ["2655140"],
            "tx_queue_2_packets": ["80570"],
            "tx_queue_2_bytes": ["39314035"],
            "tx_queue_2_restart": ["0"],
            "tx_queue_3_packets": ["5004"],
            "tx_queue_3_bytes": ["524010"],
            "tx_queue_3_restart": ["0"],
            "rx_queue_0_packets": ["578994"],
            "rx_queue_0_bytes": ["51734607"],
            "rx_queue_0_drops": ["0"],
            "rx_queue_0_csum_err": ["0"],
            "rx_queue_0_alloc_failed": ["0"],
            "rx_queue_1_packets": ["162272"],
            "rx_queue_1_bytes": ["79319788"],
            "rx_queue_1_drops": ["0"],
            "rx_queue_1_csum_err": ["0"],
            "rx_queue_1_alloc_failed": ["0"],
            "rx_queue_2_packets": ["67292"],
            "rx_queue_2_bytes": ["5850192"],
            "rx_queue_2_drops": ["0"],
            "rx_queue_2_csum_err": ["0"],
            "rx_queue_2_alloc_failed": ["0"],
            "rx_queue_3_packets": ["99976"],
            "rx_queue_3_bytes": ["16451118"],
            "rx_queue_3_drops": ["0"],
            "rx_queue_3_csum_err": ["0"],
            "rx_queue_3_alloc_failed": ["0"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -S enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_adapter_statistics(device_name="enp2s0")) == expected_output

    def test_get_statistics_xon_xoff(self, ethtool):
        output = dedent(
            """\
        NIC statistics:
            rx_packets: 52924116
            tx_packets: 6831559
            rx_bytes.nic: 23486721711
            tx_bytes.nic: 1592747875
            rx_broadcast: 17950853
            tx_broadcast: 83
            rx_multicast: 15401567
            tx_multicast: 46633
            multicast: 15401567
            collisions: 0
            rx_crc_errors: 0
            rx_no_buffer_count: 0
            rx_missed_errors: 0
            tx_aborted_errors: 0
            tx_carrier_errors: 0
            tx_window_errors: 0
            tx_abort_late_coll: 0
            tx_deferred_ok: 0
            tx_single_coll_ok: 0
            tx_multi_coll_ok: 0
            tx_timeout_count: 0
            rx_long_length_errors: 0
            rx_short_length_errors: 0
            rx_align_errors: 0
            tx_tcp_seg_good: 439677
            tx_tcp_seg_failed: 0
            rx_flow_control_xon: 0
            rx_flow_control_xoff: 0
            tx_flow_control_xon: 0
            tx_flow_control_xoff: 0
            rx_long_byte_count: 23486721711
            tx_dma_out_of_sync: 0
            tx_smbus: 0
            rx_smbus: 0
            dropped_smbus: 0
            os2bmc_rx_by_bmc: 0
            os2bmc_tx_by_bmc: 0
            os2bmc_tx_by_host: 0
            os2bmc_rx_by_host: 0
            tx_hwtstamp_timeouts: 0
            tx_hwtstamp_skipped: 0
            rx_hwtstamp_cleared: 0
            rx_errors: 0
            tx_errors: 0
            tx_dropped: 0
            rx_length_errors: 0
            rx_over_errors: 0
            rx_frame_errors: 0
            rx_fifo_errors: 0
            tx_fifo_errors: 0
            tx_heartbeat_errors: 0
            tx_queue_0_packets: 11813
            tx_queue_0_bytes: 1156810
            tx_queue_0_restart: 0
            tx_queue_1_packets: 23062
            tx_queue_1_bytes: 2655140
            tx_queue_1_restart: 2655140
            tx_queue_2_packets: 80570
            tx_queue_2_bytes: 39314035
            tx_queue_2_restart: 0
            tx_queue_3_packets: 5004
            tx_queue_3_bytes: 524010
            tx_queue_3_restart: 0
            rx_queue_0_packets: 578994
            rx_queue_0_bytes: 51734607
            rx_queue_0_drops: 0
            rx_queue_0_csum_err: 0
            rx_queue_0_alloc_failed: 0
            rx_queue_1_packets: 162272
            rx_queue_1_bytes: 79319788
            rx_queue_1_drops: 0
            rx_queue_1_csum_err: 0
            rx_queue_1_alloc_failed: 0
            rx_queue_2_packets: 67292
            rx_queue_2_bytes: 5850192
            rx_queue_2_drops: 0
            rx_queue_2_csum_err: 0
            rx_queue_2_alloc_failed: 0
            rx_queue_3_packets: 99976
            rx_queue_3_bytes: 16451118
            rx_queue_3_drops: 0
            rx_queue_3_csum_err: 0
            rx_queue_3_alloc_failed: 0
            """
        )
        expected_output = {
            "rx_flow_control_xon": ["0"],
            "rx_flow_control_xoff": ["0"],
            "tx_flow_control_xon": ["0"],
            "tx_flow_control_xoff": ["0"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -S enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_statistics_xonn_xoff(device_name="enp2s0")) == expected_output

    def test_get_adapter_statistics_with_namespace(self, ethtool):
        output = dedent(
            """\
        NIC statistics:
            rx_packets: 52924116
            tx_packets: 6831559
            rx_bytes.nic: 23486721711
            tx_bytes.nic: 1592747875
            rx_broadcast: 17950853
            tx_broadcast: 83
            rx_multicast: 15401567
            tx_multicast: 46633
            multicast: 15401567
            collisions: 0
            rx_crc_errors: 0
            rx_no_buffer_count: 0
            rx_missed_errors: 0
            tx_aborted_errors: 0
            tx_carrier_errors: 0
            tx_window_errors: 0
            tx_abort_late_coll: 0
            tx_deferred_ok: 0
            tx_single_coll_ok: 0
            tx_multi_coll_ok: 0
            tx_timeout_count: 0
            rx_long_length_errors: 0
            rx_short_length_errors: 0
            rx_align_errors: 0
            tx_tcp_seg_good: 439677
            tx_tcp_seg_failed: 0
            rx_flow_control_xon: 0
            rx_flow_control_xoff: 0
            tx_flow_control_xon: 0
            tx_flow_control_xoff: 0
            rx_long_byte_count: 23486721711
            tx_dma_out_of_sync: 0
            tx_smbus: 0
            rx_smbus: 0
            dropped_smbus: 0
            os2bmc_rx_by_bmc: 0
            os2bmc_tx_by_bmc: 0
            os2bmc_tx_by_host: 0
            os2bmc_rx_by_host: 0
            tx_hwtstamp_timeouts: 0
            tx_hwtstamp_skipped: 0
            rx_hwtstamp_cleared: 0
            rx_errors: 0
            tx_errors: 0
            tx_dropped: 0
            rx_length_errors: 0
            rx_over_errors: 0
            rx_frame_errors: 0
            rx_fifo_errors: 0
            tx_fifo_errors: 0
            tx_heartbeat_errors: 0
            tx_queue_0_packets: 11813
            tx_queue_0_bytes: 1156810
            tx_queue_0_restart: 0
            tx_queue_1_packets: 23062
            tx_queue_1_bytes: 2655140
            tx_queue_1_restart: 2655140
            tx_queue_2_packets: 80570
            tx_queue_2_bytes: 39314035
            tx_queue_2_restart: 0
            tx_queue_3_packets: 5004
            tx_queue_3_bytes: 524010
            tx_queue_3_restart: 0
            rx_queue_0_packets: 578994
            rx_queue_0_bytes: 51734607
            rx_queue_0_drops: 0
            rx_queue_0_csum_err: 0
            rx_queue_0_alloc_failed: 0
            rx_queue_1_packets: 162272
            rx_queue_1_bytes: 79319788
            rx_queue_1_drops: 0
            rx_queue_1_csum_err: 0
            rx_queue_1_alloc_failed: 0
            rx_queue_2_packets: 67292
            rx_queue_2_bytes: 5850192
            rx_queue_2_drops: 0
            rx_queue_2_csum_err: 0
            rx_queue_2_alloc_failed: 0
            rx_queue_3_packets: 99976
            rx_queue_3_bytes: 16451118
            rx_queue_3_drops: 0
            rx_queue_3_csum_err: 0
            rx_queue_3_alloc_failed: 0
            """
        )
        expected_output = {
            "rx_packets": ["52924116"],
            "tx_packets": ["6831559"],
            "rx_bytes_nic": ["23486721711"],
            "tx_bytes_nic": ["1592747875"],
            "rx_broadcast": ["17950853"],
            "tx_broadcast": ["83"],
            "rx_multicast": ["15401567"],
            "tx_multicast": ["46633"],
            "multicast": ["15401567"],
            "collisions": ["0"],
            "rx_crc_errors": ["0"],
            "rx_no_buffer_count": ["0"],
            "rx_missed_errors": ["0"],
            "tx_aborted_errors": ["0"],
            "tx_carrier_errors": ["0"],
            "tx_window_errors": ["0"],
            "tx_abort_late_coll": ["0"],
            "tx_deferred_ok": ["0"],
            "tx_single_coll_ok": ["0"],
            "tx_multi_coll_ok": ["0"],
            "tx_timeout_count": ["0"],
            "rx_long_length_errors": ["0"],
            "rx_short_length_errors": ["0"],
            "rx_align_errors": ["0"],
            "tx_tcp_seg_good": ["439677"],
            "tx_tcp_seg_failed": ["0"],
            "rx_flow_control_xon": ["0"],
            "rx_flow_control_xoff": ["0"],
            "tx_flow_control_xon": ["0"],
            "tx_flow_control_xoff": ["0"],
            "rx_long_byte_count": ["23486721711"],
            "tx_dma_out_of_sync": ["0"],
            "tx_smbus": ["0"],
            "rx_smbus": ["0"],
            "dropped_smbus": ["0"],
            "os2bmc_rx_by_bmc": ["0"],
            "os2bmc_tx_by_bmc": ["0"],
            "os2bmc_tx_by_host": ["0"],
            "os2bmc_rx_by_host": ["0"],
            "tx_hwtstamp_timeouts": ["0"],
            "tx_hwtstamp_skipped": ["0"],
            "rx_hwtstamp_cleared": ["0"],
            "rx_errors": ["0"],
            "tx_errors": ["0"],
            "tx_dropped": ["0"],
            "rx_length_errors": ["0"],
            "rx_over_errors": ["0"],
            "rx_frame_errors": ["0"],
            "rx_fifo_errors": ["0"],
            "tx_fifo_errors": ["0"],
            "tx_heartbeat_errors": ["0"],
            "tx_queue_0_packets": ["11813"],
            "tx_queue_0_bytes": ["1156810"],
            "tx_queue_0_restart": ["0"],
            "tx_queue_1_packets": ["23062"],
            "tx_queue_1_bytes": ["2655140"],
            "tx_queue_1_restart": ["2655140"],
            "tx_queue_2_packets": ["80570"],
            "tx_queue_2_bytes": ["39314035"],
            "tx_queue_2_restart": ["0"],
            "tx_queue_3_packets": ["5004"],
            "tx_queue_3_bytes": ["524010"],
            "tx_queue_3_restart": ["0"],
            "rx_queue_0_packets": ["578994"],
            "rx_queue_0_bytes": ["51734607"],
            "rx_queue_0_drops": ["0"],
            "rx_queue_0_csum_err": ["0"],
            "rx_queue_0_alloc_failed": ["0"],
            "rx_queue_1_packets": ["162272"],
            "rx_queue_1_bytes": ["79319788"],
            "rx_queue_1_drops": ["0"],
            "rx_queue_1_csum_err": ["0"],
            "rx_queue_1_alloc_failed": ["0"],
            "rx_queue_2_packets": ["67292"],
            "rx_queue_2_bytes": ["5850192"],
            "rx_queue_2_drops": ["0"],
            "rx_queue_2_csum_err": ["0"],
            "rx_queue_2_alloc_failed": ["0"],
            "rx_queue_3_packets": ["99976"],
            "rx_queue_3_bytes": ["16451118"],
            "rx_queue_3_drops": ["0"],
            "rx_queue_3_csum_err": ["0"],
            "rx_queue_3_alloc_failed": ["0"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -S enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_adapter_statistics(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -S enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_adapter_statistics_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -S enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_adapter_statistics(device_name="enp2s0")

    def test_execute_self_test(self, ethtool):
        output = dedent(
            """\
        The test result is PASS
        The test extra info:
        Register test  (offline)         0
        Eeprom test    (offline)         0
        Interrupt test (offline)         0
        Loopback test  (offline)         0
        Link test   (on/offline)         0

            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -t enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.execute_self_test(device_name="enp2s0") == output

    def test_execute_self_test_with_mode(self, ethtool):
        output = dedent(
            """\
        The test result is PASS
        The test extra info:
        Register test  (offline)         0
        Eeprom test    (offline)         0
        Interrupt test (offline)         0
        Loopback test  (offline)         0
        Link test   (on/offline)         0

            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -t enp2s0 offline", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.execute_self_test(device_name="enp2s0", test_mode="offline") == output

    def test_execute_self_test_with_namespace(self, ethtool):
        ethtool.execute_self_test(device_name="enp2s0", test_mode="offline", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -t enp2s0 offline",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_change_generic_options(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -s enp2s0 autoneg on", stdout="", return_code=0, stderr=""
        )
        ethtool.change_generic_options(device_name="enp2s0", param_name="autoneg", param_value="on")

    def test_change_generic_options_with_namespace(self, ethtool):
        ethtool.change_generic_options(device_name="enp2s0", param_name="autoneg", param_value="on", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -s enp2s0 autoneg on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_private_flags(self, ethtool):
        output = dedent(
            """\
        Private flags for enp2s0:
        legacy-rx: off
        OTP ACCESS: on
            """
        )
        expected_output = {"legacy_rx": ["off"], "otp_access": ["on"]}
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-priv-flags enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_private_flags(device_name="enp2s0")) == expected_output

    def test_get_private_flags_with_namespace(self, ethtool):
        output = dedent(
            """\
        Private flags for enp2s0:
        legacy-rx: off
        OTP ACCESS: on
            """
        )
        expected_output = {"legacy_rx": ["off"], "otp_access": ["on"]}
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-priv-flags enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_private_flags(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --show-priv-flags enp2s0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_private_flags_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-priv-flags enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_private_flags(device_name="enp2s0")

    def test_set_private_flags(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --set-priv-flags enp2s0 legacy-rx on", stdout="", return_code=0, stderr=""
        )
        ethtool.set_private_flags(device_name="enp2s0", flag_name="legacy-rx", flag_value="on")

    def test_set_private_flags_with_namespace(self, ethtool):
        ethtool.set_private_flags(device_name="enp2s0", flag_name="legacy-rx", flag_value="on", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --set-priv-flags enp2s0 legacy-rx on",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_rss_indirection_table(self, ethtool):
        output = dedent(
            """\
        RX flow hash indirection table for enp2s0 with 4 RX ring(s):
        0:      0     0     0     0     0     0     0     0
        8:      0     0     0     0     0     0     0     0
        16:      0     0     0     0     0     0     0     0
        24:      0     0     0     0     0     0     0     0
        32:      1     1     1     1     1     1     1     1
        40:      1     1     1     1     1     1     1     1
        48:      1     1     1     1     1     1     1     1
        56:      1     1     1     1     1     1     1     1
        64:      2     2     2     2     2     2     2     2
        72:      2     2     2     2     2     2     2     2
        80:      2     2     2     2     2     2     2     2
        88:      2     2     2     2     2     2     2     2
        96:      3     3     3     3     3     3     3     3
        104:      3     3     3     3     3     3     3     3
        112:      3     3     3     3     3     3     3     3
        120:      3     3     3     3     3     3     3     3
        RSS hash key:
        Operation not supported
        RSS hash function:
            toeplitz: on
            xor: off
            crc32: off
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -x enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.get_rss_indirection_table(device_name="enp2s0") == output

    def test_set_rss_indirection_table_default(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -X enp2s0 default", stdout="", return_code=0, stderr=""
        )
        ethtool.set_rss_indirection_table(device_name="enp2s0", param_name="default")

    def test_set_rss_indirection_table_with_namespace(self, ethtool):
        ethtool.set_rss_indirection_table(device_name="enp2s0", param_name="default", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -X enp2s0 default",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_rss_indirection_table_with_parameters(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -X enp2s0 equal 20", stdout="", return_code=0, stderr=""
        )
        ethtool.set_rss_indirection_table(device_name="enp2s0", param_name="equal", param_value="20")

    def test_flash_firmware_image(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -f enp2s0 gtp.pkgo", stdout="", return_code=0, stderr=""
        )
        ethtool.flash_firmware_image(device_name="enp2s0", file="gtp.pkgo")

    def test_flash_firmware_image_with_region(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -f enp2s0 gtp.pkgo 100", stdout="", return_code=0, stderr=""
        )
        ethtool.flash_firmware_image(device_name="enp2s0", file="gtp.pkgo", region=100)

    def test_flash_firmware_image_with_namespace(self, ethtool):
        ethtool.flash_firmware_image(device_name="enp2s0", file="gtp.pkgo", region=100, namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -f enp2s0 gtp.pkgo 100",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_unload_ddp_profile(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args=" ethtool -f enp2s0 - 100", stdout="", return_code=0, stderr=""
        )
        ethtool.unload_ddp_profile(device_name="enp2s0", region=100)

    def test_unload_ddp_profile_with_namespace(self, ethtool):
        ethtool.unload_ddp_profile(device_name="enp2s0", region=100, namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -f enp2s0 - 100",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_fec_settings(self, ethtool):
        output = dedent(
            """\
        FEC parameters for enp2s0:
        Configured FEC encodings:  Auto RS BaseR
        Active FEC encoding: RS
            """
        )
        expected_output = {"configured_fec_encodings": ["Auto RS BaseR"], "active_fec_encoding": ["RS"]}
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-fec enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_fec_settings(device_name="enp2s0")) == expected_output

    def test_get_fec_settings_with_namespace(self, ethtool):
        output = dedent(
            """\
        FEC parameters for enp2s0:
        Configured FEC encodings:  Auto RS BaseR
        Active FEC encoding: RS
            """
        )
        expected_output = {"configured_fec_encodings": ["Auto RS BaseR"], "active_fec_encoding": ["RS"]}
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-fec enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_fec_settings(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --show-fec enp2s0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_fec_settings_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-fec enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_fec_settings(device_name="enp2s0")

    def test_get_fec_settings_supported_configured_fec_settings(self, ethtool):
        output = dedent(
            """
        FEC parameters for enp2s1:
        Supported/Configured FEC encodings: Auto RS BaseR
        Active FEC encoding: RS"""
        )
        expected_output = {"supported_configured_fec_encodings": ["Auto RS BaseR"], "active_fec_encoding": ["RS"]}
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-fec enp2s1", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_fec_settings(device_name="enp2s1")) == expected_output

    def test_set_fec_settings(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --set-fec enp2s0 encoding off", stdout="", return_code=0, stderr=""
        )
        ethtool.set_fec_settings(device_name="enp2s0", setting_name="encoding-rx", setting_value="off")

    def test_set_fec_settings_with_namespace(self, ethtool):
        ethtool.set_fec_settings(device_name="enp2s0", setting_name="encoding-rx", setting_value="off", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --set-fec enp2s0 encoding-rx off",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_do_register_dump(self, ethtool):
        output = dedent(
            """\
        0x00000: CTRL (Device control register)               0x58100241
        Invert Loss-Of-Signal:                         no
        Receive flow control:                          enabled
        Transmit flow control:                         enabled
        VLAN mode:                                     enabled
        Set link up:                                   1
        0x00008: STATUS (Device status register)              0x00280383
        Duplex:                                        full
        Link up:                                       link config
        Transmission:                                  on
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -d enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.do_register_dump(device_name="enp2s0") == output

    def test_do_register_dump_with_namespace(self, ethtool):
        ethtool.do_register_dump(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -d enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_time_stamping_capabilities(self, ethtool):
        output = dedent(
            """\
        Time stamping parameters for enp2s0:
        Capabilities:
                hardware-transmit     (SOF_TIMESTAMPING_TX_HARDWARE)
                software-transmit     (SOF_TIMESTAMPING_TX_SOFTWARE)
                hardware-receive      (SOF_TIMESTAMPING_RX_HARDWARE)
                software-receive      (SOF_TIMESTAMPING_RX_SOFTWARE)
                software-system-clock (SOF_TIMESTAMPING_SOFTWARE)
                hardware-raw-clock    (SOF_TIMESTAMPING_RAW_HARDWARE)
        PTP Hardware Clock: 0
        Hardware Transmit Timestamp Modes:
                off                   (HWTSTAMP_TX_OFF)
                on                    (HWTSTAMP_TX_ON)
        Hardware Receive Filter Modes:
                none                  (HWTSTAMP_FILTER_NONE)
                all                   (HWTSTAMP_FILTER_ALL)
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -T enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.get_time_stamping_capabilities(device_name="enp2s0") == output

    def test_get_time_stamping_capabilities_with_namespace(self, ethtool):
        ethtool.get_time_stamping_capabilities(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -T enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_perm_hw_address(self, ethtool):
        output = dedent("""Permanent address: 00:90:fb:bb:aa:cc""")
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.get_perm_hw_address(device_name="enp2s0") == "00:90:fb:bb:aa:cc"

    def test_get_perm_hw_address_with_namespace(self, ethtool):
        output = dedent("""Permanent address: 00:90:fb:bb:aa:cc""")
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.get_perm_hw_address(device_name="enp2s0", namespace="NS1") == "00:90:fb:bb:aa:cc"
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -P enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_dump_module_eeprom(self, ethtool):
        output = dedent(
            """\
        Offset          Values
        ------          ------
        0x0014          4a 44 53 55 20 20 20 20 20 20 20 20 20 20 20 20
        0x0024          00 00 01 9c 50 4c 52 58 50 4c 53 43 53 34 33 32
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -m enp2s0 offset 0x14 length 32", stdout=output, return_code=0, stderr=""
        )
        assert ethtool.dump_module_eeprom(device_name="enp2s0", params="offset 0x14 length 32") == output

    def test_dump_module_eeprom_with_namespace(self, ethtool):
        ethtool.dump_module_eeprom(device_name="enp2s0", params="offset 0x14 length 32", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -m enp2s0 offset 0x14 length 32",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_eee_settings(self, ethtool):
        output = dedent(
            """\
        EEE Settings for enp2s0:
        EEE status: enabled - inactive
        Tx LPI: 0 (us)
        Supported EEE link modes:  100baseT/Full
                                   1000baseT/Full
        Advertised EEE link modes:  100baseT/Full
                                    1000baseT/Full
        Link partner advertised EEE link modes:  Not reported
            """
        )
        expected_output = {
            "eee_status": ["enabled - inactive"],
            "tx_lpi": ["0 (us)"],
            "supported_eee_link_modes": ["100baseT/Full", "1000baseT/Full"],
            "advertised_eee_link_modes": ["100baseT/Full", "1000baseT/Full"],
            "link_partner_advertised_eee_link_modes": ["Not reported"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-eee enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_eee_settings(device_name="enp2s0")) == expected_output

    def test_get_eee_settings_with_namespace(self, ethtool):
        output = dedent(
            """\
        EEE Settings for enp2s0:
        EEE status: enabled - inactive
        Tx LPI: 0 (us)
        Supported EEE link modes:  100baseT/Full
                                   1000baseT/Full
        Advertised EEE link modes:  100baseT/Full
                                    1000baseT/Full
        Link partner advertised EEE link modes:  Not reported
            """
        )
        expected_output = {
            "eee_status": ["enabled - inactive"],
            "tx_lpi": ["0 (us)"],
            "supported_eee_link_modes": ["100baseT/Full", "1000baseT/Full"],
            "advertised_eee_link_modes": ["100baseT/Full", "1000baseT/Full"],
            "link_partner_advertised_eee_link_modes": ["Not reported"],
        }
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-eee enp2s0", stdout=output, return_code=0, stderr=""
        )
        assert asdict(ethtool.get_eee_settings(device_name="enp2s0", namespace="NS1")) == expected_output
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --show-eee enp2s0",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_eee_settings_not_available(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --show-eee enp2s0", stdout="", return_code=0, stderr=""
        )
        with pytest.raises(EthtoolException, match="Error while fetching ethtool output"):
            ethtool.get_eee_settings(device_name="enp2s0")

    def test_set_eee_settings(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --set-eee enp2s0 eee off", stdout="", return_code=0, stderr=""
        )
        ethtool.set_eee_settings(device_name="enp2s0", param_name="eee", param_value="off")

    def test_set_eee_settings_with_namespace(self, ethtool):
        ethtool.set_eee_settings(device_name="enp2s0", param_name="eee", param_value="off", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --set-eee enp2s0 eee off",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_set_phy_tunable(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --set-phy-tunable enp2s0 downshift on count 2", stdout="", return_code=0, stderr=""
        )
        ethtool.set_phy_tunable(device_name="enp2s0", params="downshift on count 2")

    def test_set_phy_tunable_with_namespace(self, ethtool):
        ethtool.set_phy_tunable(device_name="enp2s0", params="downshift on count 2", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --set-phy-tunable enp2s0 downshift on count 2",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_reset_components(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool --reset enp2s0 phy", stdout="", return_code=0, stderr=""
        )
        ethtool.reset_components(device_name="enp2s0", param_name="phy")

    def test_reset_components_with_namespace(self, ethtool):
        ethtool.reset_components(device_name="enp2s0", param_name="phy", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool --reset enp2s0 phy",
            custom_exception=EthtoolExecutionError,
            expected_return_codes={0},
        )

    def test_get_dump(self, ethtool):
        output = dedent(
            """\
        flag: 3, version: 1, length: 4312
            """
        )
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -w enp2s0", stdout=output, return_code=0, stderr=""
        )
        ethtool.get_dump(device_name="enp2s0")

    def test_get_dump_with_namespace(self, ethtool):
        ethtool.get_dump(device_name="enp2s0", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -w enp2s0", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )

    def test_get_dump_with_file(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -w enp2s0 data file.bin", stdout="", return_code=0, stderr=""
        )
        ethtool.get_dump(device_name="enp2s0", params="data file.bin")

    def test_set_dump(self, ethtool):
        ethtool._connection.execute_command.return_value = ConnectionCompletedProcess(
            args="ethtool -W enp2s0 3", stdout="", return_code=0, stderr=""
        )
        ethtool.set_dump(device_name="enp2s0", params="3")

    def test_set_dump_with_namespace(self, ethtool):
        ethtool.set_dump(device_name="enp2s0", params="3", namespace="NS1")
        ethtool._connection.execute_command.assert_called_with(
            "ip netns exec NS1 ethtool -W enp2s0 3", custom_exception=EthtoolExecutionError, expected_return_codes={0}
        )
