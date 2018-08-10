import numpy as np
import pandas as pd

"""
Data Deduplication of Continous blood glucose. Final output are indexes of duplications, duplicated values and a plot of the values
"""
#Section one
"""
Test data comparing two uploadid's
files:0289cfb8bd6d61ccf1f31c07aa146b7b14f0eb74474be4311860d9d77dd30f15.csv
      0fe539475b52ae23f939d7dd2596cf8eb1e877edcea0478f2df73bb98bd5937c.csv
"""
##data = pd.read_csv("C:/Python27/test2.csv",delimiter=',')
##df1=data.loc[data['alp'] =='x', ['value']]
##df2=data.loc[data['alp'] =='y', ['value']]


data = pd.read_csv("C:/Users/Amenze/Desktop/tidepool/refdata/data.csv",delimiter=',')
##df1 = data.loc[data['uploadId'] =='upid_3c41703c2d3a8b97f479afdb6ccf799f', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='upid_3fc32e5ad912a8ea7efced9151804bdb', ['utcTime','value']]


##df1 = data.loc[data['uploadId'] =='upid_17db2d2a0ae0e02a12c0a5067e5fe85b', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='upid_5fad608cf32bd03a1cd56e3bb1fdb834', ['utcTime','value']]


df1 = data.loc[data['uploadId'] =='upid_5fad608cf32bd03a1cd56e3bb1fdb834', ['utcTime','value']]
df2 = data.loc[data['uploadId'] =='upid_830c6de3e2ecbbec6fbad0cecc64bdf5', ['utcTime','value']]



##data=pd.read_csv("C:/Users/Amenze/Desktop/tidepool/refdata/duplicated0fe539475b52ae23f939d7dd2596cf8eb1e877edcea0478f2df73bb98bd5937c2.csv",delimiter=',')
##df1 = data.loc[data['uploadId'] =='2f61322480c841fd8679fe81e94930b2', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='c05970591b404518a1cbd64595d628e5', ['utcTime','value']]




def distances(x,y):
   """
   input:
   x & y: vectors of cbg values

   output
   distance matrix of x and y
   """
   if len(y)>len(x):
      leny=len(y)
      lenx=len(x)
      xval=x
      yval=y
   elif len(x)>len(y):
      leny=len(x)
      lenx=len(y)
      xval=y
      yval=x
   elif len(y)==len(x):
      lenx=len(x)
      leny=len(y)
      xval=x
      yval=y
   distances= [[0] * lenx for i in range(leny)]
   for i in range(leny):  
     for j in range(lenx):   
         distances[i][j] = ((xval[j])-(yval[i]))**2
   return distances


def lstdiagonal(dis):
   """
   input
    dis: distance matrix
   output:generate a list of diagonals
     a:the diagonal array with max sum of zeroes.
     w: start index
   """
   matrix=np.array(dis)
   j=-len(dis)
   x=len(dis[0])+1
   longest_match=0
   for i in range(len(dis[0])-1,j,-1): 
       arr=matrix.diagonal(i)
       nbr_zero=(arr == 0).sum()
       if nbr_zero >= longest_match:
          longest_match = nbr_zero
          a=arr
          w=abs(i)
   return (a,w)





def diagonalzero(df,ts1,ts2,startindex):
   '''
   df: distance matrix
   ts1:vector 1
   ts2:vector 2
   startindex: the start index for the diagonal
   ouput: returns all values  and index in diagonals with max zeroes
   '''
   diaindex=[]
   diaval=[]
   if len(ts2)>len(ts1):
      leny=len(ts2)
      j=len(ts1)-1
   elif len(ts1)>len(ts2):
      leny=len(ts1)
      j=len(ts2)-1
   elif len(ts1)==len(ts2):
      lenx=len(ts1)
      leny=len(ts2)
      j=len(ts1)-1
   i=startindex
   k=0
   while i<leny and k<=j:
       if df[i][k]>=0:
          diaindex+=[[i,k]]
          diaval+=[df[i][k]]  
          k=k+1
          i=i+1  
   return (diaindex,diaval)



def zero_runs(a): #https://stackoverflow.com/questions/24885092/finding-the-consecutive-zeros-in-a-numpy-array
   """
   a: array output from diagonal zero
   output:
    Return the consecutive zero in the array
   """
   iszero = np.concatenate(([0], np.equal(a, 0).view(np.int8), [0]))
   absdiff = np.abs(np.diff(iszero))
   ranges = np.where(absdiff == 1)[0].reshape(-1, 2)
   return ranges


def countzero(runs):
   """
    runs: list of start and stop index of the consecutive zeros in an array
    output:returns the start and stop index with max zeroes
    ind: the index of the result within runs list
     
   """
   maxcount=0
   for i in  range(len(runs)):
        x=runs[i][1]-runs[i][0]
        if x>=maxcount:
            maxcount=x
            ind=i
   count=maxcount
   return count,ind


def zeroindex(runs,dia,runindex):
    '''
    dia:diagonal indexes returned from function diagonalzeros
    runs:start and stop indexes
    output"accumulate the indexes of consecutive zero
    the index for the longest zeros"
    '''
    i=runs[0]
    j=runs[1]
    indexlst=[]
    for i in range(i,j):
       indexlst+=[dia[i]]

    return indexlst



def dupindex(x,y,diagonalzero):
    """
    x & y : vectors
    diagonalzero:Output from function zeroindex
     output
     line upindexes for vector x and y and the duplicate values
    """
    yvalue=[]
    xvalue=[]
    xdup=[]
    ydup=[]
    if len(y)>len(x):
       yval=y
       xval=x
    elif len(x)>len(y):
      xval=y
      yval=x
    elif len(y)==len(x):
      xval=x
      yval=y
    for i in range(len(diagonalzero)):
       yvalue+=[diagonalzero[i][0]]
    yindex=yvalue
    for i in range(len(diagonalzero)):
       xvalue+=[diagonalzero[i][1]]
    xindex=xvalue
    for i in range(len(xindex)):
        val=xindex[i]
        xdup+=[xval[val]] 
    ts1dup=xdup
    ts1dup.reverse()
    for i in range(len(yindex)):
        val=yindex[i]
        ydup+=[yval[val]]
    ts2dup=ydup
    ts2dup.reverse()
    return(xindex,yindex,ts1dup,ts2dup)
   
def lookupdict(x):
   """
   x: vactor
   output: a dictionary holding the original indexes of vector
   """
   indexdict={}
   for i in range(len(x)):
       indexdict[i]=x[i]
   return indexdict


##retrieve original index
def original(xval,yval,xind,yind):
   """
   input:
   xval & yval: dictionary from function lookupdict
   xind $ yind: line up indexes
   output: return a list of original duplicate indexes
   """
   xlist=[]
   ylist=[]
   if len(yind) > len(xind):
      y=yind
      x=xind
   elif len(xind)>len(xind):
      y=xind
      x=yind
      xdict=x
   elif len(xind)==len(yind):
      y=yind
      x=xind
   if len(yval)>len(xval):
      xdict=xval
      ydict=yval
   elif len(xval)> len(yval):
       xdict=yval
       ydict=xval
   elif len(xval)==len(yval):
      xdict=xval
      ydict=yval
   for i in xind:
        xlist+=[xdict[i]]
   for i in yind:
        ylist+=[ydict[i]]
   xlist.reverse()
   ylist.reverse()
   return (xlist,ylist)
     


###main###
print "--------------vector one and two--------------------------"
ts1=np.array(df1['value'])
ts2=np.array(df2['value'])

##print "--------------original index for vector one and two--------------------------------------"
ts1index= df1.index
print "-----------------"
print ts1index
 
ts2index=df2.index
print ts2index
####
print "--------------------distance matrix---------------------"
dis=distances(ts1,ts2)
###print dis
##
print "----------------list of diagonals ---------------------------------------------"
arr,index=lstdiagonal(dis)
startindex=index
zeroarr=arr
#print startindex
#print zeroarr
      
print "---------------diagonal index with zero---------------------------------------"
diaindex,diaval= diagonalzero(dis,ts1,ts2,startindex)
diavals=diaval
diaindexes=diaindex
#print diavals
#print diaindexes

runs=zero_runs(diavals)

print "---list of indexes---"
#print runs
print "----maximum count of zero-------------------------------------"
sumzero,i=countzero(runs)
sumindex=i
maxruns=runs[sumindex]
#print maxruns
#print "***********"
#print sumindex

zeroruns=sumzero
#print zeroruns
######
diazero=zeroindex(maxruns,diaindexes,sumindex)
####
#print diazero
xindex2,yindex2,ts1value,ts2value=dupindex(ts1,ts2,diazero)
######
xindex=xindex2
yindex=yindex2
duplicatedts1=ts1value
duplicatedts2=ts2value
##print xindex
##print yindex
print duplicatedts1
##print"-----------------------------------------------------------------------------"
print duplicatedts2
####
import matplotlib.pyplot as plt
plt.subplot(2, 1, 1)
plt.plot(duplicatedts1,'r-')
plt.ylabel('upid_3c41703c2d3a8b97f479afdb6ccf799f cbg')
plt.subplot(2, 1, 2)
plt.plot(duplicatedts2)
plt.ylabel('upid_3fc32e5ad912a8ea7efced9151804bdb cbg')

plt.show()
print "-----------dictionary for original index--------------------------------------------------"  
originalts1=lookupdict(ts1index)
originalts2=lookupdict(ts2index)
print originalts1
print originalts2


print "--------------match to original index-------------------------"
print original(originalts1,originalts2,xindex,yindex) 

