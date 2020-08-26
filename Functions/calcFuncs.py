import numpy as np
import re
import sys

auPath = '<PATH TO ANALYSIS UTILS>' #you can download AnalysisUtils from https://casaguides.nrao.edu/index.php/Analysis_Utilities
sys.path.insert(0,auPath)
import analysisUtils as aU

"""TO DO: Calcsensitivity for inhomogenous array"""

def smoothLineFree(LFCs,sourNo,numCh):
    cpLFCs = np.copy(LFCs)
    lineChans=np.where(cpLFCs==0.0)[0]
    for lineChan in lineChans:
        if lineChan < int(numCh)-2:
            if lineChan<len(cpLFCs)-1:
                if cpLFCs[lineChan-1] == sourNo and cpLFCs[lineChan+1] == sourNo:
                    cpLFCs[lineChan]=sourNo
                elif cpLFCs[lineChan-1] == sourNo and cpLFCs[lineChan+2] == sourNo:
                    cpLFCs[lineChan]=sourNo
            elif lineChan == len(cpLFCs):
                if cpLFCs[lineChan-1] == sourNo:
                    cpLFCs[lineChan]=sourNo

    return cpLFCs

def imCellSize(msname,spw):
     c=299792458.0 #SoL m/s
     #--- max baseline
     blines=aU.getBaselineLengths(msname,sort=True)
     maxBline=blines[len(blines)-1][1]
     print maxBline
     #--- spw cent freq
     sciFreqs=aU.getScienceFrequencies(msname)
     imFreq=sciFreqs[spw]

     #--- Calc resolution
     res=((c/imFreq)/maxBline)*(180.0/np.pi)*3600.0
     FoV=((c/imFreq)/12.0)*(180.0/np.pi)*3600.0
     cellSize=res/6.0

     return cellSize, FoV

def calcGrad(chans,flux):
    #--- Takes the gradient on a channel by channel step
    gradVal=[]
    for x in range(len(chans)-1):
        gradVal.append(flux[x+1]-flux[x])

    gradVal_arr=np.array(gradVal)
    gradChans=chans[1:]

    return gradChans, gradVal_arr


def whereHighGrad(gradFreq,gradFlux,theoRMS):
    #--- Find channels with gradient <2x theorms
    moduGradFlux = np.sqrt(gradFlux**2.0)
    gradFlux[np.where(moduGradFlux<(2.0*theoRMS))]
    gradFluxIndx = (np.where(moduGradFlux<(2.0*theoRMS))[0])
    gradHighFreq=gradFreq[gradFluxIndx]

    return gradHighFreq, gradFluxIndx, gradFlux[np.where(moduGradFlux<(2.0*theoRMS))]


def calcSens(numAnts,BW,t_int,Tsys,diam):
    #--- Calc sensitivity and return in Janskys
    if BW<0.0: # To compensate for negative chanwidths
        BW=BW*-1.0

    t_int=43.5*60.0
    k=1.38e-23
    top=2.0*k*Tsys
    insqrt=((numAnts*(numAnts-1))*BW*(t_int))
    bottom=0.7*(np.pi*((diam/2.0)**2.0))*(np.sqrt(insqrt))

    sens=top/bottom
    #print float(sens/1e-26)
    return float(sens/1e-26)




def sigmaClipperSTD(ch,S,clip_level=2.0,tol=95.5):
    """0) Take all data, derive a median and standard deviation.
       1) Exclude all data point which are > median+(clip_level*std) or < median-(clip_level*std)
       2) Caculate stdLev which is ((oldStdDev - newStdDev)/newstdDev): if stdLev > tol (entered as a %age) stop, else continue
       3) Calculate SNR (Peak/medianS), if it starts increasing stop.
       4) If the remaining channels == 0 stop.

    """

    SNR=1000.0
    oldSNR=1000.0
    oldStd=1000.0
    stdLev=1000.0
    while stdLev>(1.0-(tol/100.0)):

        peakS=np.max(S) #--- Find peak value in current S array
        nChan=len(S[np.nonzero(S)]) #--- Find number of non-zeroed channels

        if nChan==0:
            print "\n >>> SNR of "+str(SNR)+" reached... stopping now"
            SNR=1.0
            newS=tmpS
        else:
            meanS=np.sum(S[np.nonzero(S)])/float(nChan)                  #of all channels
            medianS=np.median(S[np.nonzero(S)])
            stdS=np.std(S[np.nonzero(S)])
            SNR=peakS/medianS
            print "\n >>> Mean flux across all channels: "+str(meanS)
            print " >>> Median flux across all channels: "+str(medianS)
            print " >>> Peak flux across all channels: "+str(peakS)
            print " >>> Std Dev. across all channels: "+str(stdS)
            print " >>> SNR = "+str(SNR)

            print oldStd, stdS, '!----!'
            print (stdS/oldStd)*100.0
            stdLev= (oldStd-stdS)/stdS
            print stdLev

            #Want points where value is between median +/- alpha*stdS
            tru=np.where(np.logical_and(S>medianS-(clip_level*stdS),S<medianS+(clip_level*stdS)))[0]
            print medianS-(clip_level*stdS),medianS+(clip_level*stdS)
            newS=np.zeros(len(S))
            tmpS=S
            for x in tru:
                newS[x]=S[x]

            S=[]
            S=newS

            if SNR>oldSNR:
                    print "\n >>> SNR starting to increase after SNR="+str(oldSNR)+" reached... stopping now"
                    SNR=1.0
                    newS=tmpS

        oldSNR=SNR
        oldStd=stdS

    return ch, newS, meanS, stdS

def gauss(x,a,b,c):
        """ gaussian function for fitting """
        return a*np.exp(-(x-b)**2/(2*c**2))


def specFit(fl_data):
        """ Try to tidy up data by removing absorption,obvious emission and  edge channels based on 2012 SpecFit.py by me! """
        freq_naxis=len(fl_data)
        mean_flux=sum(fl_data)/freq_naxis                  #of all channels
        median_flux=np.median(fl_data)
        print "Mean flux across all channels: "+str(mean_flux)
        print "Median flux across all channels: "+str(median_flux)
        j=0                                            #counter for none line channels
        k=0                                            #counter for line channels
        q=0
        pseudo_rms_tot=0
        sumFlux=0
        #--- First pass calculate rms for all channels above 3 x mean/median value ---#

        for i in fl_data:
            if i >(3.0*mean_flux) or i < (-3.0*mean_flux):
                k=k+1
                sumFlux=sumFlux+(i*i)
            else:
                j=j+1
                pseudo_rms_tot=pseudo_rms_tot+(i*i)
            q=q+1

        print str(k)+" channels above 3.0 * median over all channels"
        if j==0:
            print "all channels above 3.0 * median over all channels"
            print "using sqrt of total flux as pseudo rms"
            pseudo_rms=np.sqrt(sumFlux/float(k))
        else:
            pseudo_rms=np.sqrt(pseudo_rms_tot/float(j))
            print "Pseudo rms: "+str(pseudo_rms)

        if k==0:
            highpass=np.max(fl_data)/pseudo_rms
            print 'reduced highpass '+str(highpass)
            scale_limits=highpass/3.0
        else:
            highpass=3.0
            scale_limits=1.0

        #----------------------- high RMS pass -----------------------------------#
        #--- 2nd pass calculate rms for all channels above 3 x first rms ---#
        #--- if a channel has is above 3x rms then make line_regions -------#
        #--- == line_val ---------------------------------------------------#
        line_regions_highrms=np.zeros(freq_naxis)
        baseline_use_regions=np.zeros(freq_naxis)
        line_val_highrms=1.0
        v=0
        l=0
        for ii in fl_data:
            if ii >(highpass*pseudo_rms) or ii <(-highpass*pseudo_rms):
                l=l+1
                line_regions_highrms[v]=line_val_highrms
                baseline_use_regions[v]=0
            else:
                baseline_use_regions[v]=fl_data[v]
            v=v+1

        #--- Assess line_regions to exclude single channels ---#
        w=0
        print freq_naxis
        for lr in line_regions_highrms:
            if lr == line_val_highrms:
                if w==(freq_naxis-1):
                    if line_regions_highrms[w-1]==0.0:
                        line_regions_highrms[w]=0.0
                elif w==0:
                    if line_regions_highrms[w+1]==0.0:
                        line_regions_highrms[w]=0.0
                else:
                    if line_regions_highrms[w-1]==0.0 and line_regions_highrms[w+1]==0.0:
                        line_regions_highrms[w]=0.0
            w=w+1

        #--------------------- low RMS pass -----------------------------------#

        #--- 2nd pass calculate rms for all channels above 2 x first rms ---#
        #--- if a channel has is above 2x rms then make line_regions -------#
        #--- == line_val ---------------------------------------------------#
        line_regions_lowrms=np.zeros(freq_naxis)
        line_val_lowrms=line_val_highrms

        vv=0
        ll=0
        for iii in fl_data:
            if iii >(scale_limits*2.0*pseudo_rms) and iii <(scale_limits*3.0*pseudo_rms) :
                ll=ll+1
                line_regions_lowrms[vv]=line_val_lowrms
                baseline_use_regions[vv]=0

            vv=vv+1

        #--- Assess line_regions to exclude single channels ---#
        ww=0

        for llr in line_regions_lowrms:
            if llr == line_val_lowrms:
                if ww==(freq_naxis-1):
                    if line_regions_lowrms[ww-1]==0.0:
                        line_regions_lowrms[ww]=0.0

                elif ww==0:
                    if line_regions_lowrms[ww+1]==0.0:
                        line_regions_lowrms[ww]=0.0
                else:
                    if  line_regions_lowrms[ww-1]==0.0 and line_regions_lowrms[ww+1]==0.0:
                        line_regions_lowrms[ww]=0.0
            ww=ww+1

        print " >> Combining rms thresholding"
        print " ------------------------------------------------------"

        threshold_line_regions=line_regions_lowrms+line_regions_highrms

        #--- Smooth along threshold_line_regions bring in the odd
        #--- line which wasn't flagged as emission before
        smoothed_lr_f=np.zeros(freq_naxis)
        smoothed_lr_b=np.zeros(freq_naxis)

        www=0
        for thlr in threshold_line_regions:
            forw_check=forward_ten(threshold_line_regions,www)
            backw_check=backward_ten(threshold_line_regions,www)

            smoothed_lr_f[www]=forw_check
            smoothed_lr_b[www]=backw_check

            www=www+1

        vv=0
        smoothed_lr=np.zeros(freq_naxis)
        for smlr in smoothed_lr:
            if smoothed_lr_f[vv] >=3.0 or smoothed_lr_b[vv]>=3.0:
                smoothed_lr[vv]=(smoothed_lr_b[vv]+smoothed_lr_f[vv])
            vv=vv+1

        smooth_window_length=20
        smoothed_lr=smooth(smoothed_lr,smooth_window_length,'flat')

        vvw=0
        for bz in smoothed_lr:
            if smoothed_lr[vvw] >0.0:
                smoothed_lr[vvw]=1.0
            vvw=vvw+1

        linesHere=smoothed_lr[(smooth_window_length/2):(freq_naxis+(smooth_window_length/2))]
        return pseudo_rms, linesHere, scale_limits



#---- Functions which are need for tidyData
def forward_ten(arr,n): #scan forward an see the sum of the next 10 chans... becomes unreliable in last 10 chans
    arr_size=arr.size
    nextt=0
    if n+5 < arr_size:
        for i in range(5):
            nextt=nextt+arr[n+i]
    else:
        j=arr_size-n
        for ii in range(j):
            nextt=nextt+arr[n+ii]

    return nextt

def backward_ten(arr,n): #scan backward an see the sum of the last 10 chans... becomes unreliable in first 10 chans
    arr_size=arr.size
    lastt=0
    if n-5 > 0:
        for i in range(5):
            lastt=lastt+arr[n-i]
    else:
        j=n
        for ii in range(j):
            lastt=lastt+arr[n-ii]

    return lastt


def smooth(x,window_len=11,window='hanning'):
    #--- Borrowed from Stackoverflow
    if x.ndim != 1:
         raise ValueError, "smooth only accepts 1 dimension arrays."

    if x.size < window_len:
        raise ValueError, "Input vector needs to be bigger than window size."

    if window_len<3:
        return x

    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"

    s=np.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]

    if window == 'flat': #moving average
        w=np.ones(window_len,'d')
    else:
        w=eval('np.'+window+'(window_len)')

    y=np.convolve(w/w.sum(),s,mode='valid')
    return y

def deAbsorb(fl_data,theoRMS):
        """ Try to tidy up data by removing absorption and edge channels, this is a bit weak and could be re-written"""
        freq_naxis=len(fl_data)
        mean_flux=sum(fl_data)/freq_naxis                  #of all channels
        median_flux=np.median(fl_data)
        print "Mean flux across all channels: "+str(mean_flux)
        print "Median flux across all channels: "+str(median_flux)

        abs_region=np.ones(freq_naxis)
        #abs_region[np.where(fl_data<(median_flux-(10.0*theoRMS)))]=0.0
        abs_region[np.where(fl_data<(3.0*theoRMS))]=0.0
        fixed_data=fl_data*abs_region

        return abs_region, fixed_data

def chunkChansSPWformat(spwString):
    #=== split off channel list ===#
    chanList = re.split(':',spwString)[1]
    chunkedChans = re.split(':',spwString)[0]+':'
    #== append and insanely large final channel
    chanList += ';1000000000'
    #=== check channels
    prevCh=int(re.split(';',chanList)[0])
    startCh=int(re.split(';',chanList)[0])
    endCh=-1

    for ch in re.split(';',chanList):
        iCh=int(ch)
        #print iCh, iCh-prevCh
        if iCh-prevCh == 1 or iCh-prevCh == 2 or iCh-prevCh == 3:
            endCh=iCh
            prevCh=iCh

        else:
            if endCh<0:
                print 'Collapsing down line free channels'
            elif startCh > endCh:
                chunkedChans += str(startCh)+';'
            else:
                chunkedChans += str(startCh)+'~'+str(endCh)+';'

            startCh=iCh
            prevCh=iCh

    chunkedChans = chunkedChans[:-1]
    print chunkedChans



    #--- Add a bit of a buffer to lines > 10 chans wide
    splitSemiCol = re.split(';',chunkedChans)
    finChunked = re.split(':',splitSemiCol[0])[0]+':'
    buffChans = 4

    for regs in range(len(re.split(';',chunkedChans))):
        #print regs, splitSemiCol[regs]
        if regs==0:
            if re.search('~',splitSemiCol[regs]):
                endCh = int(re.split('~',splitSemiCol[regs])[1])-buffChans
                startCh = int(re.split('~',re.split(':',splitSemiCol[regs])[1])[0])
                if not startCh > endCh:
                    finChunked += str(startCh)+'~'+str(endCh)
        elif regs > 0 and regs < len(re.split(';',chunkedChans))-1:
            if re.search('~',splitSemiCol[regs]):
                #print splitSemiCol[regs]
                startCh = int(re.split('~',splitSemiCol[regs])[0])+buffChans+1
                endCh = int(re.split('~',splitSemiCol[regs])[1])-buffChans
                if not startCh > endCh:
                    finChunked += ';'+str(startCh)+'~'+str(endCh)
        else:
            if re.search('~',splitSemiCol[regs]):
                endCh = int(re.split('~',splitSemiCol[regs])[1])
                startCh = int(re.split('~',splitSemiCol[regs])[0])+buffChans
                if not startCh > endCh:
                    finChunked += ';'+str(startCh)+'~'+str(endCh)

    print finChunked

    return finChunked

#==========================

""" OLD DONT USE """

"""def sigmaClipper(ch,S,clip_level=0.7):
"""
"""   sigmaClipper: This takes the channel number and the flux per channel as inputs.
    It also takes a "clip_level" or defaults to 70%. It then finds the mean and peak flux values.
    Calculates SNR as peak/mean, if this  value is > 1.0 then it sets all channels with
    flux above 70% (or clip_level) of the peak value to zero and repeats the process.
    Once SNR is ~<1.0 it stops and the flux array is returned with all non-zero values assumed
    to be continuum channels.
"""

"""    SNR=1000.0
    oldSNR=1000.0
    oldStd=1000.0
    while SNR>1.0:

        print oldSNR
        peakS=np.max(S) #--- Find peak value in current S array
        nChan=len(S[np.nonzero(S)]) #--- Find number of non-zeroed channels

        if nChan==0:
            print "\n >>> SNR of "+str(SNR)+" reached... stopping now"
            SNR=1.0
            newS=tmpS
        else:
            meanS=np.sum(S[np.nonzero(S)])/float(nChan)                  #of all channels
            medianS=np.median(S[np.nonzero(S)])
            stdS=np.std(S[np.nonzero(S)])
            SNR=peakS/meanS
            print "\n >>> Mean flux across all channels: "+str(meanS)
            print " >>> Median flux across all channels: "+str(medianS)
            print " >>> Peak flux across all channels: "+str(peakS)
            print " >>> Std Dev. across all channels: "+str(stdS)
            print " >>> SNR = "+str(SNR)


            tru=np.where(S<clip_level*peakS)[0]
            newS=np.zeros(len(S))
            tmpS=S
            for x in tru:
                newS[x]=S[x]

            S=[]
            S=newS

            if SNR>oldSNR:
                    print "\n >>> SNR starting to increase after SNR="+str(oldSNR)+" reached... stopping now"
                    SNR=1.0
                    newS=tmpS

        oldSNR=SNR
        oldStd=stdS


    return ch, newS, meanS, stdS"""
