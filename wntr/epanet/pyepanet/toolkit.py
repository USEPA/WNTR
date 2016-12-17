"""
Python extensions for the EPANET Programmers Toolkit DLLs.
EPANET toolkit constants.
"""
optNodeParams = ['EN_ELEVATION', 'EN_BASEDEMAND', 'EN_PATTERN', 'EN_EMITTER',
                'EN_INITQUAL', 'EN_SOURCEQUAL', 'EN_SOURCEPAT', 'EN_SOURCETYPE',
                'EN_TANKLEVEL', 'EN_DEMAND', 'EN_HEAD', 'EN_PRESSURE',
                'EN_QUALITY', 'EN_SOURCEMASS', 'EN_INITVOLUME', 'EN_MIXMODEL',
                'EN_MIXZONEVOL', 'EN_TANKDIAM', 'EN_MINVOLUME', 'EN_VOLCURVE',
                'EN_MINLEVEL', 'EN_MAXLEVEL', 'EN_MIXFRACTION', 'EN_TANK_KBULK',
                'EN_TANKVOLUME']

optLinkParams = ['EN_DIAMETER', 'EN_LENGTH', 'EN_ROUGHNESS', 'EN_MINORLOSS',
                'EN_INITSTATUS', 'EN_INITSETTING', 'EN_KBULK', 'EN_KWALL',
                'EN_FLOW', 'EN_VELOCITY', 'EN_HEADLOSS', 'EN_STATUS',
                'EN_SETTING', 'EN_ENERGY', 'EN_LINKQUAL']

optTimeParams = ['EN_DURATION', 'EN_HYDSTEP', 'EN_QUALSTEP', 'EN_PATTERNSTEP',
                'EN_PATTERNSTART', 'EN_REPORTSTEP', 'EN_REPORTSTART',
                'EN_RULESTEP', 'EN_STATISTIC', 'EN_PERIODS', 'EN_STARTTIME']

optComponentCounts = ['EN_NODECOUNT', 'EN_TANKCOUNT', 'EN_LINKCOUNT', 
                'EN_PATCOUNT', 'EN_CURVECOUNT', 'EN_CONTROLCOUNT']

optNodeTypes = ['EN_JUNCTION', 'EN_RESERVOIR', 'EN_TANK']

optLinkTypes = ['EN_CVPIPE', 'EN_PIPE', 'EN_PUMP', 'EN_PRV', 'EN_PSV', 'EN_PBV',
                'EN_FCV', 'EN_TCV', 'EN_GPV']

optQualTypes = ['EN_NONE', 'EN_CHEM', 'EN_AGE', 'EN_TRACE']

optSourceTypes = ['EN_CONCEN', 'EN_MASS', 'EN_SETPOINT', 'EN_FLOWPACED']

optFlowUnits = ['EN_CFS', 'EN_GPM', 'EN_MGD', 'EN_IMGD', 'EN_AFD', 'EN_LPS',
                'EN_LPM', 'EN_MLD', 'EN_CMH', 'ENCMD']

optMiscOptions = ['EN_TRIALS', 'EN_ACCURACY', 'EN_TOLERANCE', 'EN_EMITEXPON',
                'EN_DEMANDMULT']

optControlTypes = ['EN_LOWLEVEL', 'EN_HILEVEL', 'EN_TIMER', 'EN_TIMEOFDAY']

optTimeTypes = ['', 'EN_AVERAGE', 'EN_MINIMUM', 'EN_MAXIMUM', 'EN_RANGE']

optMixModels = ['EN_MIX1', 'EN_MIX2', 'EN_FIFO', 'EN_LIFO']

optFileFlag = ['EN_NOSAVE', 'EN_SAVE']

optInitFlow = ['EN_INITFLOW']

EN_ELEVATION   = 0    # Node parameters 
EN_BASEDEMAND  = 1
EN_PATTERN     = 2
EN_EMITTER     = 3
EN_INITQUAL    = 4
EN_SOURCEQUAL  = 5
EN_SOURCEPAT   = 6
EN_SOURCETYPE  = 7
EN_TANKLEVEL   = 8
EN_DEMAND      = 9
EN_HEAD        = 10
EN_PRESSURE    = 11
EN_QUALITY     = 12
EN_SOURCEMASS  = 13
EN_INITVOLUME  = 14
EN_MIXMODEL    = 15
EN_MIXZONEVOL  = 16
EN_TANKDIAM    = 17
EN_MINVOLUME   = 18
EN_VOLCURVE    = 19
EN_MINLEVEL    = 20
EN_MAXLEVEL    = 21
EN_MIXFRACTION = 22
EN_TANK_KBULK  = 23
EN_TANKVOLUME  = 24     # TNT 

EN_DIAMETER    = 0    # Link parameters 
EN_LENGTH      = 1
EN_ROUGHNESS   = 2
EN_MINORLOSS   = 3
EN_INITSTATUS  = 4
EN_INITSETTING = 5
EN_KBULK       = 6
EN_KWALL       = 7
EN_FLOW        = 8
EN_VELOCITY    = 9
EN_HEADLOSS    = 10
EN_STATUS      = 11
EN_SETTING     = 12
EN_ENERGY      = 13
EN_LINKQUAL    = 14     # TNT 

EN_DURATION    = 0    # Time parameters 
EN_HYDSTEP     = 1
EN_QUALSTEP    = 2
EN_PATTERNSTEP = 3
EN_PATTERNSTART= 4
EN_REPORTSTEP  = 5
EN_REPORTSTART = 6
EN_RULESTEP    = 7
EN_STATISTIC   = 8
EN_PERIODS     = 9
EN_STARTTIME   = 10  # Added TNT 10/2/2009 

EN_NODECOUNT   = 0   # Component counts 
EN_TANKCOUNT   = 1
EN_LINKCOUNT   = 2
EN_PATCOUNT    = 3
EN_CURVECOUNT  = 4
EN_CONTROLCOUNT= 5

EN_JUNCTION    = 0    # Node types 
EN_RESERVOIR   = 1
EN_TANK        = 2

EN_CVPIPE      = 0    # Link types. 
EN_PIPE        = 1    # See LinkType in TYPES.H 
EN_PUMP        = 2
EN_PRV         = 3
EN_PSV         = 4
EN_PBV         = 5
EN_FCV         = 6
EN_TCV         = 7
EN_GPV         = 8

EN_NONE        = 0    # Quality analysis types. 
EN_CHEM        = 1    # See QualType in TYPES.H 
EN_AGE         = 2
EN_TRACE       = 3

EN_CONCEN      = 0    # Source quality types.      
EN_MASS        = 1    # See SourceType in TYPES.H. 
EN_SETPOINT    = 2
EN_FLOWPACED   = 3

EN_CFS         = 0    # Flow units types.   
EN_GPM         = 1    # See FlowUnitsType   
EN_MGD         = 2    # in TYPES.H.         
EN_IMGD        = 3
EN_AFD         = 4
EN_LPS         = 5
EN_LPM         = 6
EN_MLD         = 7
EN_CMH         = 8
EN_CMD         = 9

EN_TRIALS      = 0   # Misc. options 
EN_ACCURACY    = 1
EN_TOLERANCE   = 2
EN_EMITEXPON   = 3
EN_DEMANDMULT  = 4

EN_LOWLEVEL    = 0   # Control types.  
EN_HILEVEL     = 1   # See ControlType 
EN_TIMER       = 2   # in TYPES.H.     
EN_TIMEOFDAY   = 3

EN_AVERAGE     = 1   # Time statistic types.    
EN_MINIMUM     = 2   # See TstatType in TYPES.H 
EN_MAXIMUM     = 3
EN_RANGE       = 4

EN_MIX1        = 0   # Tank mixing models 
EN_MIX2        = 1
EN_FIFO        = 2
EN_LIFO        = 3

EN_NOSAVE      = 0   # Save-results-to-file flag 
EN_SAVE        = 1

EN_INITFLOW    = 10  # Re-initialize flows flag  

