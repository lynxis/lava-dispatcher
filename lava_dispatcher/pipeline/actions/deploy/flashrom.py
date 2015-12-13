# Copyright (C) 2015 Alexander Couzens <lynxis@fe80.eu>
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

import os
from lava_dispatcher.pipeline.logical import Deployment
from lava_dispatcher.pipeline.connections.ssh import Scp
from lava_dispatcher.pipeline.action import Pipeline, Action, InfrastructureError
from lava_dispatcher.pipeline.utils.filesystem import mkdtemp
from lava_dispatcher.pipeline.actions.deploy import DeployAction
from lava_dispatcher.pipeline.actions.deploy.apply_overlay import ExtractRootfs, ExtractModules
from lava_dispatcher.pipeline.actions.deploy.environment import DeployDeviceEnvironment
from lava_dispatcher.pipeline.actions.deploy.download import DownloaderAction
from lava_dispatcher.pipeline.power import PowerOn, PowerOff
from lava_dispatcher.pipeline.utils.constants import DISPATCHER_DOWNLOAD_DIR
from lava_dispatcher.pipeline.utils.shell import infrastructure_error

class Flashrom(Deployment):
    """
    Flash a spi chip via Flashrom
    """

    # TODO: check what compatiblity means?
    compatibility = 1

    def __init__(self, parent, parameters):
        super(Flashrom, self).__init__(parent)
        self.action = FlashRomDeploy()
        self.action.job = self.job
        parent.add_action(self.action, parameters)

    @classmethod
    def accepts(cls, device, parameters):
        if 'actions' not in device or 'deploy' not in device['actions']:
            return False
        if 'methods' not in device['actions']['deploy']:
            return False
        if 'flashrom' not in device['actions']['deploy']['methods']:
            return False
        if 'to' in parameters and 'flashrom' != parameters['to']:
            return False
        return True

class FlashRomDeploy(DeployAction):
    # call flashrom but before put CopyViaScp into pipline
    def __init__(self):
        super(FlashRomDeploy, self).__init__()
        self.name = "flashrom"
        self.summary = "deploy a coreboot image via flashrom"
        self.description = "deploy a coreboot image via flashrom"
        self.section = 'deploy'
        self.items = []
        try:
            self.scp_dir = mkdtemp(basedir=DISPATCHER_DOWNLOAD_DIR)
        except OSError:
            # allows for unit tests to operate as normal user.
            self.suffix = '/'

    def validate(self):
        super(FlashRomDeploy, self).validate()
        if 'coreboot' not in self.parameters:
            self.errors = "%s needs a coreboot to deploy" % self.name
        if not self.valid:
            return
        lava_test_results_dir = self.parameters['deployment_data']['lava_test_results_dir']
        self.data['lava_test_results_dir'] = lava_test_results_dir % self.job.job_id
        if self.suffix:
            self.data[self.name].setdefault('suffix', self.suffix)
        self.data[self.name].setdefault('suffix', os.path.basename(self.scp_dir))
        self.errors = infrastructure_error('flashrom')

    def populate(self, parameters):
        self.internal_pipeline = Pipeline(parent=self, job=self.job, parameters=parameters)
        # download coreboot image
        download = DownloaderAction('coreboot', path=self.scp_dir)
        download.max_retries = 3  # overridden by failure_retry in the parameters, if set.
        # download coreboot image
        flashspi = FlashSPI('coreboot', path=self.scp_dir)
        self.internal_pipeline.add_action(PowerOff())
        self.internal_pipeline.add_action(download)
        self.internal_pipeline.add_action(SPIPowerOn())
        self.internal_pipeline.add_action(flashspi)
        self.internal_pipeline.add_action(SPIPowerOff())
        self.internal_pipeline.add_action(PowerOn())

class FlashSPI(Action):
    def __init__(self, key, path):
        super(FlashSPI, self).__init__()
        self.name = "flash spi"
        self.summary = "execute flashrom to flash the device"
        self.description = "execute flashrom to flash the device"
        self.key = key  # the key in the parameters of what to download
        self.path = path  # where to download

    def run(self):
        connection = super(FlashSPI, self).run(connection, args)
        command_output = self.run_command(adb_cmd)

class SPIPowerOn(Action):
    """
    Turn on external SPI power
    """
    def __init__(self):
        super(SPIPowerOn, self).__init__()
        self.name = "spi_power_on"
        self.summary = "send power_on command to SPI"
        self.description = "power on to extern SPI power"

    def run(self, connection, args=None):
        connection = super(SPIPowerOn, self).run(connection, args)
        if not hasattr(self.job.device, 'power_state'):
            return connection

        if self.job.device.power_state is not 'off':
            raise RuntimeError("device is powered. This can break the device!")

        command = self.job.device['commands']['spi_power_on']
        if not self.run_command(command.split(' ')):
            raise InfrastructureError("%s command failed" % command)
        return connection

class SPIPowerOff(Action):
    """
    Turns off external SPI power
    """
    def __init__(self):
        super(SPIPowerOff, self).__init__()
        self.name = "spi_power_off"
        self.summary = "send power_off command to SPI"
        self.description = "discontinue power to extern SPI power"

    def run(self, connection, args=None):
        connection = super(SPIPowerOff, self).run(connection, args)
        if not hasattr(self.job.device, 'power_state'):
            return connection

        command = self.job.device['commands']['spi_power_off']
        if not self.run_command(command.split(' ')):
            raise InfrastructureError("%s command failed" % command)
        return connection
