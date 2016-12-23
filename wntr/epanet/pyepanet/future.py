"""
WNTR python extensions for the EPANET Programmers Toolkit
"""
import string

def ENgetcoordinates(inp_file_name=None):
    """
    Returns network coordinates
    
    Parameters
    ----------
    inp_file_name : string
    """
    f = open(inp_file_name)
    sInpText = f.read()
    dataXY = []									# this will store our results
    dataXY2 = []
    Lines = sInpText.splitlines()				# make a string array from all the text in the inp file
    sCOORDINATES = "[COORDINATES]"				# this is our target search string
    sVERTICES    = "[VERTICES]"
    bParseXY = False							# this is a flag that says we have reached the target area in the inp file
    bParseXY2 = False
    for line in Lines:							# cycle through each line in the file
        sline = line.strip(string.whitespace)	# strip all white space from the start and end of this line
        index = sline.find(";")					# search for the comment descriptor
        if index == 0: continue					# if the comment descriptor is the first character move to next line
        index = sline.find("[")					# each section heading in the inp file starts with an open bracket
        if index == 0 and bParseXY: 			# if we found a new section AND we already started parsing coordinates...
            bParseXY = False					# stop parsing coordinates
        if index == 0 and bParseXY2:			# if we found a new section AND we already started parsing vertices... 
            bParseXY2 = False					# stop parsing vertices
        if bParseXY:							# if we are in the coordinates section...
            arr = parseInpFileLine(line)	# get an array of items on that line
            if len(arr) > 0:					# if the array contains at least one element...
                dataXY.append(arr)				# then add it to the dataXY results array
        if bParseXY2:							# if we are in the vertices section...
            arr = parseInpFileLine(line)	# get an array of items on that line
            if len(arr) > 0:					# if the array contains at least one element...
                dataXY2.append(arr)				# then add it to the dataXY2 results array
        if len(sline) == 0:	continue			# if this line only contains whitespace... then move on to the next line
        index = sline.find(sCOORDINATES)		# is the coordinates header on this line?
        if index > -1:
            bParseXY = True						# if we found the coordinates heading, begin parsing x's and y's at the next line
            bParseXY2 = False
        index = sline.find(sVERTICES)			# is the coordinates header on this line?
        if index > -1:
            bParseXY2 = True					# if we found the vertices heading, begin parsing x's and y's at the next line
            bParseXY = False
    
    pos = {d[0]: (float(d[1]), float(d[2])) for d in dataXY}
    
    return pos					# once we have reached the end of this section... return the results 

def parseInpFileLine(line=""):
    """
    Parse inp file, line by line
    """
    line = line.strip(string.whitespace)		# remove leading and trailing whitespace
    line = line.expandtabs(1)					# change internal tabs into spaces
    arr = line.split(";")						# remove any comments
    arr = arr[0].split()						# create a string array with any whitespace as the delimiter
    
    return arr[0:3]
    