![LJ Logo](https://github.com/adam-avison/LumberJack/blob/master/figures/LJ_Logo_small.png "LJ Logo")
# LumberJack
CASA task and associated scripts/functions to find spectral line free channels in ALMA data.

## STATUS: LumberJack being updated week of 24-Aug-2020

## Release Notes:
LumberJack is now available as:
 - A full CASA task which works in CASA 5.6+ on both MacOS and under Linux.
 - A Lite version. The Lite version is a Python script to be run the same directory as the target data.
 
## Download
### Task version
 - [macOS Version for CASA 5.6.x](https://github.com/adam-avison/LumberJack/blob/master/LumberJackTask_MacVersion.tar) 
 - [Linux Version for CASA 5.6.x](https://github.com/adam-avison/LumberJack/blob/master/LumberJackTask_LinuxVersion.tar)

## Build 
### Task versions
#### macOS
1. Download the Mac Version tar file above.
2. Untar with `tar xvf LumberJackTask_MacVersion.tar` and `cd` into the resultant directory.
3. `cd` again into the Functions/ directory. You will need to set the parameter auPath in the scripts calcFuncs.py (line 5) and measFuncs.py (line 13) to the location of the CASA analysis utilities on your machine. Analysis Utils can be downloaded from: https://casaguides.nrao.edu/index.php/Analysis_Utilities 
4. Start your local version of CASA (should be 5.6+, not yet tested in 5.7 or 6.x).
5. At the CASA prompt:
```python
CASA <1>: !buildmytasks
CASA <2>: execfile('mytasks.py')
```
6. You are good to go. To confirm everything is working you can try:
```python
CASA <3>: inp lumberjack
```
which should give you:
```python
--------> inp(lumberjack)
#  lumberjack :: Find line free channels to exclude in continuum imaging.
vis                 =         ''        #  name of input visibility file
spw                 =         ''        #  Spectral window
field               =         ''        #  Field Name
secsour             =         ''        #  File with positions and properties of
                                        #   Secondary Sources
stddevfact          =         ''        #  Standard deviation factor
```
#### Linux
1. Download the Linux Version tar file above.
2. Untar with `tar xvf LumberJackTask_LinuxVersion.tar` and `cd` into the resultant directory.
3. `cd` again into the Functions/ directory. You will need to set the parameter auPath in the scripts calcFuncs.py (line 5) and measFuncs.py (line 13) to the location of the CASA analysis utilities on your machine. Analysis Utils can be downloaded from: https://casaguides.nrao.edu/index.php/Analysis_Utilities 
4. Start your local version of CASA (should be 5.6+, not yet tested in 5.7 or 6.x).
5.  At the CASA prompt:
```python
CASA <1>: execfile('boot_lumberjack.py')
```
6. You are good to go. To confirm everything is working you can try:
```python
CASA <2>: inp lumberjack
```
which should give you:
```python
--------> inp(lumberjack)
#  lumberjack :: Find line free channels to exclude in continuum imaging.
vis                 =         ''        #  name of input visibility file
spw                 =         ''        #  Spectral window
field               =         ''        #  Field Name
secsour             =         ''        #  File with positions and properties of
                                        #   Secondary Sources
stddevfact          =         ''        #  Standard deviation factor
```
---
### Lite version
Coming soon...

---
## Use in CASA
### Task versions
Once built LumberJack will act like any other CASA task and input parameters and help can be sought with the CASA `inp()` and `help()` commands.

#### Input Parameters 
LumberJack's input parameters are:
    
    - `msname`: Name of CASA measurement set.
    - `spw`: Spectral Window Number (only one SPW can be analysed at a time).
    - `field`: Name of target field within the measurement set (or name of object for mosaic observations).
    - `secsour`: A secondary Source file with file extension .txt [optional, (see below for more details) on formatting].
    - `stddevfactor`: A standard deviation factor to cut off sigma clipping [optional].

#### Data Location
In the directory you are running LumberJack you will need:

- [Optional] The list of sources in the field, as defined in the `secsour` parameter. This file should be named `<field>+_SecondarySources.txt`.
The format of this file is:

 ```
 sourceX     RA[hh:mm:ss.000]    Dec[dd:mm:ss.000]   Bmaj*   Bmin*   BPA*
 ```
 * Where Bmaj, Bmin and BPA are fitted 2D Gaussian major, minor axis and position angle.

#### Output
1. If parameter `secsour` is empty LumberJack finds line free channels at the location of the peak pixel in the given field and SPW. The output in the mode is given as a .txt file named `<field>_SourceX_SPW_<SPW>_LineFreeChans.txt`. 

    This contains the line free channels at the peak flux density position in that field. 
    The line free channels are given in CASA SPW syntax: e.g.
    `25:1~30;33~81;84~526;544~591;594~1760;1783~1852;1856~1868;1871~1898;1901~1917`.

2. If using a secondary sources file (`secsour` value set):

    For each source listed in `<field>+_SecondarySources.txt` LumberJack will output:

    - An output txt file named <target_name>_sourceNo_<#>_SPW_<SPW>_LineFreeChans.txt. This contains the line free channels at that position.
    - Two PNG images:
         1. `<field>_sourceNo_<#>_SPW_<SPW>_lineFree.png` which shows the spectrum and line free channels at that position
         2. `<field>_sourceNo_<#>_SPW_<SPW>_gaussPlot.png` which shows a histogram of the flux values of line free channels.

    The final usable out put in this mode is the .txt file named `<field>_allSource_SPW_<SPW>_LineFreeChans.txt` which combines the values from each source and 'chunks' them in to the CASA SPW string syntax. e.g. 
    `25:1~30;33~81;84~526;544~591;594~1760;1783~1852;1856~1868;1871~1898;1901~1917`.
---
### Lite version
Coming soon...

---
