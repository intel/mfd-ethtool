# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Main for Ethtool parser."""

import logging
import re
from dataclasses import dataclass, make_dataclass
from typing import List, Match, Type

from mfd_common_libs import log_levels

from .exceptions import EthtoolParserException

logger = logging.getLogger(__name__)


class EthtoolParser:
    """Class for parsing ethtool output for supported options."""

    def __init__(self):
        """Initialize parser."""
        self._ignore_lines = [
            "Settings for",
            "Coalesce parameters for",
            "Pause parameters for",
            "Ring parameters for",
            "Features for",
            "Channel parameters for",
            "NIC statistics:",
            "Private flags for",
            "EEE Settings for",
            "FEC parameters for",
        ]

        self._outputs_ds = {
            "-c": "EthtoolCoalesceOptions",
            "-a": "EthtoolPauseOptions",
            "-g": "EthtoolRingParameters",
            "-k": "EthtoolFeatures",
            "-i": "EthtoolDriverInfo",
            "-l": "EthtoolChannelParameters",
            "-S": "EthtoolAdapterStatistics",
            "--show-fec": "EthtoolFECSettings",
            "--show-eee": "EthtoolEEESettings",
        }

    def _check_ignore_lines_exist(self, output_line: str) -> bool:
        """
        Check if parser output contains lines to ignore.

        :param output_line: output line to check for ignore pattern
        :return: True if pattern present in line, else return False
        """
        for ignore_line in self._ignore_lines:
            if ignore_line in output_line:
                return True
        return False

    def _search_for_pattern(self, output_line: str, search_string: str = "") -> Match[str]:
        """
        Search for specified pattern in output line.

        :param output_line: specified output line of ethtool command
        :param search_string: pattern to find
        :return: output of regex match
        """
        if not search_string:
            search_string = r"(?P<header>[^:]+):\s*(?P<value>.*)"
        search_output = re.match(search_string, output_line)
        if not search_output:
            raise EthtoolParserException(f"Could not parse line: {output_line}")
        return search_output

    def _parse_output(self, output: str, option: str = "") -> dict:
        """
        Parse raw ethtool output.

        :param output: output of ethtool command
        :param option: ethtool option, e.g. "-i"
        :return: parsed ethtool output data structure
        """
        parsed_data = {}
        key = ""
        for line in output.splitlines():
            if not self._check_ignore_lines_exist(line):
                if ":" in line:
                    if option == "-c" or option == "--show-coalesce":
                        if "cqe" in line.casefold():  # CQE mode RX: n/a  TX: n/a
                            self._handle_coalesce_cqe_parsing(line, parsed_data)
                            continue
                        elif output.splitlines().index(line) == 1:
                            search_output = self._search_for_pattern(
                                line,
                                search_string=r"(?P<header1>Adaptive RX):\s*("
                                r"?P<adaptive_rx>\S+)\s+("
                                r"?P<header2>TX):\s*("
                                r"?P<adaptive_tx>\S+)",
                            )
                            groups = search_output.groupdict()
                            parsed_data["adaptive_rx"] = [groups["adaptive_rx"]]
                            parsed_data["adaptive_tx"] = [groups["adaptive_tx"]]
                            continue
                    if option == "-g" or option == "--show-ring" or option == "-l" or option == "--show-channels":
                        if "Pre-set maximums" in line:
                            key = "preset_max"
                            continue
                        elif "Current hardware settings" in line:
                            key = "current_hw"
                            continue
                    search_output = self._search_for_pattern(line, search_string=r"(?P<header>[^:]+):\s*(?P<value>.*)")
                    groups = search_output.groupdict()
                    header, value = groups["header"], groups["value"]
                    if key:
                        header = f"{key}_{header}"
                    header = (
                        header.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
                    )
                    parsed_data[header] = [value.strip()]
                else:
                    if line:
                        parsed_data[header].append(line.strip())
        return parsed_data

    def _handle_coalesce_cqe_parsing(self, line: str, parsed_data: dict) -> None:
        """
        Handle parsing of CQE mode RX and TX.

        :param line: line to parse
        :param parsed_data: parsed data dictionary to update
        """
        # CQE mode RX: n/a  TX: n/a
        cqe_mode_rx_tx_string = self._search_for_pattern(
            line,
            search_string=r"(?P<header1>CQE mode RX):\s*(?P<cqe_mode_rx>\S+)\s+(?P<header2>TX):\s*(?P<cqe_mode_tx>\S+)",
        )
        groups = cqe_mode_rx_tx_string.groupdict()
        parsed_data["cqe_mode_rx"] = [groups["cqe_mode_rx"]]
        parsed_data["cqe_mode_tx"] = [groups["cqe_mode_tx"]]

    def parse(self, output: str, option: str = "") -> Type[dataclass]:
        """
        Parse ethtool output.

        :param output: Ethtool output
        :param option: Ethtool option, e.g. -i
        :return: Parsed ethtool output in the form of dynamically generated dataclass corresponding to option
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=output)
        parse_raw_output = self._parse_output(output, option=option)
        if not parse_raw_output:
            raise EthtoolParserException(f"Error while trying to parse ethtool output for option: {option}")
        if option == "":
            supported_link_modes = []
            advertised_link_modes = []
            if "supported_link_modes" in parse_raw_output.keys():
                for pair in parse_raw_output["supported_link_modes"]:
                    supported_link_modes += pair.split()
                parse_raw_output["supported_link_modes"] = supported_link_modes
            if "advertised_link_modes" in parse_raw_output.keys():
                for pair in parse_raw_output["advertised_link_modes"]:
                    advertised_link_modes += pair.split()
                parse_raw_output["advertised_link_modes"] = advertised_link_modes
            if "supported_ports" in parse_raw_output.keys():
                supported_ports = parse_raw_output["supported_ports"][0].strip("[] ").split()
                parse_raw_output["supported_ports"] = supported_ports
            output_dataclass = make_dataclass(
                "EthtoolStandardInfo", [(k, List[str]) for k, v in parse_raw_output.items()]
            )
            return output_dataclass(**parse_raw_output)
        elif option == "--show-priv-flags":
            output_dataclass = make_dataclass(
                "EthtoolShowPrivFlags", [(k, List[str]) for k, v in parse_raw_output.items()]
            )
            return output_dataclass(**parse_raw_output)
        else:
            if option not in self._outputs_ds.keys():
                raise EthtoolParserException(f"Unsupported option: {option}")
            output_dataclass = make_dataclass(
                self._outputs_ds[option], [(k, List[str]) for k, v in parse_raw_output.items()]
            )
            return output_dataclass(**parse_raw_output)
