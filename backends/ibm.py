import ibm_vpc as ibm
import sys

from ibm_cloud_sdk_core import ApiException as IBMException
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator as IBMAuthenticator

from backends.abstract import AbstractBackend


class IBM(AbstractBackend):
    def __init__(self, auth_token, sshkey=""):
        self.authenticator = IBMAuthenticator(auth_token)
        self.service = ibm.VpcV1(authenticator=self.authenticator)
        self.instances = self._list_resource_objects("instances",
                                                     self.service.list_instances)
        self.templates = self._list_resource_objects("templates",
                                                     self.service.list_instance_templates)

    @staticmethod
    def _list_resource_objects(resource_name, vpc_callback):
        #TODO: replace listing with the get_instance_template call to get a
        # specific template to instantiate
        objs = None

        try:
            json_data = vpc_callback()
            objs = json_data.get_result()[resource_name]
        except IBMException as e:
            print("error: failed to fetch {} : {}".format(resource_name,
                                                          str(e.code)),
                  file=sys.stderr)
        return objs

    def vm_start(self, name):
        pass

    def vm_stop(self, name):
        pass

    def vm_rebuild(self, name, template, ssh_pubkey):
        # IBM doesn't support machine rebuilds
        pass

    def vm_new(self, name, template, ssh_pubkey):
        """ Create a new machine with label '@name' from template '@template' """

        # shortcut variable references
        primary_nic = self.templates[0]["primary_network_interface"]
        security_groups = primary_nic["security_groups"]

        # models - almost minimal attribute set to spin up an instance
        security_group_model = {}
        security_group_model["id"] = security_groups[0]["id"]

        primary_nic_model = {}
        primary_nic_model["name"] = primary_nic["name"]
        primary_nic_model["subnet"] = primary_nic["subnet"]
        primary_nic_model["security_groups"] = [security_group_model]

        instance_prototype = {}
        instance_prototype["name"] = name
        instance_prototype["vpc"] = self.templates[0]["vpc"]
        instance_prototype["profile"] = self.templates[0]["profile"]
        instance_prototype["keys"] = self.templates[0]["keys"]
        instance_prototype["user_data"] = self.templates[0]["user_data"]
        instance_prototype["zone"] = self.templates[0]["zone"]
        instance_prototype["image"] = self.templates[0]["image"]
        instance_prototype["primary_network_interface"] = primary_nic_model

        try:
            new_instance = self.service.create_instance(instance_prototype)
        except IBMException as e:
            print("error: failed to create new instance: {}".format(str(e.code)),
                  file=sys.stderr)

    def vm_delete(self, name):
        """ Delete a machine with label '@label' """
        return self.service.delete_instance(name)
