import re
import numpy as np
import math
def RADec_to_Gal(RADec):

    return "this doesnt work yet "+str(RADec)

def split_coords(coord):
    delim=coord[2]
    RADEC_coords=re.split('\t',coord)
    
    RA_coords=re.split(delim,RADEC_coords[0])
    DEC_coords=re.split(delim,RADEC_coords[1])
    hours=RA_coords[0]
    mins=RA_coords[1]
    sec=RA_coords[2]
    deg=DEC_coords[0]
    amin=DEC_coords[1]
    asec=DEC_coords[2]

    return hours,mins,sec,deg,amin,asec

def Deg_to_RADec(degPos):

    degParts=re.split('\t',degPos)
    raDeg=float(degParts[0])
    decDeg=float(degParts[1])

    raRem,raHours=math.modf(raDeg/15.0)
    raRem2,raMin=math.modf(raRem*60.0)
    raSec=raRem2*60.0

    decRem,decHours=math.modf(decDeg)
    
    if decHours<0.0:
        sign=-1.0
    else:
        sign=1.0

    decRem2,decMin=math.modf(sign*decRem*60.0)
    decSec=decRem2*60.0
    
    return str(int(raHours))+" "+str(int(raMin))+" "+str(raSec)+"\t"+str(int(decHours))+" "+str(int(decMin))+" "+str(decSec)

def Deg_to_RADecCASA(degPos):

    degParts=re.split('\t',degPos)
    raDeg=float(degParts[0])
    decDeg=float(degParts[1])

    
    raRem,raHours=math.modf(raDeg/15.0)
    raRem2,raMin=math.modf(raRem*60.0)
    raSec=raRem2*60.0

    if raSec<10.0:
        raSec='0'+str(np.around(raSec, decimals=5))
    else:
        raSec=str(np.around(raSec, decimals=5))

    decRem,decHours=math.modf(decDeg)
    
    if decHours<0.0:
        sign=-1.0
    else:
        sign=1.0

    decRem2,decMin=math.modf(sign*decRem*60.0)
    decSec=decRem2*60.0
    if decSec<10.0:
        decSec='0'+str(np.around(decSec, decimals=4))
    else:
        decSec=str(np.around(decSec, decimals=4))

    #print str(int(raHours)).zfill(2)+":"+str(int(raMin)).zfill(2)+":"+str(raSec)+", "+str(int(decHours)).zfill(3)+"."+str(int(decMin)).zfill(2)+"."+str(np.around(decSec, decimals=4)).zfill(7)

    return str(int(raHours)).zfill(2)+":"+str(int(raMin)).zfill(2)+":"+raSec+", "+str(int(decHours)).zfill(3)+"."+str(int(decMin)).zfill(2)+"."+decSec
    
    
def RADec_to_Deg(RADec):

    hours,mins,sec,deg,amin,asec=split_coords(RADec)
    hours=float(hours)
    mins=float(mins)
    sec=float(sec)
    deg=float(deg)
    amin=float(amin)
    asec=float(asec)
    
    RA_in_Deg=(hours+(mins/60.0)+(sec/3600.0))*15.0

    if deg<0:
        Dec_in_Deg=deg-(amin/60)-(asec/3600)
    else:
        Dec_in_Deg=deg+(amin/60)+(asec/3600)

    Deg=str(RA_in_Deg)+" "+str(Dec_in_Deg)
    
    return Deg

def calc_offset(source1,source2):
    sou1_h,sou1_m,sou1_s,sou1_d,sou1_am,sou1_as=source1
    sou2_h,sou2_m,sou2_s,sou2_d,sou2_am,sou2_as=source2
    
    
    sou1_RA=(float(sou1_h)+(float(sou1_m)/60.0)+(float(sou1_s)/3600.0))*15.0
    sou2_RA=(float(sou2_h)+(float(sou2_m)/60.0)+(float(sou2_s)/3600.0))*15.0

    if float(sou1_d)<0:
        sou1_DEC=(float(sou1_d)-(float(sou1_am)/60.0)-(float(sou1_as)/3600.0))
    else:
        sou1_DEC=(float(sou1_d)+(float(sou1_am)/60.0)+(float(sou1_as)/3600.0))

    if float(sou2_d)<0:
        sou2_DEC=(float(sou2_d)-(float(sou2_am)/60.0)-(float(sou2_as)/3600.0))
    else:
        sou2_DEC=(float(sou2_d)+(float(sou2_am)/60.0)+(float(sou2_as)/3600.0))

    delta_RA=(sou1_RA-sou2_RA)*np.cos(sou2_DEC/57.29)*3600
    delta_DEC=(sou1_DEC-sou2_DEC)*3600

    absol_OFFSET=np.sqrt((delta_RA**2.0)+(delta_DEC**2.0))
    
    return delta_RA, delta_DEC, absol_OFFSET

def getBnut(nu,temp):
    #returns value of planck equation at given freq and temp
    left=(2.0*h*nu**3.0)/(c**2.0)
    right=1.0/(np.expm1((h*nu)/(k*temp)))

    Bnut=left*right

    return Bnut #in SI units needs converting to Jy in code proper


