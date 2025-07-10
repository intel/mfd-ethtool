# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Main Ethtool module."""

import logging
import re
from typing import Iterable
from dataclasses import dataclass, make_dataclass
from mfd_common_libs import add_logging_level, log_levels, os_supported
from mfd_kernel_namespace import add_namespace_call_command
from mfd_base_tool import ToolTemplate
from mfd_typing import OSName, OSBitness
from .exceptions import EthtoolNotAvailable, EthtoolException, EthtoolExecutionError
from .const import ETHTOOL_RC_VALUE_UNCHANGED, ETHTOOL_RC_VALUE_OUT_OF_RANGE

from mfd_ethtool import EthtoolParser
from .structures import GetReceiveNetworkFlowClassification, SetReceiveNetworkFlowClassification

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


class Ethtool(ToolTemplate):
    """Class for Ethtool."""

    tool_executable_name = {
        (OSName.LINUX, OSBitness.OS_32BIT): "ethtool",
        (OSName.LINUX, OSBitness.OS_64BIT): "ethtool",
    }

    __init__ = os_supported(OSName.LINUX)(ToolTemplate.__init__)

    known_errors = [
        "Operation not permitted",
        "Cannot add",
        "Cannot insert",
        "Cannot change",
        "Invalid argument",
        "Operation not permitted",
        "Operation not supported",
        "Cannot get driver information",
    ]

    parser = EthtoolParser()

    def _get_tool_exec_factory(self) -> str:
        """Get correct tool name."""
        return self.tool_executable_name[(self._connection.get_os_name(), self._connection.get_os_bitness())]

    def check_if_available(self) -> None:
        """
        Check if tool is available in system.

        :raises EthtoolNotAvailable when tool not available.
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Check if Ethtool is available")
        command = f"{self._tool_exec} --version"
        self._connection.execute_command(command, custom_exception=EthtoolNotAvailable)

    def get_version(self) -> str:
        """
        Get version of Ethtool.

        :return: Ethtool version
        :raises EthtoolException: if version is not found
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Get Ethtool version")
        command = f"{self._tool_exec} --version"
        output = self._connection.execute_command(command).stdout
        version_regex = r"ethtool\sversion\s+(?P<version>[\d|\w].+)"
        match = re.search(version_regex, output)
        if match:
            return match.group("version")
        raise EthtoolException("Ethtool version not found.")

    def execute_ethtool_command(
        self,
        device_name: str,
        option: str = "",
        params: str = "",
        namespace: str | None = None,
        succeed_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Execute ethtool command with device name, options to pass and parameters.

        :param device_name: interface/device/adapter name
        :param option: ethtool supported options, e.g. "-i"
        :param params: required parameters to call the command
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param succeed_codes: set of acceptable return codes
        :return: output of the executed ethtool command user to verify it
        :raises EthtoolExecutionError: if ethtool command fails on execution
        :raises EthtoolException: if ethtool command fails with known error
        """
        command = f"{self._tool_exec} {device_name}"
        if option:
            command = f"{self._tool_exec} {option} {device_name}"
        if params:
            command += f" {params}"
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Execute ethtool command: {command}")
        output = self._connection.execute_command(
            add_namespace_call_command(command, namespace=namespace),
            custom_exception=EthtoolExecutionError,
            expected_return_codes=succeed_codes,
        )
        if output.return_code not in [ETHTOOL_RC_VALUE_UNCHANGED, ETHTOOL_RC_VALUE_OUT_OF_RANGE] and output.stderr:
            for e in self.known_errors:
                if e in output.stderr:
                    raise EthtoolException(f"Error while running ethtool command: {output.stderr}")
        return output.stdout

    def get_standard_device_info(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Display standard information about device - ethtool DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get standard information about device: {device_name}")
        output = self.execute_ethtool_command(device_name, namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output)

    def get_pause_options(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get pause option - ethtool -a|--show-pause DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get pause option for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-a", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-a")

    def set_pause_options(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set pause options - ethtool -A|--pause DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name: supported pause option params to set. example: rx/tx/autoneg
        :param param_value: supported pause option param values. example: on/off
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set pause options for device: {device_name}")
        return self.execute_ethtool_command(
            device_name,
            option="-A",
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_coalesce_options(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get coalesce options - ethtool -c|--show-coalesce DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get coalesce options for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-c", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-c")

    def set_coalesce_options(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set coalesce options - ethtool -C|--coalesce DEVNAME.

        :param device_name: interface/device/adapter name/pkt-rate-low
        :param param_name: supported coalesce option params to set. example: adaptive-rx/rx-frames
        :param param_value: supported coalesce option param values. example: on/N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set coalesce options for device: {device_name}")
        return self.execute_ethtool_command(
            device_name,
            option="-C",
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_ring_parameters(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get RX/TX ring parameters - ethtool -g|--show-ring DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get rx/tx ring parameters for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-g", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-g")

    def set_ring_parameters(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set RX/TX ring parameters - ethtool -G|--set-ring DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name : supported ring parameters to set. example: rx/rx-mini
        :param param_value: supported ring parameters values. example: N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set rx/tx ring parameters for device: {device_name}")
        return self.execute_ethtool_command(
            device_name,
            option="-G",
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_driver_information(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Show driver information - ethtool -i|--driver DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get driver information for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-i", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-i")

    def get_protocol_offload_and_feature_state(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get state of protocol offload and other features - ethtool -k|--show-features|--show-offload DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Get state of protocol offload and other features for device: " f"{device_name}",
        )
        output = self.execute_ethtool_command(device_name, option="-k", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-k")

    def set_protocol_offload_and_feature_state(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set protocol offload and other features - ethtool -K|--features|--offload DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name : supported features to set. example: tso/lro
        :param param_value: supported feature values. example: on/off
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(
            level=log_levels.MODULE_DEBUG, msg=f"Set protocol offload and other features for device: " f"{device_name}"
        )
        return self.execute_ethtool_command(
            device_name,
            option="-K",
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_channel_parameters(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get Channels parameters values - ethtool -l|--show-channels DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get channel parameters for device: " f"{device_name}")
        output = self.execute_ethtool_command(device_name, option="-l", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-l")

    def set_channel_parameters(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set Channels - ethtool -L|--set-channels DEVNAME.

        In case of 'rx' or 'tx' we need to read value of the another parameter first and set it again together
        with the required one - ethtool cli allows us to put rx/tx together only.

        :param device_name: interface/device/adapter name
        :param param_name : supported channel parameters to set. example: rx/tx/rx tx/other/combined
        :param param_value: supported feature values. example: N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        :raises EthtoolException: if we can't read channel parameters or incorrect parameter name is used
        :return: output of the executed ethtool command user to verify it
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set channel parameters for device: {device_name}")

        match param_name:
            case "rx":
                try:
                    tx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_tx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for tx.")
                params = f"rx {param_value} tx {tx_current}"
            case "tx":
                try:
                    rx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_rx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for rx.")
                params = f"tx {param_value} rx {rx_current}"
            case "rx tx":
                try:
                    rx_value, tx_value = param_value.strip().split(" ")
                except Exception:
                    raise EthtoolException(f"Can't match rx / tx parameters values - '{param_value}' is incorrect")
                params = f"rx {rx_value} tx {tx_value}"
            case "other" | "combined":
                params = f"{param_name} {param_value}"
            case _:
                raise EthtoolException(f"Incorrect parameter name for ethtool command: {param_name}")

        return self.execute_ethtool_command(
            device_name,
            option="-L",
            params=params,
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def set_channel_parameters_ice_idpf_aligned(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set Channels - ethtool -L|--set-channels DEVNAME params.

        After implementation of DCR-4504 ice/idpf drivers behavior are aligned with ethtool manual. It means that the
        user has to use "combined" parameter to set the symmetrical part of the configuration, and then use either "rx"
        or "tx" to set the remaining asymmetrical part of the configuration.The previous values of "combined", "rx", and
        "tx" are preserved independently. If a certain value is not specified in the command, it will stay the same
        instead of being set to zero.

        Tx/Rx queues cannot exist outside of queue pairs simultaneously, so either "rx" or "tx" parameter has to be
        equal zero.

        :param device_name: interface/device/adapter name
        :param param_name : supported channel parameters to set. Example: rx/tx/rx tx/combined rx tx/combined/other
        :param param_value: supported feature values. example: N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        :raises EthtoolException: if we can't read channel parameters or incorrect parameter name is used
        :return: output of the executed ethtool command user to verify it
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set channel parameters for device: {device_name}")

        match param_name:
            case "rx":
                try:
                    tx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_tx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for tx.")
                if tx_current != "0":
                    raise EthtoolException(
                        "Cannot configure separate rx-only channels when tx-only channels are not equal to 0"
                    )
                params = f"rx {param_value}"
            case "tx":
                try:
                    rx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_rx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for rx.")
                if rx_current != "0":
                    raise EthtoolException(
                        "Cannot configure separate tx-only channels when rx-only channels are not equal to 0"
                    )
                params = f"tx {param_value}"
            case "rx tx":
                try:
                    rx_value, tx_value = param_value.split()
                except Exception:
                    raise EthtoolException(f"Can't match rx / tx parameters values - '{param_value}' is incorrect")
                if rx_value != "0" and tx_value != "0":
                    raise EthtoolException("Either rx or tx parameter has to be equal zero.")
                params = f"rx {rx_value} tx {tx_value}"
            case "combined rx tx":
                try:
                    combined_value, rx_value, tx_value = param_value.split()
                except Exception:
                    raise EthtoolException(
                        f"Can't match rx / tx / combined parameters values - '{param_value}' is incorrect"
                    )
                if rx_value != "0" and tx_value != "0":
                    raise EthtoolException("Either rx or tx parameter has to be equal zero.")
                if combined_value == "0":
                    raise EthtoolException("Combine value must be greater than 0.")
                params = f"combined {combined_value} rx {rx_value} tx {tx_value}"
            case "combined rx":
                try:
                    combined_value, rx_value = param_value.split()
                    tx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_tx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for tx.")
                except Exception:
                    raise EthtoolException(
                        f"Can't match rx / combined parameters values - '{param_value}' is incorrect"
                    )
                if tx_current != "0":
                    raise EthtoolException(
                        "Cannot configure separate rx-only channels when tx-only channels are not equal to 0"
                    )
                if combined_value == "0":
                    raise EthtoolException("Combine value must be greater than 0.")
                params = f"combined {combined_value} rx {rx_value}"
            case "combined tx":
                try:
                    combined_value, tx_value = param_value.split()
                    rx_current = self.get_channel_parameters(
                        device_name=device_name, namespace=namespace
                    ).current_hw_rx[0]
                except IndexError:
                    raise EthtoolException("Can't read channel parameters for rx.")
                except Exception:
                    raise EthtoolException(
                        f"Can't match tx / combined parameters values - '{param_value}' is incorrect"
                    )
                if rx_current != "0":
                    raise EthtoolException(
                        "Cannot configure separate tx-only channels when rx-only channels are not equal to 0"
                    )
                if combined_value == "0":
                    raise EthtoolException("Combine value must be greater than 0.")
                params = f"combined {combined_value} tx {tx_value}"
            case "combined":
                if param_value == "0":
                    raise EthtoolException("Combine value must be greater than 0.")
                params = f"combined {param_value}"
            case "other":
                params = f"{param_name} {param_value}"
            case _:
                raise EthtoolException(f"Incorrect parameter name for ethtool command: {param_name}")

        return self.execute_ethtool_command(
            device_name,
            option="-L",
            params=params,
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_receive_network_flow_classification(
        self,
        device_name: str,
        param_name: str = "",
        param_value: str = "",
        option: GetReceiveNetworkFlowClassification = GetReceiveNetworkFlowClassification.U,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Get Rx network flow classification options or rules - ethtool -n|-u|--show-nfc|--show-ntuple DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name : supported rx network flow classification or rules to get. example: rx-flow-hash
        :param param_value: supported rx network flow classification or rule values. example: rule
        :param option: one of GetReceiveNetworkFlowClassification options: -n, -u, --show-nfc or --show-ntuple
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        :return: ethtool output
        :raises EthtoolException in case of wrong option used
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Get Rx network flow classification options or rules for " f"device: {device_name}",
        )
        if not isinstance(option, GetReceiveNetworkFlowClassification):
            raise EthtoolException(f"Incorrect option for ethtool command: {option}")
        return self.execute_ethtool_command(
            device_name,
            option=option.value,
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def set_receive_network_flow_classification(
        self,
        device_name: str,
        params: str,
        option: SetReceiveNetworkFlowClassification = SetReceiveNetworkFlowClassification.U,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Configure Rx network flow classification options or rules - ethtool -N|-U|--config-nfc|--config-ntuple DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: options/rules to set. example:  flow-type ip4 proto 1 action -1
        :param option: one of GetReceiveNetworkFlowClassification options: -N, -U, --config-nfc or --config-ntuple
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        :return: ethtool output
        :raises EthtoolException in case of wrong option used
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Configure Rx network flow classification options or rules for device: {device_name}",
        )
        if not isinstance(option, SetReceiveNetworkFlowClassification):
            raise EthtoolException(f"Incorrect option for ethtool command: {option}")
        return self.execute_ethtool_command(
            device_name, option=option.value, params=f"{params}", namespace=namespace, succeed_codes=expected_codes
        )

    def show_visible_port_identification(
        self, device_name: str, duration: int = 3, namespace: str | None = None
    ) -> str:
        """
        Show visible port identification (e.g. blinking) - ethtool -p|--identify DEVNAME.

        :param device_name: interface/device/adapter name
        :param duration: blink duration
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: raw ethtool output
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Show visible port identification for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-p", params=f"{duration}", namespace=namespace)

    def change_eeprom_settings(self, device_name: str, params: str, namespace: str | None = None) -> str:
        """
        Change bytes in device EEPROM - ethtool -E|--change-eeprom DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: eeprom parameters to change. example: length/magic/offset/value N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Change bytes in EEPROM for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-E", params=f"{params}", namespace=namespace)

    def do_eeprom_dump(self, device_name: str, params: str = "", namespace: str | None = None) -> str:
        """
        Do EEPROM dump - ethtool -e|--eeprom-dump DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameters supported for eeprom dump, e.g. names: raw/offset/length, values: on/off/N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Do EEPROM dump for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-e", params=f"{params}", namespace=namespace)

    def restart_negotiation(self, device_name: str, namespace: str | None = None) -> str:
        """
        Restart N-WAY negotiation - ethtool -r|--negotiate DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Restart negotiation for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-r", namespace=namespace)

    def get_adapter_statistics(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Show adapter statistics - ethtool -S|--statistics DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get adapter statistics for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-S", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="-S")

    def get_statistics_xonn_xoff(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Show interface statistics - ethtool -S|--statistics DEVNAME with filtered out xon/xoff only.

        :param device_name: interface or device name
        :param namespace: the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get XON/XOFF statistics for device: {device_name}")
        all_stats = self.get_adapter_statistics(device_name=device_name, namespace=namespace)
        filtered_stats = {name: value for name, value in all_stats.__dict__.items() if "xon" in name or "xoff" in name}
        output_dataclass = make_dataclass(
            self.parser._outputs_ds["-S"], [(k, list[str]) for k, v in filtered_stats.items()]
        )
        return output_dataclass(**filtered_stats)

    def execute_self_test(self, device_name: str, test_mode: str = "", namespace: str | None = None) -> str:
        """
        Execute adapter self test - ethtool -t|--test DEVNAME.

        :param device_name: interface/device/adapter name
        :param test_mode: self test mode. example: online/offline/external_lb
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output containing test result
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Execute self test for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-t", params=test_mode, namespace=namespace)

    def change_generic_options(
        self, device_name: str, param_name: str, param_value: str, namespace: str | None = None
    ) -> str:
        """
        Change generic options - ethtool -s|--change DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name: generic option to set. example: speed/autoneg
        :param param_value: generic option value to set. example: %d/on
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Change generic options for device: {device_name}")
        return self.execute_ethtool_command(
            device_name, option="-s", params=f"{param_name} {param_value}", namespace=namespace
        )

    def set_private_flags(
        self,
        device_name: str,
        flag_name: str,
        flag_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set private flags - ethtool --set-priv-flags DEVNAME.

        :param device_name: interface/device/adapter name
        :param flag_name: flag to set
        :param flag_value: flag value to set. example: on/off
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set private flags for device: {device_name}")
        return self.execute_ethtool_command(
            device_name,
            option="--set-priv-flags",
            params=f"{flag_name} {flag_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def get_private_flags(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get private flags - ethtool --show-priv-flags DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get private flags for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="--show-priv-flags", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="--show-priv-flags")

    def get_rss_indirection_table(self, device_name: str, namespace: str | None = None) -> str:
        """
        Get Rx flow hash indirection table and/or RSS hash key - ethtool -x|--show-rxfh-indir|--show-rxfh DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Get Rx flow hash indirection table/ RSS hash key for device: " f"{device_name}",
        )
        return self.execute_ethtool_command(device_name, option="-x", namespace=namespace)

    def set_rss_indirection_table(
        self, device_name: str, param_name: str, param_value: str = "", namespace: str | None = None
    ) -> str:
        """
        Set Rx flow hash indirection table and/or RSS hash key - ethtool -X|--set-rxfh-indir|--rxfh DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name: supported parameters for rx flow indirection or hash key. example: equal/hkey/hfunc/default
        :param param_value: supported parameter values for rx flow indirection or hash key.
                           example: N/<key>/<func>
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Set Rx flow hash indirection table/ RSS hash key for device: " f"{device_name}",
        )
        params = f"{param_name}"
        if param_value:
            params += f" {param_value}"
        return self.execute_ethtool_command(device_name, option="-X", params=params, namespace=namespace)

    def flash_firmware_image(
        self, device_name: str, file: str, region: int | None = None, namespace: str | None = None
    ) -> str:
        """
        Flash firmware image from the specified file to a region on the device - ethtool -f|--flash DEVNAME.

        :param device_name: interface/device/adapter name
        :param file: Firmware image file name
        :param region: region number to flash
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Flash firmware image for device: {device_name}")
        params = f"{file}"
        if region is not None:
            params += f" {region}"
        return self.execute_ethtool_command(device_name, option="-f", params=f"{params}", namespace=namespace)

    def unload_ddp_profile(self, device_name: str, region: int, namespace: str | None = None) -> str:
        """
        Rollback to a previously loaded profile - ethtool -f DEVNAME - region.

        :param device_name: interface/device/adapter name
        :param region: region number to flash
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Unload ddp profile for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-f", params=f"- {region}", namespace=namespace)

    def get_fec_settings(self, device_name: str, namespace: str = None) -> type[dataclass]:
        """
        Get FEC settings - ethtool --show-fec DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get fec settings for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="--show-fec", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="--show-fec")

    def set_fec_settings(
        self, device_name: str, setting_name: str, setting_value: str, namespace: str | None = None
    ) -> str:
        """
        Set FEC settings - ethtool --set-fec DEVNAME.

        :param device_name: interface/device/adapter name
        :param setting_name: FEC option to set. example: encoding
        :param setting_value: FEC option value to set. example: auto|off|rs|baser
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set FEC settings for device: {device_name}")
        return self.execute_ethtool_command(
            device_name, option="--set-fec", params=f"{setting_name} {setting_value}", namespace=namespace
        )

    def do_register_dump(self, device_name: str, params: str = "", namespace: str | None = None) -> str:
        """
        Do register dump - ethtool -d|--register-dump DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameters supported for eeprom dump, e.g. name: raw/file value: on/filename
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Do register dump for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-d", params=params, namespace=namespace)

    def get_time_stamping_capabilities(self, device_name: str, namespace: str | None = None) -> str:
        """
        Get time stamping capabilities - ethtool -T|--show-time-stamping DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get time stamping capabilities for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-T", namespace=namespace)

    def get_perm_hw_address(self, device_name: str, namespace: str = None) -> str:
        """
        Get permanent hardware address - ethtool -P|--show-permaddr DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: hardware address
        :raises EthtoolException: if getting permanent hardware address fails
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get permanent hardware address for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="-P", namespace=namespace)
        addr_regex = r"Permanent\saddress:\s+(?P<addr>[\S]+)"
        match = re.search(addr_regex, output)
        if match:
            return match.group("addr")
        raise EthtoolException("Permanent hardware address not found")

    def dump_module_eeprom(self, device_name: str, params: str = "", namespace: str | None = None) -> str:
        """
        Query Module EEPROM information and optical diagnostics - ethtool -m|--dump-module-eeprom|--module-info DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameters supported for module eeprom dump, e.g. names: raw/offset/length, values: on/off/N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(
            level=log_levels.MODULE_DEBUG,
            msg=f"Query/Decode Module EEPROM information and optical diagnostics "
            f"if available for device: {device_name}",
        )
        return self.execute_ethtool_command(device_name, option="-m", params=f"{params}", namespace=namespace)

    def get_eee_settings(self, device_name: str, namespace: str | None = None) -> type[dataclass]:
        """
        Get EEE settings - ethtool --show-eee DEVNAME.

        :param device_name: interface/device/adapter name
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: parsed ethtool output
        :raises EthtoolException: if output of executed ethtool command is empty
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get EEE settings for device: {device_name}")
        output = self.execute_ethtool_command(device_name, option="--show-eee", namespace=namespace)
        if not output:
            raise EthtoolException("Error while fetching ethtool output")
        return self.parser.parse(output, option="--show-eee")

    def set_eee_settings(
        self,
        device_name: str,
        param_name: str,
        param_value: str,
        namespace: str | None = None,
        expected_codes: Iterable = frozenset({0}),
    ) -> str:
        """
        Set EEE settings - ethtool --set-eee DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name : eee setting name. example: eee/advertise/tx-lpi/tx-timer
        :param param_value: supported feature values. example: on/%x/off/%d
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set eee settings for device: {device_name}")
        return self.execute_ethtool_command(
            device_name,
            option="--set-eee",
            params=f"{param_name} {param_value}",
            namespace=namespace,
            succeed_codes=expected_codes,
        )

    def set_phy_tunable(
        self, device_name: str, params: str, namespace: str | None = None, expected_codes: Iterable = frozenset({0})
    ) -> str:
        """
        Set PHY tunable - ethtool --set-phy-tunable DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameters to be set, e.g. name: downshift/count values: on/off/N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set PHY tunable for device: {device_name}")
        return self.execute_ethtool_command(
            device_name, option="--set-phy-tunable", params=params, namespace=namespace, succeed_codes=expected_codes
        )

    def reset_components(
        self, device_name: str, param_name: str, param_value: str = "", namespace: str | None = None
    ) -> str:
        """
        Reset components - ethtool --reset DEVNAME.

        :param device_name: interface/device/adapter name
        :param param_name: supported components for reset. example: phy/flags/offload
        :param param_value: supported values for certain components. example: %x for flags
        :param namespace: name of the namespace in which ethtool command needs to be executed
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Reset components for device: " f"{device_name}")
        params = f"{param_name}"
        if param_value:
            params += f" {param_value}"
        return self.execute_ethtool_command(device_name, option="--reset", params=params, namespace=namespace)

    def get_dump(self, device_name: str, params: str = "", namespace: str | None = None) -> str:
        """
        Get dump flag, data - ethtool -w|--get-dump DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameters supported, e.g. data FILENAME
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :return: ethtool output
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Get dump for device: {device_name}")
        return self.execute_ethtool_command(device_name, option="-w", params=f"{params}", namespace=namespace)

    def set_dump(
        self, device_name: str, params: str, namespace: str | None = None, expected_codes: Iterable = frozenset({0})
    ) -> str:
        """
        Set dump flag of the device - ethtool -W|--set-dump DEVNAME.

        :param device_name: interface/device/adapter name
        :param params: Parameter to be set, e.g. N
        :param namespace: name of the namespace in which ethtool command needs to be executed
        :param expected_codes: expected return codes
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Set dump flag of the device: {device_name}")
        return self.execute_ethtool_command(
            device_name, option="-W", params=params, namespace=namespace, succeed_codes=expected_codes
        )
