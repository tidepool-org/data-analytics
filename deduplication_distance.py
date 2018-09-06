import numpy as np
import pandas as pd
"""
Data Deduplication of Continous blood glucose. Final output are indexes of duplicated values, duplicated values and a plot of the values
"""
"""
Test data  from two files
files:0289cfb8bd6d61ccf1f31c07aa146b7b14f0eb74474be4311860d9d77dd30f15.csv
      0fe539475b52ae23f939d7dd2596cf8eb1e877edcea0478f2df73bb98bd5937c.csv
"""
#Test data1
##data = pd.read_csv("C:/Python27/test2.csv",delimiter=',')
##print data
##df1=data.loc[data['alp'] =='x', ['value']]
##df2=data.loc[data['alp'] =='y', ['value']]
#Test data2
#data = pd.read_csv("C:/Users/Amenze/Desktop/tidepool/refdata/data.csv",delimiter=',')
##df1 = data.loc[data['uploadId'] =='upid_3c41703c2d3a8b97f479afdb6ccf799f', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='upid_3fc32e5ad912a8ea7efced9151804bdb', ['utcTime','value']]
#Test data3
##df1 = data.loc[data['uploadId'] =='upid_17db2d2a0ae0e02a12c0a5067e5fe85b', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='upid_5fad608cf32bd03a1cd56e3bb1fdb834', ['utcTime','value']]
#Test data4
##df1 = data.loc[data['uploadId'] =='upid_5fad608cf32bd03a1cd56e3bb1fdb834', ['utcTime','value']]
##df2 = data.loc[data['uploadId'] =='upid_830c6de3e2ecbbec6fbad0cecc64bdf5', ['utcTime','value']]

#Test data5
data=pd.read_csv("C:/Users/Amenze/Desktop/tidepool/refdata/duplicated0fe539475b52ae23f939d7dd2596cf8eb1e877edcea0478f2df73bb98bd5937c2.csv",delimiter=',')
df1 = data.loc[data['uploadId'] =='2f61322480c841fd8679fe81e94930b2', ['utcTime','value']]
df2 = data.loc[data['uploadId'] =='c05970591b404518a1cbd64595d628e5', ['utcTime','value']]

def Distances(x,y):
   """
   Compute the distance matrix for vector x and y
   Args:
    x:vector value for uploadid x 
    y:vector value for uploadid y
   Returns:
     distances: distance matrix of x and y
   """
   if len(y) > len(x):
      leny = len(y)
      lenx = len(x)
      xval = x
      yval = y
   elif len(x) > len(y):
      leny = len(x)
      lenx = len(y)
      xval = y
      yval = x
   elif len(y) == len(x):
      lenx = len(x)
      leny = len(y)
      xval = x
      yval = y
   distances= [[0] * lenx for i in range(leny)]
   for i in range(leny):  
     for j in range(lenx):   
         distances[i][j] = ((xval[j])-(yval[i]))**2
   return distances

def DiagonalList(dis):
   """
   Find the diagonal with the highest count of zero  and the diagonal start index
   Args:
    dis: distance matrix
   Returns:
     diagonal: diagonal with higest count of zero
     diagonalStartIndex:Start Index of diagonal
   """
   matrix=np.array(dis)
   j=-len(dis)
   x=len(dis[0])+1
   highestCount=0
   for i in range(len(dis[0])-1,j,-1): 
       arr = matrix.diagonal(i)
       countZero = (arr == 0).sum()
       if countZero >= highestCount:
          highestCount = countZero
          diagonal=arr
          diagonalStartIndex=abs(i)
   return (diagonal,diagonalStartIndex)

def DiagonalZero(disMatrix,ts1,ts2,startindex):
   """
   Compute the diagonal Index with the highest count of zero (output from DiagonalList)
   Args:
    disMatrix: distance matrix
    ts1:Vector 1
    ts2:vector 2
    startindex: the start index for the diagonal
   Returns:
     dia.Index:diagonal Index
     dia.value: diagonal value
   """
   diaIndex=[]
   diaValue=[]
   if len(ts2) > len(ts1):
      leny = len(ts2)
      j = len(ts1)-1
   elif len(ts1) > len(ts2):
      leny = len(ts1)
      j = len(ts2)-1
   elif len(ts1) == len(ts2):
      lenx = len(ts1)
      leny = len(ts2)
      j = len(ts1)-1
   i = startindex
   k = 0
   while i < leny and k <= j:
       if disMatrix[i][k] >= 0:
          diaIndex += [[i,k]]
          diaValue += [disMatrix[i][k]]  
          k = k+1
          i = i+1  
   return (diaIndex,diaValue)

def zero_runs(diaValue): #https://stackoverflow.com/questions/24885092/finding-the-consecutive-zeros-in-a-numpy-array
   """
   Args:
   diaValue: diagonal values returned from function diagonalzero
   Returns:
    ranges: list of consecutive zero ranges in the diagonal
   """
   iszero = np.concatenate(([0], np.equal(diaValue, 0).view(np.int8), [0]))
   absdiff = np.abs(np.diff(iszero))
   ranges = np.where(absdiff == 1)[0].reshape(-1, 2)
   return ranges
def CountZero(runs):
   """
   Args:
    runs: list of start and stop index of the consecutive zeros in an array
   Returns:
    totalCount:returns the count of consecutive zero
    countIndex:list index with max zeros
   """
   maxcount=0
   for i in  range(len(runs)):
        count=runs[i][1]-runs[i][0]
        if count>=maxcount:
            maxcount=count
            countIndex=i
   totalCount=maxcount
   return (totalCount,countIndex)


def ZeroIndex(runs,dia,runindex):
    """
   #accumulate indexes  
    Args:
      dia:diagonal indexes returned from function DiagonalZero
      runs:start and stop indexes
   Results:
     indexlst: list of indexes
    """
    i=runs[0]
    j=runs[1]
    indexlst=[]
    for i in range(i,j):
       indexlst+=[dia[i]]

    return indexlst

def DupIndex(x,y,indexzero):
    """
    Args:
    x & y : vectors
    indexzero:Output from function zeroindex
    Result:
     xindex& yindex:matrix indexes for vector x and y
     ts1dup &ts2dup: duplicated values
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
    for i in range(len(indexzero)):
       yvalue+=[indexzero[i][0]]
    yindex=yvalue
    for i in range(len(indexzero)):
       xvalue+=[indexzero[i][1]]
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
   Args:
     x: vector
   Returns:
     indexDict: a dictionary holding the original indexes of vector
   """
   indexDict={}
   for i in range(len(x)):
       indexDict[i]=x[i]
   return indexDict

def ExtracteIndex(xDict,yDict,xIndex,yIndex):
   """
   Args:
      xDict & yDict: dictionary from function lookupdict
      xIndex $ yIndex: line up indexes
   Returns:
    xIndexList,yIndexList: a list of original duplicate indexes
   """
   xIndexList=[]
   yIndexList=[]
   if len(yIndex) > len(xIndex):
      y=yIndex
      x=xIndex
   elif len(xIndex)>len(yIndex):
      y=xIndex
      x=yIndex
     # x.Dict=x
   elif len(xIndex)==len(yIndex):
      y=yIndex
      x=xIndex
   if len(yDict)>len(xDict):
      xdict=xDict
      ydict=yDict
   elif len(xDict)> len(yDict):
       xdict=yDict
       ydict=xDict
   elif len(xDict)==len(yDict):
      xdict=xDict
      ydict=yDict
   for i in xIndex:
        xIndexList+=[xdict[i]]
   for i in yIndex:
        yIndexList+=[ydict[i]]
   xIndexList.reverse()
   yIndexList.reverse()
   return (xIndexList,yIndexList)
import time
start_time = time.time()
     
###main###
print "--------------vector one and two--------------------------"
ts1=np.array(df1['value'])
ts2=np.array(df2['value'])

print "--------------original index for vector one and two--------------------------------------"
ts1index= df1.index
print "-----------------"
#print ts1index
 
ts2index=df2.index
#print ts2index
####
print "--------------------distance matrix---------------------"
dis=Distances(ts1,ts2)
#print dis
##
print "----------------list of diagonals ---------------------------------------------"
arr,index=DiagonalList(dis)
startindex=index
zeroarr=arr
#print startindex
#print zeroarr
      
print "---------------diagonal index with zero---------------------------------------"
diaindex,diaval= DiagonalZero(dis,ts1,ts2,startindex)
diavals=diaval
diaindexes=diaindex
#print diavals
#print diaindexes

runs=zero_runs(diavals)

print "---list of indexes---"
#print runs

print "----maximum count of zero-------------------------------------"
sumzero,i=CountZero(runs)
sumindex=i
#print sumindex
maxruns=runs[sumindex]
#print maxruns
zeroruns=sumzero
#print zeroruns
print "*******************"
######
diazero=ZeroIndex(maxruns,diaindexes,sumindex)
####
#print diazero
xindex2,yindex2,ts1value,ts2value=DupIndex(ts1,ts2,diazero)
######
xindex=xindex2
yindex=yindex2
duplicatedts1=ts1value
duplicatedts2=ts2value
#print xindex
#print yindex
print duplicatedts1
print"-----------------------dup1------------------------------------------------------"
print duplicatedts2

print "-----------dictionary for original index--------------------------------------------------"  
originalindexts1=lookupdict(ts1index)
originalindexts2=lookupdict(ts2index)
#print originalindexts1
#print originalindexts2


print "--------------match to original index-------------------------"
print ExtracteIndex(originalindexts1,originalindexts2,xindex,yindex) 

print time.time() - start_time, "seconds"

##
import matplotlib.pyplot as plt
plt.subplot(2, 1, 1)
plt.plot(duplicatedts1,'r-')
plt.ylabel('vector x')
plt.subplot(2, 1, 2)
plt.plot(duplicatedts2)
plt.ylabel('vector y')

plt.show()
