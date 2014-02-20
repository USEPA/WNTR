def read_network_data(file_name):
    # Open file, return property dictonary
    fid = open(file_name, 'r')
    propmap = fid.read()
    fid.close()
    propmap = propmap.splitlines()
    prop = list()
    data = list()
    for i in range(len(propmap)):
        temp = propmap[i].split(' ')
        prop.append(temp[0]) 
        data.append(float(temp[1])) 
    
    return dict(zip(prop, data))