"""
Unit Conversion
"""
import math

def convert(type, flowunit, data):
    r"""Convert data to meter-kilogram-second
    
    Parameters
    ----------
    type : string
        options = 'Concentration', 'Demand', 'Flow', 'Emitter Coefficient', 
        'Pipe Diameter', 'Tank Diameter', 'Elevation', 'Hydraulic Head', 
        'Length', 'Velocity', 'Energy', 'Power', 'Pressure', 
        'Source Mass Injection', 'Volume', 'Water Age'
    
    flowunit: int
        flowunit = enData.ENgetflowunits()
        EN_CFS = 0 cubic feet per second
        EN_GPM = 1 gallons per minute
        EN_MGD = 2 million gallons per day
        EN_IMGD = 3 Imperial mgd
        EN_AFD = 4 acre-feet per day
        EN_LPS = 5 liters per second
        EN_LPM = 6 liters per minute
        EN_MLD = 7 million liters per day
        EN_CMH = 8 cubic meters per hour
        EN_CMD = 9 cubic meters per day
    
    data: numpy array or scalar
    
    Returns
    -------
    converted_data: numpy array or scalar
        Converted data, same size as data
        
    Examples
    --------
    >>> data = np.array([10,20,30])
    >>> en.units.convert('Length', 1, data)
    array([ 3.048,  6.096,  9.144])
    
    >>> en.units.convert('Pressure', 2, 30)
    21.096
    
    Notes
    -----
    Appendix A from EPANET2 user manual
    Units of Measure
    
    PARAMETER               US CUSTOMARY                SI METRIC
    flowunit                0,1,2,3,4                   5,6,7,8,9
    Concentration           mg/L or mg/L                mg/L or mg/L
    Demand                  (see Flow units)            (see Flow units)
    Diameter(Pipes)         inches                      millimeters
    Diameter(Tanks)         feet                        meters
    Efficiency              percent                     percent
    Elevation               feet                        meters
    Emitter Coefficient     flow units / (psi)1/2       flow units / (meters)1/2
    Energy                  kilowatt - hours            kilowatt - hours
    Flow                    CFS (cubic feet / sec)      LPS (liters / sec)
                            GPM (gallons / min)         LPM (liters / min)
                            MGD (million gal / day)     MLD (megaliters / day)
                            IMGD (Imperial MGD)         CMH (cubic meters / hr)
                            AFD (acre-feet / day)       CMD (cubic meters / day)
    Friction Factor         unitless                    unitless
    Hydraulic Head          feet                        meters
    Length                  feet                        meters
    Minor Loss Coeff.       unitless                    unitless
    Power                   horsepower                  kilowatts
    Pressure                psi                         meters
    Reaction Coeff. (Bulk)  1/day (1st-order)           1/day (1st-order)
    Reaction Coeff. (Wall)  mass / L / day (0-order)    mass / L / day (0-order)
                            ft / day (1st-order)        meters / day (1st-order)
    Roughness Coefficient   10-3 feet (Darcy-Weisbach)  millimeters (Darcy-Weisbach)
                            unitless otherwise          unitless otherwise
    Source Mass Injection   mass / minute               mass / minute
    Velocity                feet / second               meters / second
    Volume                  cubic feet                  cubic meters
    Water Age               hours                       hours
    
    Note: US Customary units apply when CFS, GPM, AFD, or MGD is chosen as flow
    units. SI Metric units apply when flow units are expressed using either 
    liters or cubic meters.
"""
    
    if type == 'Concentration':
        data = data * 1.0e-6 * 0.001 # mg/L to kg/m3
        
    if type in ['Demand', 'Flow', 'Emitter Coefficient']:
        if flowunit == 0: 
            data = data*0.0283168 # ft3/s to m3/s
        elif flowunit == 1: 
            data = (data*0.00378541)/60 # gall/min to m3/s
        elif flowunit == 2: 
            data = (data*1e6*0.00378541)/86400 # million gall/d to m3/s
        elif flowunit == 3: 
            data = (data*1e6*0.00454609)/86400 # million imperial gall/d to m3/s
        elif flowunit == 4: 
            data = (data*1233.48184)/86400 # acre-feet/day to m3/s
        elif flowunit == 5: # 
            data = data*0.001 # L/s to m3/s
        elif flowunit == 6: 
            data = (data*0.001)/60 # L/min to m3/s
        elif flowunit == 7: 
            data = (data*1e6*0.001)/86400 # million L/day to m3/s
        elif flowunit == 8: 
            data = data/3600 # m3/hour to m3/s
        elif flowunit == 9: 
            data = data/86400 # m3/day to m3/s
            
        if type == 'Emitter Coefficient':
            if flowunit in [0,1,2,3,4]:
                data = data / 0.7032 # flowunit/psi0.5 to flowunit/m0.5
                
    elif type == 'Pipe Diameter':
        if flowunit in [0,1,2,3,4]:
            data = data * 0.0254 # in to m
        else:
            data = data * 0.001 # mm to m
            
    elif type in ['Tank Diameter', 'Elevation', 'Hydraulic Head', 'Length']:
        if flowunit in [0,1,2,3,4]:
            data = data * 0.3048 # ft to m
    
    elif type in 'Velocity':
        if flowunit in [0,1,2,3,4]:
            data = data * 0.3048 # ft/s to m/s
            
    elif type == 'Energy':
        data = data*3600000 # kW*hr to J
        
    elif type == 'Power':
        if flowunit in [0,1,2,3,4]:
            data = data*745.699872 # hp to W (Nm/s)
        else:
            data = data/1000 # kW to W (Nm/s)
        
    elif type == 'Pressure':
        if flowunit in [0,1,2,3,4]:
            data = data * 0.7032 # psi to m
    
    elif type == 'Source Mass Injection':
        data = data /60 # per min to per second
        
    elif type == 'Volume':
        if flowunit in [0,1,2,3,4]:
            data = data * math.pow(0.3048, 3) # ft3 to m3 
            
    elif type == 'Water Age':
        data = data * 3600 # hr to s
        
    return data
