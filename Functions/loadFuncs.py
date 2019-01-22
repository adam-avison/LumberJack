import numpy as np
import os
import sys
import glob
import re

def loadFromText(txtfile):

    chan,S=np.loadtxt(txtfile,unpack=True)
    return chan,S

def whereIsEverything(cwd):
          mem_wd=re.split('calibrated',cwd)[0]
          print "\n >>> Checking that all the required files are present."

          #--- Find Tsys Tables
          TsysTables=[]

          for tables in os.listdir(cwd+'/working/'):
                    if tables.endswith('tsyscal.tbl'):
                              TsysTables.append(cwd+'/working/'+tables)

          if len(TsysTables)==0:
                    sys.exit("\n >>> No Tsys Tables found in:\n\n"+cwd+"/working/\n\n >>> Bailing out!")
          else:
                    print"\n >>> Tsys table(s) found."

          #--- Find listobs files

          try:
                    pipelineFolder=glob.glob(mem_wd+'qa/pipeline-*')[0]
                    print "\n >>> Pipeline output directory found"
          except IndexError:
                    print "\n >>> Pipeline output directory doesn't exist checking for tarball weblog"

                    try:
                              tarPipelineFolder=glob.glob(mem_wd+'/qa/*.weblog.tar.gz')[0]
                              print "\n >>> Tarball weblog  hasn't been untarred yet... untarring"
                              os.system('tar xvfz '+mem_wd+'/qa/*.weblog.tar.gz -C '+mem_wd+'/qa')
                              pipelineFolder=glob.glob(mem_wd+'/qa/pipeline-*')[0]
                              print "\n >>> Pipeline output directory untarred"
                    except IndexError:
                              sys.exit("\n >>> No listobs.txt found for raw MS found in:\n\n"+mem_wd+"/qa/\n\n >>> Bailing out!")

          rawListobs=[]
          for MSs in TsysTables:
                    MS_uid=re.split('\.',re.split('/',MSs)[-1])[0] # A messy regex to jsut get the uid name for each relavent Tsys table to look for corresponding listobs
                    try:
                              thisListobs=glob.glob(pipelineFolder+'/html/sessionsession_*/'+MS_uid+'.ms/listobs.txt')[0]
                              print thisListobs
                    except IndexError:
                              sys.exit("\n >>> No listobs.txt found for raw MS"+MS_uid+"\n >>> Bailing out!")

          return TsysTables, thisListobs

def numpyToSPWString(SPW,arr):
        SPWstring=str(SPW)+':'    
        for v in arr:
                SPWstring+=str(v)+';'

        SPWstring=SPWstring[:-1]#chop off the trailing semicolon
        return SPWstring
