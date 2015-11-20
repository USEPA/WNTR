
class Waterquality(object):
    """
    Waterquality scenario class.
    """

    def __init__(self, quality_type, nodes=None, source_type=None, source_quality=None, start_time=None, end_time=None):
        self.quality_type = quality_type
        """ Water quality simulation type, options = CHEM, AGE, or TRACE"""
        self.nodes = nodes
        """ List of injection nodes, used for CHEM and TRACE only"""
        self.source_type = source_type
        """ Source type, used for CHEM only, options = CONCEN, MASS, FLOWPACED, or SETPOINT"""
        self.source_quality = source_quality
        """ Source quality, used for CHEM only (kg/m3 if source_type = CONCEN, otherwise kg/s)"""
        self.start_time = start_time
        """ Injection start time, used for CHEM only (s)"""
        self.end_time = end_time
        """ Injection end time, used for CHEM only (s), -1 = end of simulation"""
