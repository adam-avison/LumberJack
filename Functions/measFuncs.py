import numpy as np
import os
import sys
import re
from taskinit import *
import matplotlib.pyplot as plt
from astroFUNCS import *
# from task_imstat import imstat
from imstat_cli import imstat_cli as imstat
from imval_cli import imval_cli as imval

#--- Import analysis utils
auPath = '<PATH TO ANALYSIS UTILS>'#you can download AnalysisUtils from https://casaguides.nrao.edu/index.php/Analysis_Utilities 
sys.path.insert(0,auPath)
import analysisUtils as aU


#--- INITIALISE SOME CASA TOOL
ia = iatool()
msmd = msmdtool()

def getTsys(myMS,SPW):
    """
    #FUNCTION TO RETURN MEDIAM TSYS IN A GIVEN MS & SPW

    """
    wantTsys = np.array([])

    msmd.open(myMS) #--- Open the measurement set
    baseband  = msmd.baseband(int(SPW))
    msmd.close() #--- close the measurement set
    msmd.done()  #--- kill the msmd tool.
    baseband_str = 'BB_'+str(baseband) #--- get SPW baseband into basebandName format

    #--- OPEN DATA TABLE AND GET TSYS & FREQ RANGES VALUES ---#
    tb.open(myMS+'/ASDM_CALATMOSPHERE', nomodify=True)
    tsys = tb.getcol('tSys')                #--- ALL Tsys vales
    BB = tb.getcol('basebandName')          #--- Baseband Name
    tb.close()

    wantTsys = np.append(wantTsys,tsys[0][np.where(BB==baseband_str)[0]]) #--- XX corr Tsys vals
    wantTsys = np.append(wantTsys,tsys[1][np.where(BB==baseband_str)[0]]) #--- YY corr Tsys vals

    medianTsys = np.median(wantTsys)

    return medianTsys


def getMean(xdata):
        #--- get mean values from imval for spectra---#
        meanArr=[]
        tmpVal=0.0
        for z in range(xdata.shape[2]):
                for x in range(xdata.shape[0]):
                        for y in range(xdata.shape[1]):
                                    #print x, y, z

                                    #print xdata[x][y][z]
                                    tmpVal+=(xdata[x][y][z])
                meanArr.append(tmpVal/float(xdata.shape[0]+xdata.shape[1]))
                tmpVal=0.0
        return np.array(meanArr)

def readListobs(listFile):
          #--- reads the SPW info from the raw MS listobs ---#
          listing=open(listFile).readlines()
          parse=False

          spwInfo=[]
          for line in listing:
                    if line.startswith("  SpwID  Name"):
                              parse=True
                    elif line.startswith("Sources:"):
                              parse=False

                    if parse:
                            spwInfo.append(re.split('\s+',line))

          return spwInfo

def getTsysValue(tables,listobsFile,wantSPW,msname):
          """ DEPRECATED"""
          #--- Return the average Tsys value for the spectral window we are looking at --#
          tab_count=0
          TsysAverage=0
          for table in tables:
                    tb.open(table)

                    spwsIDs=tb.getcol('SPECTRAL_WINDOW_ID')

                    #--- Get the raw MS listobs data related to SPWs        ---#
                    #--- This contains the Tsys and WVR SPWs as well as the ---#
                    #--- Science ones... we want to find the Tsys SPW which ---#
                    #--- matches our Science SPW                            ---#
                    spwData=readListobs(listobsFile)

                    sciFreqs=aU.getScienceFrequencies(msname)
                    wantSciFreq=(sciFreqs[wantSPW])/1.0e6
                    #--- Find which Tsys SPW has minimum difference from sci spw ---#
                    freqDiff=[]
                    for spwz in np.unique(np.asarray(spwsIDs)):
                              for msSPW in spwData:
                                        if msSPW[1] == str(spwz):
                                                  freqDiff.append(np.sqrt((float(msSPW[5])-wantSciFreq)**2.0))

                    #--- this is the Tsys SPW we want associated with our Sci SPW ---#
                    wantTsysSPW=np.unique(np.asarray(spwsIDs))[np.argmin(freqDiff)]
                    #--- These are the rows of Tsys data associated with our Sci SPW ---#
                    wantTsysRows=np.where(spwsIDs==wantTsysSPW)[0]

                    #--- get only Tsys values that are in our wanted Tsys SPW ---#
                    tsysVals=tb.getcol('FPARAM',startrow=wantTsysRows[0],nrow=len(wantTsysRows))
                    tb.close()
                    print np.median(tsysVals[0][7:120][:]),np.median(tsysVals[1][7:120][:])

                    #--- Take average Tsys from non-edge channels in xx and yy corr ---#
                    thisTsysAverage=np.average([np.median(tsysVals[0][7:120][:]),np.median(tsysVals[1][7:120][:])])


                    tab_count+=1

                    TsysAverage+=thisTsysAverage
                    print "\n >>> Average Tsys = "+str(TsysAverage)+" K"

          TsysAverage=TsysAverage/float(tab_count)

          return TsysAverage


def measSetInfo(msname,wantSPW,myfield=''):

    listobsFile=msname+'.listobs'
    listRead=open(listobsFile,'r')
    linecount=0 #--- Counter to figureout where to grab antenna info from.
    for listLine in listRead:
        if re.match('Data records:',listLine):
            dataRecs=listLine.strip()
        if re.match('\s+Observed from',listLine):
            obsFrom=listLine.strip()
        if re.match('Antennas:',listLine):
            numAnts=float((re.split('\:',listLine.strip())[1]).strip())
            antDataStartLine=linecount+3
        linecount+=1

    #--- Load all antenna data

    antData=np.loadtxt(listobsFile,skiprows=antDataStartLine,dtype={'names':('ID','Name','Station','Diam','DiamU','Long','Lat','EastOff','NorthOff','Elev','antX','antY','antZ'),'formats':('i4','S6','S6','S6','S4','S12','S12','f8','f8','f8','f8','f8','f8')})

    #--- convert dish diameters to m

    outDiamM=[]#--output diameter after conversion will me in meter
    for x in range(len(antData['Diam'])):
        inpDiam=qa.quantity(str(antData['Diam'][x])+antData['DiamU'][x])

        outDiam=qa.convert(inpDiam,'m')
        outDiamM.append(outDiam['value'])

    #--- Use msmd tools to get spw numbers and bandwidths etc

    msmd.open(msname)
    dataBWs=msmd.bandwidths() #--- Get bandwidths
    chan_res = msmd.chanwidths(wantSPW,unit="Hz")
    numChan = msmd.nchan(wantSPW)
    spws=msmd.almaspws(sqld=True, complement=True) #--- Get spectral window numbers

    #--- Get all science target fields
    target_fields=msmd.fieldsforintent("OBSERVE_TARGET#ON_SOURCE")
    allFields=msmd.fieldnames()
    #--- If no field specified get the first target source and use that
    if myfield=='':
         myfield=allFields[target_fields[0]]

         print "\n >>> You didn't specify a field so I am assuming the first target field\n >>> in the MS, which is "+myfield

    #--- Check is all the target names match... i.e. is the target field mosaiced
    scan_numbers=[]
    for field in allFields:
	    if field[:-2] == myfield[:-2]:
		    theseScan=msmd.scansforfield(field)
		    print field, theseScan
		    #for scans in
		    #     scan_numbers.append(scans)



    mySourceIdx=allFields.index(myfield)
    scan_numbers=np.asarray(theseScan)
    #--- Get timeOn Source
    obsTime=0
    obsID=0

    mydict = aU.timeOnSource(msname,verbose=False) #in minutes

    obsTime=mydict['minutes_on_science']

    msmd.close()
    msmd.done()

    return numAnts, outDiamM[0], dataBWs[wantSPW], (obsTime*60.0)/float(len(target_fields)), np.asarray(target_fields), chan_res[wantSPW], mySourceIdx, numChan

################################################################################

def getSourcePos(targImage,specPath):
        #--- Function to get useful information about the image file, and extract the spectrum at the position of the peak pixel.
        #--- Saves spectrum to textfile and returns position of peak

        ia.done()
        #--- OPEN IMAGE
        ia.open(targImage)

        #--- Source names
        sourName=re.split('/',targImage)[-1]
        sourName='/'+sourName
        #--- GET AXIS INFORMATION
        inp_csys=ia.coordsys()
        freqAxis=inp_csys.findcoordinate(type='spectral')['pixel'][0]#--- determine which axis is the freq axis
        freqRefPix=inp_csys.referencepixel()['numeric'][freqAxis]#--- frequency axis reference pixel
        freqRefVal=inp_csys.referencevalue()['numeric'][freqAxis]#--- frequency axis reference value (in Hz)
        freqIncr=inp_csys.increment()['numeric'][freqAxis]#--- frequency increment
        freqExtent=ia.shape()[freqAxis]#--- get the length of the freq axis
        fPix=np.arange(0,freqExtent,1)
        freqVals=freqRefVal+((fPix-freqRefPix)*freqIncr)

        #--- SHAPE OF IMAGE IN RA/DEC
        RAExtent=ia.shape()[0]
        DecExtent=ia.shape()[1]

        raAxis=inp_csys.findcoordinate(type='direction')['pixel'][0]#--- determine which axis is the RA axis
        decAxis=inp_csys.findcoordinate(type='direction')['pixel'][1]#--- determine which axis is the dec axis
        raIncr=inp_csys.increment()['numeric'][raAxis]
        decIncr=inp_csys.increment()['numeric'][decAxis]

        #--- GET BEAM INFORMATION
        beamDict=ia.restoringbeam()
        try:
                bMaj=str(beamDict['major']['value'])+str(beamDict['major']['unit'])#--- get the synthesised beam major axis properties
                bMin=str(beamDict['minor']['value'])+str(beamDict['minor']['unit'])#--- get the synthesised beam minor axis properties
                bPA=str(beamDict['positionangle']['value'])+str(beamDict['positionangle']['unit'])#--- get the synthesised beam position angle properties

        except KeyError:
                beamDictL=beamDict['beams']['*0']['*0']
                bMaj=str(beamDictL['major']['value'])+str(beamDictL['major']['unit'])#--- get the synthesised beam major axis properties
                bMin=str(beamDictL['minor']['value'])+str(beamDictL['minor']['unit'])#--- get the synthesised beam minor axis properties
                bPA=str(beamDictL['positionangle']['value'])+str(beamDictL['positionangle']['unit'])#--- get the synthesised beam position angle properties


        #--- FIND PEAK POSITION (as in the brightest pixel in the whole cube)
        #--- We will then extract a spectrum at that position.
        warning=""
        maxFitDict=ia.maxfit()

        mF_Dec=maxFitDict['component0']['shape']['direction']['m1']['value']#---Dec position of peak in rad
        mF_RA=maxFitDict['component0']['shape']['direction']['m0']['value']#---RA position of peak in rad

        #--- Make sure peak position is sensible (if is is >100 pixels from centre set position to centre)
        offsetX=np.sqrt((int(np.floor(RAExtent/2.0))-int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][0])))**2.0)
        offsetY=np.sqrt((int(np.floor(DecExtent/2.0))-int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][1])))**2.0)
        if (offsetX > 100.0) or (offsetY > 100.0):
                print "================================================================================================"
                print "\n\n Possible non-detection for "+sourName+" setting spectra pixel to centre pixel "+str(int(np.floor(RAExtent/2.0)))+","+(int(np.floor(DecExtent/2.0)))+" \n\n"
                print "================================================================================================"

                posPixStrHigh=str(int(np.floor(RAExtent/2.0)))+","+(int(np.floor(DecExtent/2.0)))#--- Pixel coords cos the work better
                posPixStrLow=str(int(np.floor(RAExtent/2.0))+1)+","+(int(np.floor(DecExtent/2.0))+1)

                warning="#possible non-detection!!!\n"

        else:
                warning=""
                posPixStrHigh=str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][0])))+'pix, '+str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][1])))+'pix'#--- Pixel coords cos the work better
                posPixStrLow=str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][0])))+'pix, '+str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][1])))+'pix'

                posStr=str(360.0+np.degrees(mF_RA))+"\t"+str(np.degrees(mF_Dec))#---conversion from rad to decimal degrees of peak position
                posStrLow=str(360.0+np.degrees(mF_RA-(raIncr/1.5)))+"\t"+str(np.degrees(mF_Dec-(decIncr/1.5)))#---conversion from rad to decimal degrees -half pixel
                posStrHigh=str(360.0+np.degrees(mF_RA+(raIncr/1.5)))+"\t"+str(np.degrees(mF_Dec+(decIncr/1.5)))#---conversion from rad to decimal degrees +half pixel

                #--- CONVERT TO RA AND DEC in CASA FORMAT
                raDecStr=Deg_to_RADecCASA(posStr)
                raDecStrLow=Deg_to_RADecCASA(posStrLow)
                raDecStrHigh=Deg_to_RADecCASA(posStrHigh)

                #--- define some CASA regions
                ellStr="ellipse[["+raDecStr+"],["+bMaj+","+bMin+"],"+bPA+"]"
                circStr="circle[["+raDecStr+"],"+bMaj+"]"


        boxStr="box[["+posPixStrLow+"],["+posPixStrHigh+"]]"
        print boxStr, '!!!!! CHEESE !!!!!'
        #boxStr="box[[124pix, 118pix],[124pix, 118pix]]"
        #print boxStr, '!!!!! PEAK MANUAL OVERWRITE !!!!!'

        #--- CLOSE IMAGE
        ia.done()
        ia.close()

        #print PBtargImage
        #--- Get peak flux at brightest pixel position from the pbcor image.
        imstat_dict=imstat(imagename=targImage, axes=[0,1], region=boxStr, box="", chans="", stokes="", listit=True, verbose=True, mask="", stretch=False, logfile="", append=True, algorithm='classic',fence=-1, center="mean", lside=True, zscore=-1, maxiter=-1, clmethod="auto", niter=3)


        print specPath+sourName+'_spec.txt'
        np.savetxt(specPath+sourName+'_spec.txt',np.c_[freqVals,imstat_dict['sum']],header=warning+'#freq[Hz]\tpeak flux[Jy/beam]')

        imageSpecFile=specPath+sourName+'_spec.txt'

        return imageSpecFile

################################################################################

def getSourcePos2(targImage,position,specPath,sourNum, bMaj, bMin, bPA):
        #--- AS ABOVE EXCEPT EXTRACT SPECTRUM AT A GIVEN POSITION
        #--- Function to get useful information about the image file, and extract the spectrum at a given position.
        #--- Saves spectrum to textfile and returns position of peak

        ia.done()
        #--- OPEN IMAGE
        ia.open(targImage)

        #--- Source names
        sourName=re.split('/',targImage)[-1]
        sourName='/'+sourName
        #--- GET AXIS INFORMATION
        inp_csys=ia.coordsys()
        freqAxis=inp_csys.findcoordinate(type='spectral')['pixel'][0]#--- determine which axis is the freq axis
        freqRefPix=inp_csys.referencepixel()['numeric'][freqAxis]#--- frequency axis reference pixel
        freqRefVal=inp_csys.referencevalue()['numeric'][freqAxis]#--- frequency axis reference value (in Hz)
        freqIncr=inp_csys.increment()['numeric'][freqAxis]#--- frequency increment
        freqExtent=ia.shape()[freqAxis]#--- get the length of the freq axis
        fPix=np.arange(0,freqExtent,1)
        freqVals=freqRefVal+((fPix-freqRefPix)*freqIncr)

        #--- SHAPE OF IMAGE IN RA/DEC
        RAExtent=ia.shape()[0]
        DecExtent=ia.shape()[1]

        raAxis=inp_csys.findcoordinate(type='direction')['pixel'][0]#--- determine which axis is the RA axis
        decAxis=inp_csys.findcoordinate(type='direction')['pixel'][1]#--- determine which axis is the dec axis
        raIncr=inp_csys.increment()['numeric'][raAxis]
        decIncr=inp_csys.increment()['numeric'][decAxis]

        #--- BEAM INFORMATION FROM SOURCE IS INCLUDED IN FUNC DEF



        #--- CONVERT RA DEC TO RADIANS
        warning=""
        """
        Deg=RADec_to_Deg(position)

        raRad=float(re.split('\s+',Deg)[0])/(180.0/np.pi)
        decRad=float(re.split('\s+',Deg)[1])/(180.0/np.pi)

        mF_Dec=decRad#maxFitDict['component0']['shape']['direction']['m1']['value']#---Dec position of peak in rad
        mF_RA=raRad#maxFitDict['component0']['shape']['direction']['m0']['value']#---RA position of peak in rad

        posPixStrHigh=str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][0])))+'pix, '+str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][1])))+'pix'#--- Pixel coords cos the work better
        posPixStrLow=str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][0])))+'pix, '+str(int(np.ceil(inp_csys.topixel([mF_RA,mF_Dec])['numeric'][1])))+'pix'

        posStr=str(360.0+np.degrees(mF_RA))+"\t"+str(np.degrees(mF_Dec))#---conversion from rad to decimal degrees of peak position
        posStrLow=str(360.0+np.degrees(mF_RA-(raIncr/1.5)))+"\t"+str(np.degrees(mF_Dec-(decIncr/1.5)))#---conversion from rad to decimal degrees -half pixel
        posStrHigh=str(360.0+np.degrees(mF_RA+(raIncr/1.5)))+"\t"+str(np.degrees(mF_Dec+(decIncr/1.5)))#---conversion from rad to decimal degrees +half pixel

        #--- CONVERT TO RA AND DEC in CASA FORMAT
        raDecStr=Deg_to_RADecCASA(posStr)
        raDecStrLow=Deg_to_RADecCASA(posStrLow)
        raDecStrHigh=Deg_to_RADecCASA(posStrHigh)"""

        #--- define some CASA regions
        positionRA=re.split('\t',position)[0]
        positionDec=re.sub(':','.',re.split('\t',position)[1])
        ellStr="ellipse[["+positionRA+","+positionDec+"],["+bMaj+","+bMin+"],"+bPA+"]"
        print ellStr
        circStr="circle[["+positionRA+","+positionDec+"],"+bMaj+"]"

        """
        boxStr="box[["+posPixStrLow+"],["+posPixStrHigh+"]]"
        print '\n!!! AAAAAAAAA!!!\n'
        print boxStr
        print '\n!!! BBBBBBBBB!!!\n'
        """

        #--- CLOSE IMAGE
        ia.done()


        #print PBtargImage
        #--- Get peak flux at brightest pixel position from the pbcor image.
        imstat_dict=imstat(imagename=targImage, axes=[0,1], region=ellStr, box="", chans="", stokes="", listit=True, verbose=True, mask="", stretch=False, logfile="", append=True, algorithm='classic',fence=-1, center="mean", lside=True, zscore=-1, maxiter=-1, clmethod="auto", niter=3)


        print specPath+sourName+'_secndOnSource_'+sourNum+'_spec.txt'
        np.savetxt(specPath+sourName+'_secndOnSource_'+sourNum+'_spec.txt',np.c_[freqVals,imstat_dict['flux']],header=warning+'#freq[Hz]\tpeak flux[Jy/beam]')

        imageSpecFile=specPath+sourName+'_secndOnSource_'+sourNum+'_spec.txt'

        return imageSpecFile
