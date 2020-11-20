#
# User defined tasks setup.
# Generated from buildmytask.
#

if sys.path[1] != '/raid1/scratch/aavison/LJ_2020':
  sys.path.insert(1, '/raid1/scratch/aavison/LJ_2020')
from odict import odict
if not globals().has_key('mytasks') :
  mytasks = odict()

mytasks['lumberjack'] = 'Find line free channels to exclude in continuum imaging.'

if not globals().has_key('task_location') :
  task_location = odict()

task_location['lumberjack'] = '/raid1/scratch/aavison/LJ_2020'
import inspect
#myglobals = sys._getframe(len(inspect.stack())-1).f_globals
from casa_stack_manip import stack_frame_find
myglobals_x = stack_frame_find( )  
myglobals_y = sys._getframe(len(inspect.stack())-1).f_globals

myglobals = myglobals_x.copy()
myglobals.update(myglobals_y) 

tasksum = myglobals['tasksum'] 
for key in mytasks.keys() :
  print key
  tasksum[key] = mytasks[key]

from lumberjack_cli2 import  lumberjack_cli as lumberjack
