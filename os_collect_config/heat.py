#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from heatclient import client as heatclient
from keystoneclient.v3 import client as keystoneclient
from oslo_config import cfg
from oslo_log import log

from os_collect_config import exc
from os_collect_config import keystone
from os_collect_config import merger

CONF = cfg.CONF
logger = log.getLogger(__name__)

opts = [
    cfg.StrOpt('user-id',
               help='User ID for API authentication'),
    cfg.StrOpt('password',
               help='Password for API authentication'),
    cfg.StrOpt('project-id',
               help='ID of project for API authentication'),
    cfg.StrOpt('auth-url',
               help='URL for API authentication'),
    cfg.StrOpt('stack-id',
               help='ID of the stack this deployment belongs to'),
    cfg.StrOpt('resource-name',
               help='Name of resource in the stack to be polled'),
    cfg.StrOpt('region-name',
               help='Region Name for extracting Heat endpoint'),
    cfg.BoolOpt('ssl-certificate-validation',
                help='ssl certificat validation flag for connect to heat',
                default=False),
    cfg.StrOpt('ca-file',
               help='CA Cert file for connect to heat'),
]
name = 'heat'


class Collector(object):
    def __init__(self,
                 keystoneclient=keystoneclient,
                 heatclient=heatclient,
                 discover_class=None):
        self.keystoneclient = keystoneclient
        self.heatclient = heatclient
        self.discover_class = discover_class

    def collect(self):
        if CONF.heat.auth_url is None:
            logger.info('No auth_url configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.password is None:
            logger.info('No password configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.project_id is None:
            logger.info('No project_id configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.user_id is None:
            logger.info('No user_id configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.stack_id is None:
            logger.info('No stack_id configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.resource_name is None:
            logger.info('No resource_name configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.ssl_certificate_validation is None:
            logger.info('No ssl_certificate_validation configured.')
            raise exc.HeatMetadataNotConfigured
        if CONF.heat.ca_file is None:
            logger.info('No ca_file configured.')
            raise exc.HeatMetadataNotConfigured
        # NOTE(flwang): To be compatible with old versions, we won't throw
        # error here if there is no region name.

        try:
            ks = keystone.Keystone(
                auth_url=CONF.heat.auth_url,
                user_id=CONF.heat.user_id,
                password=CONF.heat.password,
                project_id=CONF.heat.project_id,
                ca_file=CONF.heat.ca_file,
                ssl_certificate_validation=CONF.heat.ssl_certificate_validation,
                keystoneclient=self.keystoneclient,
                discover_class=self.discover_class).client
            kwargs = {'service_type': 'orchestration',
                      'endpoint_type': 'publicURL'}
            if CONF.heat.region_name:
                kwargs['region_name'] = CONF.heat.region_name
            endpoint = ks.service_catalog.url_for(**kwargs)
            logger.debug('Fetching metadata from %s' % endpoint)
            heat = self.heatclient.Client(
                '1', endpoint, token=ks.auth_token)
            r = heat.resources.metadata(CONF.heat.stack_id,
                                        CONF.heat.resource_name)

            final_list = merger.merged_list_from_content(
                r, cfg.CONF.deployment_key, name)
            return final_list

        except Exception as e:
            logger.warn(str(e))
            raise exc.HeatMetadataNotAvailable
