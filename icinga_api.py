#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2016, Dan Vaida <vaida.dan@gmail.com>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.


DOCUMENTATION = '''
---
module: icinga_api
version_added: "0.1"
author: "Dan Vaida (@danvaida)"
short_description: Interact with the Icinga API
description:
  - A module to control Icinga through its API.
  - Certificate-based authentication shall be added in a future version.
  - This modules expects that the API feature of Icinga has already been enabled, configured and is available.
requirements: []
options:
  url:
    description:
      - The URL address of the Icinga API. This is set to HTTPS protocol.
    required: true
  port:
    description:
      - The port number behind which the Icinga API is listening.
    required: false
    default: "5665"
  user:
    description:
      - The username used to connect to the API.
    required: true
    default: "root"
    aliases: [ "url_username" ]
  password:
    description:
      - The password used to connect to the API.
    required: true
    default: "icinga"
    aliases: [ "url_password" ]
  endpoint:
    description:
      - The API endpoint that you want to make the request against.
    required: true
    choices: [ "objects", "status" ]
  object_family:
    description:
      - The "family" (type) of the configuration object.
    required: true
    choices: [ "zones", "hostgroups", "hosts", "servicegroups", "services" ]
  object_name:
    description:
      - The name of the object to handle.
    required: false
  state:
    description:
      - Delete, create or update if configuration object already exists.
    required: false
    choices: [ "present", "absent" ]
    default: "present"
  headers:
    description:
      - Sets custom HTTP headers.
      - Pass custom headers in the form of YAML hash/dict.
    required: false
  validate_certs:
    description:
      - If set to C(false), SSL certificates will not be validated.
      - This should only be set to C(false) when used on personally controlled sites using self-signed certificates.
    required: false
    choices: [ "true", "false" ]
    default: "true"
  cascade_delete:
    description:
      - Delete object(s) that are depending on the deleted object(s) (e.g. services on a host).
      - May be used in conjunction with C(state=absent).
    required: false
    choices: [ "true", "false" ]
    default: false
  definition:
    description:
      - Definition of the configuration object.
      - Must be used when C(endpoint=objects) and C(state=present).
      - Send configuration object definition as JSON.
    required: false
'''

EXAMPLES = '''
---
# Here's an example of a variable structure and a task that creates multiple zone configuration objects (play excerpt):
- vars:
  icinga_zones:
    - name: checker
      definition:
        templates: [ "generic-zone" ]
        attrs:
          endpoints: [ "master" ]
- tasks:
    - icinga_api:
        url: icinga.example.com
        endpoint: objects
        object_family: zones
        object_name: "{{ item.name }}"
        definition: "{{ item.definition | to_json }}"
      with_items: "{{ icinga_zones }}"

# Create ssh service for web host:
- icinga_api:
    url: 127.0.0.1
    endpoint: objects
    object_family: services
    object_name: 'web!ssh'
    definition: "{{ lookup('file','ssh.json') }}"

# Fetch status information about your Icinga instance:
- icinga_api: url=your.icinga.com endpoint=status

# Fetch object definition for service
- icinga_api:
    url: your.icinga.com
    endpoint: objects
    object_family: services
    object_name: 'host!disk'
  register: icinga_host_disk

- debug: var="{{ icinga_host_disk }}"
'''

RETURN = '''
---
url:
  description: https address of the targetted Icinga API
  returned: always
  type: string
  sample: "https://monitoring.example.com"
port:
  description: port on which the Icinga API is listenting
  returned: always
  type: int
  sample: "5665"
user:
  description: the username used for authentication
  returned: always
  type: string
  sample: "root"
password:
  description: the password used for authentication
  returned: always
  type: string
  sample: "icinga"
endpoint:
  description: the API endpoint. not to be confused with the C(url) parameter
  returned: always
  type: string
  sample: "status"
object_family:
  description: the type of the configuration object. always plural form
  returned: when supported
  type: string
  sample: "servicegroups"
object_name:
  description: the name of the configuration object. services have composed names
  returned: when supported
  type: string
  sample: "srv10!nginx"
state:
  description: the state of the configuration object. absent means delete, present means create or update (PUT or POST verbs)
  returned: when supported
  type: string
  sample: "absent"
headers:
  description: the request headers sent to the API
  returned: when supported
  type: dictionary
  sample: {
    Accept: 'application/json',
    User-Agent: 'AnsibleIcingaModule',
  }
validate_certs:
  description: wether or not to validate the presented SSL certificate
  returned: when supported
  type: boolean
  sample: True
cascade_delete:
  description: deletes object(s) that are depending on the deleted object(s) (e.g. services on a host). requires C(state=absent)
  returned: when supported
  type: boolean
  sample: False
definition:
  description: the data sent to the API. requires C(endpoint=objects) and C(state=present)
  returned: when supported
  type: dictionary
  sample: {
    templates: [ "generic-host" ]
    attrs:
      address: 127.0.0.1
      vars.hostgroups: databases
      groups: [ "databases" ]
  }
'''

def main():

    changed = False
    failed  = False

    params = {
        "url": {
            "required": True,
            "default": None,
            "type": 'str'
        },
        "port": {
            "required": False,
            "default": '5665',
            "type": 'int'
        },
        "url_username": {
            "required": False,
            "default": 'root',
            "aliases": ['user']
        },
        "url_password": {
            "required": False,
            "default": 'icinga',
            "aliases": ['password']
        },
        "endpoint": {
            "required": True,
            "default": None,
            "type": 'str',
            "choices": ['objects', 'status']
        },
        "object_family": {
            "required": False,
            "default": None,
            "type": 'str',
            "choices": ['zones', 'hostgroups', 'hosts', 'servicegroups', 'services']
        },
        "object_name": {
            "required": False,
            "default": None,
            "type": 'str',
            "aliases": ['name']
        },
        "state": {
            "required": False,
            "default": 'present',
            "type": 'str',
            "choices": ['present', 'absent']
        },
        "headers": {
            "required": False,
            "default": {},
            "type": 'dict'
        },
        "cascade_delete": {
            "required": False,
            "default": False,
            "type": 'bool',
            "choices": ['true', 'false']
        },
        "definition": {
            "required": False,
            "default": {},
            "type": 'dict'
        }
    }
    argument_spec = url_argument_spec()
    argument_spec.update(params)
    argument_spec.update(dict(
        mutually_exclusive=(('cascade_delete', 'definition')),
        check_invalid_arguments=False,
        supports_check_mode=True
    ))

    module = AnsibleModule(
        argument_spec=argument_spec
    )

    module.exit_json(changed=False, meta=module.params)


# import module snippets
from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

if __name__ == '__main__':
    main()
