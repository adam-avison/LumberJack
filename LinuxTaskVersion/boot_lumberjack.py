import os
import re
cwd = os.getcwd()

f = open('lumberjack_cli.py','r')
f2 = open('lumberjack_cli2.py','w')
print ">> Updating lumberjack_cli.py to lumberjack_cli2.py"
for line in f.readlines():
    if line.lstrip().startswith('pathname'):
        print >> f2, re.split('p',line)[0]+'pathname="file://'+cwd+'/"'
    else:
        print >> f2, line.rstrip()
    
f.close()
f2.close()


f3 = open('load_lumberjack.py','r')
f4 = open('load_lumberjack2.py','w')
print ">> Updating load_lumberjack.py to load_lumberjack2.py"
for line in f3.readlines():
    if line.startswith('if sys.path[1]'):
        print >> f4, re.split('=', line)[0]+'= \''+cwd+'\':'
    elif line.startswith('  sys.path.insert'):
        print >> f4, re.split(',', line)[0]+', \''+cwd+'\')'
    elif line.startswith('task_location'):
        print >> f4, re.split('=', line)[0]+'= \''+cwd+'\''
    else:
        print >> f4, line.rstrip()
    
f3.close()
f4.close()



execfile('load_lumberjack2.py')


