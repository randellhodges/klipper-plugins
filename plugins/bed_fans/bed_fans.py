import logging
import math

from klippy.extras import fan

EVENT_INTERVAL = 1.
SEP_1 = '='
SEP_2 = ','

# PEP 485 isclose()
def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

class BedFans:

    def __init__(self, config):

        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()

        self.fan_name = config.get("fan")
        self.heater_name = config.get("heater", default="heater_bed")

        self.gcode = self.printer.lookup_object("gcode")

        self.heater = None
        self.fan = None

        ranges = config.get("ranges")
        self._set_ranges(ranges)

        self.enabled = config.getboolean("enable_on_start", False)
        self.timer = self.reactor.register_timer(self._tick_event)

        # Register printer events
        self.printer.register_event_handler("klippy:ready", 
                                            self._handle_ready)

        # Register gcode commands
        self.gcode.register_command("QUERY_BED_FANS",
                                    self.cmd_QUERY_BED_FANS,
                                    desc=self.cmd_QUERY_BED_FANS_help)
        self.gcode.register_command("SET_BED_FANS",
                                    self.cmd_SET_BED_FANS,
                                    desc=self.cmd_SET_BED_FANS_help)

    cmd_SET_BED_FANS_help = "Changes BED FANS stuff"
    def cmd_SET_BED_FANS(self, gcmd):

        enable = gcmd.get("ENABLE", default=self.enabled, parser=int)
        enable = bool(enable)

        ranges = gcmd.get("RANGES", default=None)

        self._set_ranges(ranges)
        self._set_enabled(enable)

    cmd_QUERY_BED_FANS_help = "Queries BED FANS stuff"
    def cmd_QUERY_BED_FANS(self, gcmd):

        ranges = SEP_2.join(map(lambda x: str(x[0]) + SEP_1 + str(x[1]), self.ranges))
        msg = f"BED FANS ENABLED: {self.enabled}\nRANGES: {ranges}"

        gcmd.respond_info(msg, log=False)

    def _handle_ready(self):

        self.heater = self.printer.lookup_object(self.heater_name)
        self.fan = self.printer.lookup_object(self.fan_name)

        if self.heater is None or self.fan is None:
            pass

        if self.enabled:
            self.reactor.update_timer(self.timer, self.reactor.NOW)

    def _set_ranges(self, ranges):
        if ranges:
            ranges = [[float(x) for x in list.split(SEP_1)] for list in ranges.split(SEP_2)]
            self.ranges = list(ranges)
            self.ranges.sort()

    def _set_enabled(self, enable):
        if enable != self.enabled:
            if enable:
                self.reactor.update_timer(self.timer, self.reactor.NOW)
            else:
                self.reactor.update_timer(self.timer, self.reactor.NEVER)
                self._set_fan_speed(0)
            self.enabled = enable

    def _tick_event(self, eventtime):

        if self.printer.is_shutdown():
            return self.reactor.NEVER

        heater_status = self.heater.get_status(eventtime)
        fan_status = self.fan.get_status(eventtime)

        temperature = float(heater_status.get("temperature", 0))
        target_fan_speed = 0.

        for min_temp, fan_speed in self.ranges:
            if temperature < min_temp:
                continue
            target_fan_speed = fan_speed

        current_fan_speed = fan_status.get("speed", None)
        if current_fan_speed is not None:
            if not isclose(current_fan_speed, target_fan_speed, abs_tol=1e-2):
                self._set_fan_speed(target_fan_speed)

        return eventtime + EVENT_INTERVAL

    def _set_fan_speed(self, fan_speed):
        fan = self.fan.fan
        fan.set_speed_from_command(fan_speed)

def load_config(config):
    return BedFans(config)
