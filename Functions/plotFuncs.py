import matplotlib.pyplot as plt

def testPlots(x,y,col,mar='',lin='-',figNo=1):
    fig = plt.figure(figNo, figsize=[7,7])
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(x,y,color=col,linestyle=lin,marker=mar)
    #plt.show()
