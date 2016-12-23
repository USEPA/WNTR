unit epanet2;

{ Declarations of imported procedures from the EPANET PROGRAMMERs TOOLKIT }
{ (EPANET2.DLL) }

{Last updated on 2/25/08}

interface

const

{ These are codes used by the DLL functions }
 EN_ELEVATION  = 0;    { Node parameters }
 EN_BASEDEMAND = 1;
 EN_PATTERN    = 2;
 EN_EMITTER    = 3;
 EN_INITQUAL   = 4;
 EN_SOURCEQUAL = 5;
 EN_SOURCEPAT  = 6;
 EN_SOURCETYPE = 7;
 EN_TANKLEVEL  = 8;
 EN_DEMAND     = 9;
 EN_HEAD       = 10;
 EN_PRESSURE   = 11;
 EN_QUALITY    = 12;
 EN_SOURCEMASS = 13;
 EN_INITVOLUME = 14;
 EN_MIXMODEL   = 15;
 EN_MIXZONEVOL = 16;

 EN_TANKDIAM    = 17;
 EN_MINVOLUME   = 18;
 EN_VOLCURVE    = 19;
 EN_MINLEVEL    = 20;
 EN_MAXLEVEL    = 21;
 EN_MIXFRACTION = 22;
 EN_TANK_KBULK  = 23;

 EN_DIAMETER    = 0;    { Link parameters }
 EN_LENGTH      = 1;
 EN_ROUGHNESS   = 2;
 EN_MINORLOSS   = 3;
 EN_INITSTATUS  = 4;
 EN_INITSETTING = 5;
 EN_KBULK       = 6;
 EN_KWALL       = 7;
 EN_FLOW        = 8;
 EN_VELOCITY    = 9;
 EN_HEADLOSS    = 10;
 EN_STATUS      = 11;
 EN_SETTING     = 12;
 EN_ENERGY      = 13;

 EN_DURATION     = 0;  { Time parameters }
 EN_HYDSTEP      = 1;
 EN_QUALSTEP     = 2;
 EN_PATTERNSTEP  = 3;
 EN_PATTERNSTART = 4;
 EN_REPORTSTEP   = 5;
 EN_REPORTSTART  = 6;
 EN_RULESTEP     = 7;
 EN_STATISTIC    = 8;
 EN_PERIODS      = 9;

 EN_NODECOUNT    = 0; { Component counts }
 EN_TANKCOUNT    = 1;
 EN_LINKCOUNT    = 2;
 EN_PATCOUNT     = 3;
 EN_CURVECOUNT   = 4;
 EN_CONTROLCOUNT = 5;

 EN_JUNCTION   = 0;   { Node types }
 EN_RESERVOIR  = 1;
 EN_TANK       = 2;

 EN_CVPIPE     = 0;   { Link types }
 EN_PIPE       = 1;
 EN_PUMP       = 2;
 EN_PRV        = 3;
 EN_PSV        = 4;
 EN_PBV        = 5;
 EN_FCV        = 6;
 EN_TCV        = 7;
 EN_GPV        = 8;

 EN_NONE       = 0;   { Quality analysis types }
 EN_CHEM       = 1;
 EN_AGE        = 2;
 EN_TRACE      = 3;

 EN_CONCEN     = 0;   { Source quality types }
 EN_MASS       = 1;
 EN_SETPOINT   = 2;
 EN_FLOWPACED  = 3;

 EN_CFS        = 0;   { Flow units types }
 EN_GPM        = 1;
 EN_MGD        = 2;
 EN_IMGD       = 3;
 EN_AFD        = 4;
 EN_LPS        = 5;
 EN_LPM        = 6;
 EN_MLD        = 7;
 EN_CMH        = 8;
 EN_CMD        = 9;

 EN_TRIALS     = 0;   { Option types }
 EN_ACCURACY   = 1;
 EN_TOLERANCE  = 2;
 EN_EMITEXPON  = 3;
 EN_DEMANDMULT = 4;

 EN_LOWLEVEL   = 0;   { Control types }
 EN_HILEVEL    = 1;
 EN_TIMER      = 2;
 EN_TIMEOFDAY  = 3;

 EN_AVERAGE    = 1;   { Time statistic types }
 EN_MINIMUM    = 2; 
 EN_MAXIMUM    = 3;
 EN_RANGE      = 4;

 EN_MIX1       = 0;   { Tank mixing models }
 EN_MIX2       = 1;
 EN_FIFO       = 2;
 EN_LIFO       = 3;

 EN_NOSAVE     = 0;   { Save-results-to-file flag }
 EN_SAVE       = 1;
 EN_INITFLOW   = 10;  { Re-initialize flow flag }

 function  ENepanet(F1: Pchar; F2: Pchar; F3: Pchar; F4: Pointer): Integer; stdcall;
 function  ENopen(F1: Pchar; F2: Pchar; F3: Pchar): Integer; stdcall;
 function  ENsaveinpfile(F: Pchar): Integer; stdcall;
 function  ENclose: Integer; stdcall;

 function  ENsolveH: Integer; stdcall;
 function  ENsaveH: Integer; stdcall;
 function  ENopenH: Integer; stdcall;
 function  ENinitH(SaveFlag: Integer): Integer; stdcall;
 function  ENrunH(var T: LongInt): Integer; stdcall;
 function  ENnextH(var Tstep: LongInt): Integer; stdcall;
 function  ENcloseH: Integer; stdcall;
 function  ENsavehydfile(F: Pchar): Integer; stdcall;
 function  ENusehydfile(F: Pchar): Integer; stdcall;

 function  ENsolveQ: Integer; stdcall;
 function  ENopenQ: Integer; stdcall;
 function  ENinitQ(SaveFlag: Integer): Integer; stdcall;
 function  ENrunQ(var T: LongInt): Integer; stdcall;
 function  ENnextQ(var Tstep: LongInt): Integer; stdcall;
 function  ENstepQ(var Tleft: LongInt): Integer; stdcall;
 function  ENcloseQ: Integer; stdcall;

 function  ENwriteline(S: Pchar): Integer; stdcall;
 function  ENreport: Integer; stdcall;
 function  ENresetreport: Integer; stdcall;
 function  ENsetreport(S: Pchar): Integer; stdcall;

 function  ENgetcontrol(Cindex: Integer; var Ctype: Integer; var Lindex: Integer; var Setting: Single;
                        var Nindex: Integer; var Level: Single): Integer; stdcall;
 function  ENgetcount(Code: Integer; var Count: Integer): Integer; stdcall;
 function  ENgetoption(Code: Integer; var Value: Single): Integer; stdcall;
 function  ENgettimeparam(Code: Integer; var Value: LongInt): Integer; stdcall;
 function  ENgetflowunits(var Code: Integer): Integer; stdcall;
 function  ENgetpatternindex(ID: Pchar; var Index: Integer): Integer; stdcall;
 function  ENgetpatternid(Index: Integer; ID: Pchar): Integer; stdcall;
 function  ENgetpatternlen(Index: Integer; var Len: Integer): Integer; stdcall;
 function  ENgetpatternvalue(Index: Integer; Period: Integer; var Value: Single): Integer; stdcall;
 function  ENgetqualtype(var QualCode: Integer; var TraceNode: Integer): Integer; stdcall;
 function  ENgeterror(ErrCode: Integer; ErrMsg: Pchar; N: Integer): Integer; stdcall;

 function  ENgetnodeindex(ID: Pchar; var Index: Integer): Integer; stdcall;
 function  ENgetnodeid(Index: Integer; ID: Pchar): Integer; stdcall;
 function  ENgetnodetype(Index: Integer; var Code: Integer): Integer; stdcall;
 function  ENgetnodevalue(Index: Integer; Code: Integer; var Value: Single): Integer; stdcall;

 function  ENgetlinkindex(ID: Pchar; var Index: Integer): Integer; stdcall;
 function  ENgetlinkid(Index: Integer; ID: Pchar): Integer; stdcall;
 function  ENgetlinktype(Index: Integer; var Code: Integer): Integer; stdcall;
 function  ENgetlinknodes(Index: Integer; var Node1: Integer; var Node2: Integer): Integer; stdcall;
 function  ENgetlinkvalue(Index: Integer; Code: Integer; var Value: Single): Integer; stdcall;

 function  ENgetversion(var Value: Integer): Integer; stdcall;

 function  ENsetcontrol(Cindex: Integer; Ctype: Integer; Lindex: Integer; Setting: Single;
                        Nindex: Integer; Level: Single): Integer; stdcall;
 function  ENsetnodevalue(Index: Integer; Code: Integer; Value: Single): Integer; stdcall;
 function  ENsetlinkvalue(Index: Integer; Code: Integer; Value: Single): Integer; stdcall;
 function  ENaddpattern(ID: Pchar): Integer; stdcall;
 function  ENsetpattern(Index: Integer; F: array of Single; N: Integer): Integer; stdcall;
 function  ENsetpatternvalue(Index: Integer; Period: Integer; Value: Single): Integer; stdcall;
 function  ENsettimeparam(Code: Integer; Value: LongInt): Integer; stdcall;
 function  ENsetoption(Code: Integer; Value: Single): Integer; stdcall;
 function  ENsetstatusreport(Code: Integer): Integer; stdcall;
 function  ENsetqualtype(QualCode: Integer; ChemName: Pchar; ChemUnits: Pchar; TraceNodeID: Pchar): Integer; stdcall;

implementation

 function  ENepanet;          external 'EPANET2.DLL';
 function  ENopen;            external 'EPANET2.DLL';
 function  ENsaveinpfile;     external 'EPANET2.DLL';
 function  ENclose;           external 'EPANET2.DLL';

 function  ENsolveH;          external 'EPANET2.DLL';
 function  ENsaveH;           external 'EPANET2.DLL';
 function  ENopenH;           external 'EPANET2.DLL';
 function  ENinitH;           external 'EPANET2.DLL';
 function  ENrunH;            external 'EPANET2.DLL';
 function  ENnextH;           external 'EPANET2.DLL';
 function  ENcloseH;          external 'EPANET2.DLL';
 function  ENsavehydfile;     external 'EPANET2.DLL';
 function  ENusehydfile;      external 'EPANET2.DLL';

 function  ENsolveQ;          external 'EPANET2.DLL';
 function  ENopenQ;           external 'EPANET2.DLL';
 function  ENinitQ;           external 'EPANET2.DLL';
 function  ENrunQ;            external 'EPANET2.DLL';
 function  ENnextQ;           external 'EPANET2.DLL';
 function  ENstepQ;           external 'EPANET2.DLL';
 function  ENcloseQ;          external 'EPANET2.DLL';

 function  ENwriteline;       external 'EPANET2.DLL';
 function  ENreport;          external 'EPANET2.DLL';
 function  ENresetreport;     external 'EPANET2.DLL';
 function  ENsetreport;       external 'EPANET2.DLL';

 function  ENgetcontrol;      external 'EPANET2.DLL';
 function  ENgetcount;        external 'EPANET2.DLL';
 function  ENgetoption;       external 'EPANET2.DLL';
 function  ENgettimeparam;    external 'EPANET2.DLL';
 function  ENgetflowunits;    external 'EPANET2.DLL';
 function  ENgetpatternindex; external 'EPANET2.DLL';
 function  ENgetpatternid;    external 'EPANET2.DLL';
 function  ENgetpatternlen;   external 'EPANET2.DLL';
 function  ENgetpatternvalue; external 'EPANET2.DLL';
 function  ENgetqualtype;     external 'EPANET2.DLL';
 function  ENgeterror;        external 'EPANET2.DLL';

 function  ENgetnodeindex;    external 'EPANET2.DLL';
 function  ENgetnodeid;       external 'EPANET2.DLL';
 function  ENgetnodetype;     external 'EPANET2.DLL';
 function  ENgetnodevalue;    external 'EPANET2.DLL';

 function  ENgetlinkindex;    external 'EPANET2.DLL';
 function  ENgetlinkid;       external 'EPANET2.DLL';
 function  ENgetlinktype;     external 'EPANET2.DLL';
 function  ENgetlinknodes;    external 'EPANET2.DLL';
 function  ENgetlinkvalue;    external 'EPANET2.DLL';

 function  ENgetversion;      external 'EPANET2.DLL';

 function  ENsetcontrol;      external 'EPANET2.DLL';
 function  ENsetnodevalue;    external 'EPANET2.DLL';
 function  ENsetlinkvalue;    external 'EPANET2.DLL';
 function  ENaddpattern;      external 'EPANET2.DLL';
 function  ENsetpattern;      external 'EPANET2.DLL';
 function  ENsetpatternvalue; external 'EPANET2.DLL';
 function  ENsettimeparam;    external 'EPANET2.DLL';
 function  ENsetoption;       external 'EPANET2.DLL';
 function  ENsetstatusreport; external 'EPANET2.DLL';
 function  ENsetqualtype;     external 'EPANET2.DLL';

end.
