import re
import numpy as np
import os
import matplotlib.pyplot as plt
import sys
import glob
from scipy.optimize import curve_fit
from cleanhelper import *
#-------------------#
#--- Load Extras ---#
#-------------------#
cwd=os.getcwd()
sys.path.insert(0,cwd+'/Functions/')
from loadFuncs import *
from plotFuncs import *
from calcFuncs import *
from measFuncs import*

#-------------------------#
#--- Main Body of Code ---#
#-------------------------#

""" LUMBERJACK 'LITE' VERSION

A SCRIPTED VERSION OF THE LUMBERJACK TASK
- Created by A.Avison Jan-2019

--- INPUT ----

 User will need to input the following below:
- Spectral Window Number (as paramter SPW)
- Target name (as parameter targ)
- Observation Tsys (parameter Tsys [in K] can be taken from qa/ report).
- Name of measurement set (parameter msname)
- The number of channels in your spectral window (parameter numChan, can be found in listobs)


In the current directory you will need:
- A calibrated measurement set containing your target data
- A list of sources in the field in a file named <target_name>+_SecondarySources.txt
    - The format of this file is:
    sourceX     RA[hh:mm:ss.000]    Dec[dd:mm:ss.000]   Bmaj*   Bmin*   BPA*

    *fitted 2D Gaussian major, minor axis and position angle.
- The un-tarred Functions201*.tar directory.

--- OUTPUT ---

For each SPW and source listed in *_SecondarySources.txt you will get:

- An output txt file named <target_name>_sourceNo_<#>_SPW_<SPW>_LineFreeChans.txt. This contains the line free channels at that position.

- Two PNG images:
    - <target_name>_sourceNo_<#>_SPW_<SPW>_lineFree.png which shows the spectrum and line free chans
    - <target_name>_sourceNo_<#>_SPW_<SPW>_gaussPlot.png which shows a histogram of the flux values of line free channels.

- A txt file named <target_name>_allSource_SPW_<SPW>_LineFreeChans.txt which combines the values from each source and 'chunks' them in to a CASA SPW string format. e.g. 25:1~30;33~81;84~526;544~591;594~1760;1783~1852;1856~1868;1871~1898;1901~1917

"""
#---------- LITE VERSION ---------------#
#--- USER INPUT PARAMS
Tsys=60.0  # Average Tsys taken from AQUA or qa/ directory plats
msname='../uid___A002_Xb046c2_X3b39.ms.split.cal'
StdDevFactor=1.5
SPW=2
numChan=240

targ='ngc3256'
secondaryFile=targ+'_SecondarySources.txt'

#--- 0.5) Take listobs of an MS and recover the useful information.
listobsFile=msname+'.listobs'

try:
    testList=open(listobsFile,'r')
except IOError:
    print "\n >>> Listobs failed to open, making a new one."
    listobs(msname, listfile=listobsFile)
    testList=open(listobsFile,'r')

    testList.close()

#-- 1) Look into the MS and get useful info
nAnt,antDiam,BW,tInt,sourceFields,chWid,targIdx=measSetInfo(msname,SPW,myfield=targ)
theoRMS=calcSens(nAnt,chWid,tInt,Tsys,antDiam)


print "\n >>> Assuming "+str(nAnt)+" antennas of diameter "+str(antDiam)+" and channel width of "+str(chWid)+"\n >>> observed for "+str(tInt)+" sec"
print "\n >>> The theoretical RMS in a single channel is (assuming no flagging etc) is "+str(theoRMS)+"Jy"

print sourceFields

#-- 1.5) In second version loop around detected continuum sources.
secondarySources=np.genfromtxt(secondaryFile, dtype=None, names=['souNum','secRA','secDec','secBmaj','secBmin','secPA'])

#- How many sources?

try:
    useRange = len(secondarySources['souNum'])
except TypeError:
    useRange = 1

for x in range(useRange):
    if useRange == 1:
        source_no=re.split('source',str(secondarySources['souNum']))[1]
        position=secondarySources['secRA']+'\t'+secondarySources['secDec']
        thisBmaj=str(secondarySources['secBmaj'])+'arcsec'
        thisBmin=str(secondarySources['secBmin'])+'arcsec'
        thisPA=str(secondarySources['secPA'])+'deg'
    else:
        source_no=re.split('source',secondarySources['souNum'][x])[1]
        position=secondarySources['secRA'][x]+'\t'+secondarySources['secDec'][x]
        thisBmaj=str(secondarySources['secBmaj'][x])+'arcsec'
        thisBmin=str(secondarySources['secBmin'][x])+'arcsec'
        thisPA=str(secondarySources['secPA'][x])+'deg'

    print "\n >>>"+source_no+" "+position+" "+thisBmaj+" "+thisBmin+" "+thisPA

    #-- 2) Load associated spectrum / or generate one from image !

    #-- See if an image exists
    imageFile=msname+'_'+targ+'_SPW_'+str(SPW)+'_ContFind.image'
    print "\n >>> looking for "+imageFile
    if len(glob.glob(imageFile+'.image')):
            useImage=glob.glob(imageFile+'.image')[0]
            print "\n >>> Image found using "+useImage

            #--- See if spectrum exists
            sourName=re.split('/',useImage)[-1]
            sourName='/'+sourName
            specFile=cwd+sourName+'_spec.txt'

            specFile=getSourcePos2(useImage,position,cwd,source_no, thisBmaj, thisBmin, thisPA)

    else:
            print "\n >>> No image found... I guess I'll have to make one"
            print " >>> Assuming the lowest target field ID is the mosaic centre... NEED BETTER MESSAGE HERE"
            #1) Get cell size and field of view
            cellSize,FoV=imCellSize(msname,SPW)
            imageSize=cleanhelper.getOptimumSize(int((FoV/cellSize)*2.0))
            useImage=imageFile
            clean(vis = msname,
                  imagename = useImage,
                  field = str(targIdx),
                  spw =str(SPW),
                  weighting = 'briggs',
                  outframe='LSRK',
                  phasecenter=str(targIdx),
                  robust=0.5,
                  cell=[str(cellSize)+'arcsec'],
                  imsize=[imageSize,imageSize], #covers about the FoV
                  imagermode='mosaic',
                  width=1,
                  mode='channel',
                  nchan=-1,
                  start='',
                  niter=0)

            specFile=getSourcePos2(useImage+'.image',position,cwd,source_no, thisBmaj, thisBmin, thisPA)

    freq,S=loadFromText(specFile)
    #-- 2.5) Test plots
    testPlots(freq,S,'black')


    #--- 2.75) Tidy up the data (i.e. remove absorption , weird end chans etc etc)
    #--- and obvisous spectral lines

    #--- get brightline emission
    psd_rms,poss_lines,scale_limits=specFit(S)
    poss_lines=poss_lines*0.0 #-- THIS IS NOT USED SO SET TO ZERO
    #--- define where lines aren't
    poss_not_lines=(1.0-poss_lines)#*(np.max(S)*1.02)#last bit jsut for scaling
    lineless_S=poss_not_lines*S
    #testPlots(freq,poss_not_lines*(np.max(S)*0.5),'c')


    #-- 3) Sigma clipping loop... explained in calcFuncs.py
    freqS,newS,meanS,stdS=sigmaClipperSTD(freq,S,2.0,95.5)
    testPlots(freqS[np.where(newS!=0)],newS[np.where(newS!=0)],'orange','.','none')

    #-- 4) Testing the gradient approach
    gradFreq,gradS=calcGrad(freq,S)
    highFreq,highCh,highS=whereHighGrad(gradFreq,gradS,2.0*theoRMS)
    gradyS=newS[highCh]
    gradyS=gradyS[np.where(gradyS!=0.0)]

    #-- 6) Gaussian tests

    fig3 = plt.figure(3)
    ax3 = fig3.add_subplot(111)

    #-- Get interquartile range --#
    binX=newS[np.where(newS!=0.0)]

    q75, q25 = np.percentile(binX, [75 ,25])
    iqr = q75 - q25
    bin_widths=2.0*iqr*(len(binX)**(-1.0/3.0))
    num_bins=(np.max(binX)-np.min(binX))/bin_widths
    #print bin_widths,num_bins,'!!! BREAD !!!'


    valsSC,binsCent=np.histogram(newS[np.where(newS!=0.0)],bins=np.ceil(num_bins))
    valsGR,binsCent=np.histogram(gradyS,bins=binsCent)

    centreBins=(binsCent[:-1] + binsCent[1:])/2

    #--- remove outliers

    ax3.hist(newS[np.where(newS!=0.0)], binsCent, facecolor='orange', edgecolor='orange', alpha=0.15)
    ax3.hist(gradyS, binsCent, facecolor='cyan', edgecolor='cyan', alpha=0.15)

    ax3.plot(centreBins,valsSC,'rd--')
    ax3.plot(centreBins,valsGR,'bd--')

    #-- Fit the gaussian
    meanSC=sum(centreBins*valsSC)/sum(valsSC)
    sigmaSC=np.sqrt(sum(valsSC*(centreBins-meanSC)**2)/sum(valsSC))

    meanGR=sum(centreBins*valsGR)/sum(valsGR)
    sigmaGR=np.sqrt(sum(valsGR*(centreBins-meanGR)**2)/sum(valsGR))

    print 'theoRMs',theoRMS,'!!!'
    try:
            poptSC,pcovSC = curve_fit(gauss,centreBins,valsSC,p0=[np.max(valsSC),meanSC,sigmaSC])
            poptGR,pcovGR = curve_fit(gauss,centreBins,valsGR,p0=[np.max(valsGR),meanGR,sigmaGR])

            ax3.plot(centreBins,gauss(centreBins,poptSC[0],poptSC[1],poptSC[2]),'ro:',label='fit')
            ax3.plot(centreBins,gauss(centreBins,poptGR[0],poptGR[1],poptGR[2]),'bo:',label='fit')
            plt.savefig(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_gaussPlot.png')
            ax3.cla()
            fig3.clf()

    except RuntimeError:
            print "\n >>> Curve_fit failed."
    #--- Now get the standard deviation and list chans with values within 1,2 and 3 standard deviations.

    print " \n >>> Sigma clipper gives... Mean: "+str(poptSC[1])
    print " >>>                    Std. Dev: "+str(poptSC[2])
    print " >>> --------"
    print " \n >>> Gradient test gives... Mean: "+str(poptGR[1])
    print " >>>                    Std. Dev: "+str(poptGR[2])
    print " >>> --------"

    #---  SD

    testPlots(freq[np.where(np.logical_and(S>=(poptSC[1]-StdDevFactor*poptSC[2]), S<=(poptSC[1]+StdDevFactor*poptSC[2])))],S[np.where(np.logical_and(S>=(poptSC[1]-StdDevFactor*poptSC[2]), S<=(poptSC[1]+StdDevFactor*poptSC[2])))],'magenta','.','none')

    testPlots([np.min(freq), np.max(freq)],[(poptSC[1]-StdDevFactor*poptSC[2]),poptSC[1]-StdDevFactor*poptSC[2]],'magenta')
    testPlots([np.min(freq), np.max(freq)],[(poptSC[1]+StdDevFactor*poptSC[2]),poptSC[1]+StdDevFactor*poptSC[2]],'magenta')


    testPlots(freq[np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptGR[1]+StdDevFactor*poptGR[2])))],S[np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptGR[1]+StdDevFactor*poptGR[2])))],'lime','x','none')

    testPlots([np.min(freq), np.max(freq)],[(poptGR[1]-StdDevFactor*poptGR[2]),poptGR[1]-StdDevFactor*poptGR[2]],'lime')
    testPlots([np.min(freq), np.max(freq)],[(poptGR[1]+StdDevFactor*poptGR[2]),poptGR[1]+StdDevFactor*poptGR[2]],'lime')


    #--- ZERO LINE
    testPlots([np.min(freq)-0.01e9, np.max(freq)+0.1e9],[0, 0],'green')
    plt.savefig(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_lineFree.png')
    plt.cla()
    plt.clf()
    #--- Channels to use
    print " \n >>> Channels in the "+str(StdDevFactor)+" sigma range of Sigma clip:\n"+str(np.where(np.logical_and(S>=(poptSC[1]-StdDevFactor*poptSC[2]), S<=(poptSC[1]+StdDevFactor*poptSC[2])))[0])
    print " \n >>> Channels in the "+str(StdDevFactor)+" sigma range of Gradient test:\n"+str(np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptSC[1]+StdDevFactor*poptGR[2])))[0])


    sigChans=np.where(np.logical_and(S>=(poptSC[1]-StdDevFactor*poptSC[2]), S<=(poptSC[1]+StdDevFactor*poptSC[2])))[0]
    gradChans=np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptSC[1]+StdDevFactor*poptGR[2])))[0]
    #--- Combine the channels from the two tests
    combinedChans=np.intersect1d(sigChans,gradChans)
    #--- And exclude where specFit thinks lines are... jsut to be safe
    if np.sum(poss_not_lines)==0.0:#To catch when specFit finds no lines
            useChans=combinedChans
    else:
            useChans=np.intersect1d(((np.where(poss_not_lines==1.0)[0])),combinedChans)

    print useChans

    spwString=numpyToSPWString(SPW,useChans)

    outSPWString = open(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_LineFreeChans.txt','w')
    print >> outSPWString,  spwString
    outSPWString.close()

#========== PART 2 ============================================#
#---- GET ALL THE LINE FREE FILES CLEAR THE UNQIUE SET --------#
useThis=np.zeros(numChan)
for x in range(useRange):

    if useRange == 1:
        source_no=re.split('source',str(secondarySources['souNum']))[1]
    else:
        source_no=re.split('source',secondarySources['souNum'][x])[1]

    thisSPWstr=open(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_LineFreeChans.txt','r')
    for line in thisSPWstr:
        nuline=re.sub(str(SPW)+':','',line)
        nuline=re.sub('\n','',nuline)

    nuline2=re.split(';',nuline)
    nulineNP=np.asarray(nuline2,dtype=np.int)

    for chan in nuline2:
        ch=int(chan)
        useThis[ch]+=1
    thisSPWstr.close()

    smoothUseThis=smoothLineFree(useThis,useRange)

allSourceUseChans=np.where(smoothUseThis==useRange)[0]

allSourceSpwString=numpyToSPWString(SPW,allSourceUseChans)
allSourceSpwStringChunk=chunkChansSPWformat(allSourceSpwString)

allSourceOutSPW = open(targ+'_allSource_SPW_'+str(SPW)+'_LineFreeChans.txt','w')
print >> allSourceOutSPW,  allSourceSpwStringChunk
allSourceOutSPW.close()
