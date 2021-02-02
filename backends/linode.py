import linode_api4 as li
import sys

from time import sleep

from backends.abstract import AbstractBackend


LINODE_REGION = "eu-west"
LINODE_TYPE = "g6-standard-4"


class Linode(AbstractBackend):
    def _sync_wait(self, name=None, status=None):
        if not name:
            print("internal error: name cannot be None",
                  file=sys.stderr)
            return

        timeout = 5

        # If we're not waiting for status it means the machine is being deleted
        # so we have to resort to issuing a GET query instead of polling our
        # local copy
        if not status:
            try:
                while self._get_linodes()[name]:
                    sleep(timeout)
            except KeyError:
                return

        else:
            linode = self.linodes[name]
            while linode.status != status:
                sleep(timeout)

    def __init__(self, auth_token, sshkey=""):
        self.client = li.LinodeClient(auth_token)
        self.linodes = self._get_linodes()
        self.sshkey = sshkey

    def _get_linodes(self):
        """ Utility helper caching the linodes in a dictionary """

        linodes = self.client.linode.instances()
        return {i.label:i for i in linodes}

    def _get_create_params(self, template, ssh_pubkey):
        """
        Utility helper to aggregate common creation params like SSH keys and
        image name
        """

        params = {
            "sshkey": ssh_pubkey,
            "image": self.client.images(li.Image.label == template).first(),
        }

        return params

    def vm_start(self, name, sync=True):
        """ Start a machine with label '@name' """

        linode = self.linodes[name]

        if linode.status != "running":
            linode.boot()

        if sync:
            self._sync_wait(name, "running")

    def vm_stop(self, name, sync=True):
        """ Stop a machine with label '@name' """

        linode = self.linodes[name]

        if linode.status == "running":
            linode.shutdown()

        if sync:
            self._sync_wait(name, "offline")

    def vm_rebuild(self, name, template, ssh_pubkey=None, sync=True):
        """ Rebuild a machine with label '@name' from template '@template' """

        try:
            linode = self.linodes[name]
        except KeyError:
            sys.exit(f"Machine '{name} not found'")

        params = self._get_create_params(template, ssh_pubkey)
        self.vm_stop(name, sync)

        linode.rebuild(params["image"], authorized_keys=[params["sshkey"]])

        if sync:
            self._sync_wait(name, "running")

    def vm_new(self, name, template, ssh_pubkey=None, sync=True):
        """ Create a new machine with label '@name' from template '@template' """

        try:
            linode = self.linodes[name]
            sys.exit(f"Machine '{name}' already exists")
        except KeyError:
            pass

        # Linode currently doesn't support resize on boot disks instantiated
        # from custom images, so we need to hack around a bit.
        params = self._get_create_params(template, ssh_pubkey)

        print(f"Creating an empty instance '{name}'...", end="", flush=True)
        instance = self.client.linode.instance_create(LINODE_TYPE,
                                                      LINODE_REGION,
                                                      label=name)

        # Populate our internal instance cache
        self.linodes[name] = instance

        # Now we need to wait for an empty instance to be created
        # TODO: Once Linode supports boot disk resize with custom images, we
        # can drop the below code
        if sync:
            self._sync_wait(name, "offline")
        print("DONE")

        swap_disk_size = 1024
        boot_disk_size = instance.specs.disk - swap_disk_size

        print("Creating a new swap disk...", end="", flush=True)
        swap_disk = instance.disk_create(size=swap_disk_size,
                                         filesystem="swap",
                                         label="SWAP")

        while swap_disk.status != "ready":
            sleep(2)
        print("DONE")

        # breakpoint()
        print("Creating a new boot disk...", end="", flush=True)
        boot_disk, _ = instance.disk_create(size=boot_disk_size,
                                            image=params["image"],
                                            authorized_keys=params["sshkey"],
                                            label="BOOT",
                                           )

        while boot_disk.status != "ready":
            sleep(2)
        print("DONE")

        # we need a boot config before starting the instance
        config = instance.config_create(label="boot_config",
                                        disks=[boot_disk, swap_disk])

        # finally we can boot the instance
        print(f"Booting instance '{name}'...", end="", flush=True)
        instance.boot()

        if sync:
            self._sync_wait(name, "running")
        print("DONE")

        print(f"Your instance is ready with IP: {instance.ipv4[0]}")

    def vm_delete(self, name, sync=True):
        """ Delete machine with label '@name' """

        try:
            linode = self.linodes[name]
        except KeyError:
            sys.exit(f"Machine '{name}' not found")

        print(f"Deleting instance '{name}'...", end="", flush=True)

        linode = self.linodes[name]

        linode.delete()

        if sync:
            self._sync_wait(name, status=None)

        print("DONE")
