import re
import numpy as np
import os
import matplotlib.pyplot as plt
import sys
import glob
from scipy.optimize import curve_fit
from cleanhelper import *
from taskinit import *
from listobs_cli import listobs_cli as listobs
from tclean_cli import tclean_cli as tclean
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

""" LUMBERJACK CASA TASK VERSION

- Created by A.Avison ages ago, finalised Aug -2020

--- INPUT PARAMETERS ----
 User will need to input the following parameters:
- Name of measurement set (parameter msname)
- Spectral Window Number (as parameter SPW)
- Target name (as parameter field)
- [optional] A secondary Source file (as parameter secsour see below for more details)
- [optional] A standard deviation factor to cut off sigma clipping (as parameter stddevfact)

--- DATA LOCATION ---
In the current directory you will need:
- A calibrated ALMA measurement set containing your target as defined in the field parameter.
- [Optional] A list of sources in the field in a file named <field>+_SecondarySources.txt
    - The format of this file is:
    sourceX     RA[hh:mm:ss.000]    Dec[dd:mm:ss.000]   Bmaj*   Bmin*   BPA*
    *fitted 2D Gaussian major, minor axis and position angle.

--- OUTPUT ---
If not using a secondary sources file:
- An output txt file named <field>_SourceX_SPW_<SPW>_LineFreeChans.txt. This contains the line free channels at the peak flux density position in that field. The line free channels are given in CASA SPW syntax: e.g.
25:1~30;33~81;84~526;544~591;594~1760;1783~1852;1856~1868;1871~1898;1901~1917

If using a secondary Sources file:

For each source listed in *_SecondarySources.txt you will get:
- An output txt file named <target_name>_sourceNo_<#>_SPW_<SPW>_LineFreeChans.txt. This contains the line free channels at that position.
- Two PNG images:
    - <target_name>_sourceNo_<#>_SPW_<SPW>_lineFree.png which shows the spectrum and line free chans
    - <target_name>_sourceNo_<#>_SPW_<SPW>_gaussPlot.png which shows a histogram of the flux values of line free channels.
- A txt file named <target_name>_allSource_SPW_<SPW>_LineFreeChans.txt which combines the values from each source and 'chunks' them in to a CASA SPW string format. e.g. 25:1~30;33~81;84~526;544~591;594~1760;1783~1852;1856~1868;1871~1898;1901~1917
"""
#---------- TASK VERSION ---------------#
def lumberjack(vis, spw, field, secsour, stddevfact):
    presdir = os.path.realpath('.')
    #========== PART 0 ============================================#
    #---- USER INPUT AND GENERATE THE SPECTRUM TO ANALYSE ---------#
    casalog.origin('lumberjack')

    #--- USER INPUT PARAMS
    # msname=cwd+'/'+vis
    msname=presdir+'/'+vis

    SPW=int(spw)
    targ=field

    #--- set StdDevFactor to default unless otherwise specified
    if stddevfact == '':
        StdDevFactor=1.5
    else:
        StdDevFactor=stddevfact

    #--- Switch to turn on multiple source extraction if User defines secondarySourcesFile
    #--- True to use a user defined list of secondary source positions, False to find spectrum at peak pixel.
    if secsour == '':

        useSecSources = False
    else:
        useSecSources = True

    if useSecSources:
        secondaryFile=secsour

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
    nAnt,antDiam,BW,tInt,sourceFields,chWid,targIdx,numChan=measSetInfo(msname,SPW,myfield=targ)

    Tsys = getTsys(msname,SPW)
    #print Tsys
    theoRMS=calcSens(nAnt,chWid,tInt,Tsys,antDiam)

    print "\n >>> Assuming "+str(nAnt)+" antennas of diameter "+str(antDiam)+" and channel width of "+str(chWid)+"\n >>> observed for "+str(tInt)+" sec"
    print "\n >>> The theoretical RMS in a single channel is (assuming no flagging etc) is "+str(theoRMS)+"Jy"

    print sourceFields

    #-- 1.5) Depending on if a user supplies a SecSource list allow ability to loop around detected continuum sources.
    if useSecSources:
        print "\n >>> In Secondary Source mode: Using user defined positions and source properties to generate spectra"

        secondarySources=np.genfromtxt(secondaryFile, dtype=None, names=['souNum','secRA','secDec','secBmaj','secBmin','secPA'])

        #- How many sources?

        try:
            useRange = len(secondarySources['souNum'])
        except TypeError:
            useRange = 1
    else:
        print "\n >>> In Unknown Source mode: Using peak pixel position to generate spectra"
        useRange = 1

    for x in range(useRange):
        if useRange == 1:
            if useSecSources:
                source_no=re.split('source',str(secondarySources['souNum']))[1]
                position=secondarySources['secRA']+'\t'+secondarySources['secDec']
                thisBmaj=str(secondarySources['secBmaj'])+'arcsec'
                thisBmin=str(secondarySources['secBmin'])+'arcsec'
                thisPA=str(secondarySources['secPA'])+'deg'

                print "\n >>>"+source_no+" "+position+" "+thisBmaj+" "+thisBmin+" "+thisPA
            else:
                source_no='X'

        else:
            source_no=re.split('source',secondarySources['souNum'][x])[1]
            position=secondarySources['secRA'][x]+'\t'+secondarySources['secDec'][x]
            thisBmaj=str(secondarySources['secBmaj'][x])+'arcsec'
            thisBmin=str(secondarySources['secBmin'][x])+'arcsec'
            thisPA=str(secondarySources['secPA'][x])+'deg'

            print "\n >>>"+source_no+" "+position+" "+thisBmaj+" "+thisBmin+" "+thisPA

        #-- 2) Load associated spectrum / or generate one from image !

        #-- See if an image exists
        imageFile=msname+'_'+targ+'_SPW_'+str(SPW)+'_LumberJack.im'
        print "\n >>> looking for "+imageFile

        if len(glob.glob(imageFile+'.image')):
                useImage=glob.glob(imageFile+'.image')[0]
                print "\n >>> Image found, using "+useImage

                #--- See if spectrum exists
                sourName=re.split('/',useImage)[-1]
                sourName='/'+sourName
                specFile=cwd+sourName+'_spec.txt'

                if useSecSources:
                    specFile=getSourcePos2(useImage,position,cwd,source_no, thisBmaj, thisBmin, thisPA) # get specta at defined user positions
                else:
                    specFile=getSourcePos(useImage,cwd)# get spectrum as peak pixel position (within synth beam)

        else:
                print "\n >>> No image found... I guess I'll have to make one"
                print " >>> Assuming the lowest target field ID is the mosaic centre... NEED BETTER MESSAGE HERE"
                #1) Get cell size and field of view
                cellSize,FoV=imCellSize(msname,SPW)
                imageSize=cleanhelper.getOptimumSize(int((FoV/cellSize)*2.0))
                useImage=imageFile
                tclean(vis = msname,
                      imagename = useImage,
                      field = str(targIdx),
                      spw =str(SPW),
                      weighting = 'briggs',
                      outframe='TOPO',
                      #phasecenter=str(targIdx),
                      robust=0.5,
                      cell=[str(cellSize)+'arcsec'],
                      imsize=[imageSize,imageSize], #covers about the FoV
                      gridder='mosaic',
                      width=1,
                      specmode='cube',
                      nchan=-1,
                      start='',
                      niter=0,
                      restoringbeam = 'common')

                if useSecSources:
                    specFile=getSourcePos2(useImage+'.image',position,cwd,source_no, thisBmaj, thisBmin, thisPA) # get specta at defined user positions
                else:
                    specFile=getSourcePos(useImage+'.image',cwd)# get spectrum as peak pixel position (within synth beam)

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
        testPlots(freq,poss_not_lines*(np.max(S)*0.5),'c')


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

        valsSC,binsCent=np.histogram(newS[np.where(newS!=0.0)],bins=np.ceil(num_bins))
        valsGR,binsCent=np.histogram(gradyS,bins=binsCent)

        centreBins=(binsCent[:-1] + binsCent[1:])/2

        #--- remove outliers

        ax3.hist(newS[np.where(newS!=0.0)], binsCent, facecolor='orange', edgecolor='orange', alpha=0.15)
        ax3.hist(gradyS, binsCent, facecolor='cyan', edgecolor='cyan', alpha=0.15)
        #
        ax3.plot(centreBins,valsSC,'rd--')
        ax3.plot(centreBins,valsGR,'bd--')

        #-- Fit the gaussian
        meanSC=sum(centreBins*valsSC)/sum(valsSC)
        sigmaSC=np.sqrt(sum(valsSC*(centreBins-meanSC)**2)/sum(valsSC))

        meanGR=sum(centreBins*valsGR)/sum(valsGR)
        sigmaGR=np.sqrt(sum(valsGR*(centreBins-meanGR)**2)/sum(valsGR))

        # print 'theoRMs',theoRMS,'!!!'
        try:
                poptSC,pcovSC = curve_fit(gauss,centreBins,valsSC,p0=[np.max(valsSC),meanSC,sigmaSC])
                poptGR,pcovGR = curve_fit(gauss,centreBins,valsGR,p0=[np.max(valsGR),meanGR,sigmaGR])

                ax3.plot(centreBins,gauss(centreBins,poptSC[0],poptSC[1],poptSC[2]),'ro:',label='fit')
                ax3.plot(centreBins,gauss(centreBins,poptGR[0],poptGR[1],poptGR[2]),'bo:',label='fit')
                ax3.set_xlabel('binned flux')
                ax3.set_ylabel('Counts')
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


        testPlots(freq[np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptGR[1]+StdDevFactor*poptGR[2])))][0],S[np.where(np.logical_and(S>=(poptGR[1]-StdDevFactor*poptGR[2]), S<=(poptGR[1]+StdDevFactor*poptGR[2])))][0],'lime','x','none')

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

        # print useChans

        spwString=numpyToSPWString(SPW,useChans)

        outSPWString = open(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_LineFreeChans.txt','w')
        print >> outSPWString,  spwString
        outSPWString.close()

    #========== PART 2 ============================================#
    #---- GET ALL THE LINE FREE FILES CLEAR THE UNQIUE SET --------#
    useThis=np.zeros(numChan)
    for x in range(useRange):

        if useRange == 1:
            if useSecSources:
                source_no=re.split('source',str(secondarySources['souNum']))[1]
            else:
                source_no = 'X'
        else:
            source_no=re.split('source',secondarySources['souNum'][x])[1]

        thisSPWstr=open(targ+'_sourceNo_'+source_no+'_SPW_'+str(SPW)+'_LineFreeChans.txt','r')
        for line in thisSPWstr:
            nuline=re.sub(str(SPW)+':','',line)
            nuline=re.sub('\n','',nuline)

        nuline2=re.split(';',nuline)

        for chan in nuline2:
            ch=int(chan)
            useThis[ch]+=1
        thisSPWstr.close()

        smoothUseThis=smoothLineFree(useThis,useRange,numChan)

    allSourceUseChans=np.where(smoothUseThis==useRange)[0]

    allSourceSpwString=numpyToSPWString(SPW,allSourceUseChans)

    allSourceSpwStringChunk=chunkChansSPWformat(allSourceSpwString)
    if useSecSources:
        allSourceOutSPW = open(targ+'_allSource_SPW_'+str(SPW)+'_LineFreeChans.txt','w')
    else:
        allSourceOutSPW = open(targ+'_SourceX_SPW_'+str(SPW)+'_LineFreeChans.txt','w')
    print >> allSourceOutSPW,  allSourceSpwStringChunk

    allSourceOutSPW.close()
