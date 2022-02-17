from . import lacing_base


def create_subclasses_list(cls):
    return {subclass.__name__: subclass for subclass in cls.__subclasses__()}


ShoeLacingMethods = create_subclasses_list(lacing_base.ShoeLacing)
