# LumberJack ![LJ Logo](https://github.com/adam-avison/LumberJack/tree/master/figures/LJ_Logo.png)
CASA task and associated scripts/functions to find spectral line free channels in ALMA data.

## STATUS: LumberJack being updated week of 24-Aug-2020

## Release Notes:
LumberJack is now available as:
 - A full CASA task which works in CASA 5.6+ on both MacOS and under Linux.
 - A Lite version. The Lite version is a Python script to be run the same directory as the target data.
 
## Download
Coming soon...
 
## Usage
### Task version
#### To build Mac Version
1. Download the Mac Version tar file above.
2. Untar with `tar xvf MacVersion.tar` and `cd` into the resultant directory.
3. Start your local version of CASA (should be 5.6+, not yet tested in 5.7 or 6.x).
4. At the CASA prompt:
```python
CASA <1>: !buildmytasks
CASA <2>: execfile('mytasks.py')
```
5. You are good to go. To confirm everything is working you can try:
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
#### To build Linux Version
Coming soon...

___

### Lite version
