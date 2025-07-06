# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Copyright (c) [2025] [Bruno Henrique]

import re
import logging
import os
import argparse
from datetime import timedelta

script_dir = os.path.dirname(os.path.abspath(__file__))

TAG_BEFORE_LAYER_CHANGE = ";BEFORE_LAYER_CHANGE"
GCODE_SET_LCD_MESSAGE = "M117"

log_file_path = os.path.join(script_dir, "pps_display_info_on_lcd.log")
logging.basicConfig(
    filename=log_file_path,
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

def format_time(time_seconds):
    td = timedelta(seconds=time_seconds)
    h, m, s = td.seconds // 3600, (td.seconds % 3600) // 60, td.seconds % 60
    formatted_time = f"{h}h{m}m{s}s"
    return formatted_time

def log_message(message, success=True):
    if success:
        logging.info(f"✅ {message}")
    else:
        logging.info(f"❌ {message}")

def log_success(message):
    log_message(message)

def log_fail(message):
    log_message(message, False)

def parse_total_time(lines):
    """Parse estimated total print time from lines like:
       ; estimated printing time (normal mode) = 14m 55s
       ; estimated printing time (normal mode) = 1h 12m 30s
    """
    for line in lines:
        line_lower = line.lower()
        if "estimated printing time" in line_lower:
            time_parts = re.findall(r'(\d+)([hms])', line_lower)
            hours = minutes = seconds = 0
            for val, unit in time_parts:
                if unit == 'h':
                    hours = int(val)
                elif unit == 'm':
                    minutes = int(val)
                elif unit == 's':
                    seconds = int(val)
            estimated_time = hours * 3600 + minutes * 60 + seconds
            log_success(f"Estimated time found: {format_time(estimated_time)}.")
            return estimated_time

    log_fail("Could not find estimated time.")
    return 0

def parse_layer_count(lines):
    """Parse layer count from lines like:
       ; total layers count = 22
    """
    for line in lines:
        line_lower = line.lower()
        if "total layers count" in line_lower:
            try:
                layer_count = int(line.strip().split("=")[1].strip())
                log_success(f"Layer count found: {layer_count}.")
                return layer_count
            except:
                pass

    log_fail("Could not find layer count.")
    return None

def inject_m117_lines(input_file):
    with open(input_file, "r") as f:
        lines = f.readlines()

    total_time = parse_total_time(lines)
    total_layers = parse_layer_count(lines)

    if total_time == 0:
        return

    if total_layers is None:
        return

    time_per_layer = total_time / total_layers
    layer_num = 0
    output_lines = []

    for line in lines:
        msg = ""

        if line.startswith(TAG_BEFORE_LAYER_CHANGE):
            remaining_time = int(round((total_layers - layer_num) * time_per_layer))

            formatted_time = format_time(remaining_time)

            layer_num += 1

            msg = f"{GCODE_SET_LCD_MESSAGE} {layer_num}/{total_layers} | ET {formatted_time}\n"

        output_lines.append(line)

        if msg:
            output_lines.append(msg)

    with open(input_file, "w") as f:
        f.writelines(output_lines)

    log_success(f"{GCODE_SET_LCD_MESSAGE} messages injected into {input_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Post-process G-code adding M117 messages with estimated time and current layers."
    )
    parser.add_argument("input_file", help="Path to the input G-code file.")
    args = parser.parse_args()

    inject_m117_lines(input_file=args.input_file)