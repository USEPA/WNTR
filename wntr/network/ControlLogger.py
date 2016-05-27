import wntr


class ControlLogger(object):
    def __init__(self):
        self.changed_objects = {}  # obj_name: object
        self.changed_attributes = {}  # obj_name: attribute

    def add(self, obj, attr):
        if obj.name() in self.changed_objects:
            self.changed_attributes[obj.name()].append(attr)
        else:
            self.changed_objects[obj.name()] = obj
            self.changed_attributes[obj.name()] = [attr]

    def reset(self):
        self.changed_objects = {}
        self.changed_attributes = {}