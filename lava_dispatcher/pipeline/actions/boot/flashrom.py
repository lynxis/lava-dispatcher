# Copyright (C) 2016 Alexander Couzens <lynxis@fe80.eu>
#
# Author: Alexander Couzens <lynxis@fe80.eu>
#
# This file is part of LAVA Dispatcher.
#
# LAVA Dispatcher is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# LAVA Dispatcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along
# with this program; if not, see <http://www.gnu.org/licenses>.

from lava_dispatcher.pipeline.action import (
    Action,
    Pipeline,
    InfrastructureError,
)
from lava_dispatcher.pipeline.logical import Boot
from lava_dispatcher.pipeline.actions.boot import BootAction, AutoLoginAction
from lava_dispatcher.pipeline.shell import ExpectShellSession
from lava_dispatcher.pipeline.connections.serial import ConnectDevice
from time import sleep

class BootFlashrom(Boot):
    """
    Expects flashrom bootloader, and boots.
    """
    compatibility = 1

    def __init__(self, parent, parameters):
        super(BootFlashrom, self).__init__(parent)
        self.action = BootFlashromAction()
        self.action.section = self.action_type
        self.action.job = self.job
        parent.add_action(self.action, parameters)

    @classmethod
    def accepts(cls, device, parameters):
        if 'method' in parameters:
            if parameters['method'] == 'flashrom':
                return True
        return False

class BootFlashromAction(BootAction):
    """
    Provide for auto_login parameters in this boot stanza and re-establish the
    connection after boot.
    """
    def __init__(self):
        super(BootFlashromAction, self).__init__()
        self.name = "flashrom_boot"
        self.summary = "flashrom boot"
        self.description = "flashrom boot into the system"

    def populate(self, parameters):
        self.internal_pipeline = Pipeline(parent=self, job=self.job, parameters=parameters)
        self.internal_pipeline.add_action(ConnectDevice())
        self.internal_pipeline.add_action(PowerButton())
        self.internal_pipeline.add_action(AutoLoginAction())
        self.internal_pipeline.add_action(ExpectShellSession())  # wait

    def run(self, connection, args=None):
        connection = super(BootFlashromAction, self).run(connection, args)
        self.data['boot-result'] = 'failed' if self.errors else 'success'
        return connection

class PowerButton(Action):
    """
    press the power button
    """
    def __init__(self):
        super(PowerButton, self).__init__()
        self.name = "power_button"
        self.summary = "press the power button"
        self.description = "press the power button."

    def run(self, connection, args=None):
        connection = super(PowerButton, self).run(connection, args)
        self.logger.debug("Pressing power button")
        self.logger.info("Wait 10 secs before pressing the button to give pdu daemon enough time to react")
        sleep(10)
        command = self.job.device['commands']['power_button']
        if not self.run_command(command.split(' ')):
            raise InfrastructureError("%s command failed" % command)
        return connection

