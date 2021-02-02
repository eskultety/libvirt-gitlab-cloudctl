import abc


class AbstractBackend(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def vm_new(self, instance_name, template_name):
        pass

    @abc.abstractmethod
    def vm_rebuild(self, instance_name, template_name=None):
        pass

    @abc.abstractmethod
    def vm_start(self, instance_name):
        pass

    @abc.abstractmethod
    def vm_stop(self, instance_name):
        pass

    @abc.abstractmethod
    def vm_delete(self, instance_name):
        pass
