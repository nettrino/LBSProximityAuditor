class Enum(set):
    """Defines an enumeration
    """
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

# rounding levels for the proximity oracle
ROUNDING = Enum(["UP", "DOWN", "BOTH"])
# log level
LOG = Enum(["STANDARD", "ALL"])
