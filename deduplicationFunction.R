StringConvert <- function(x, y, alpha.Size){
  #
  # Coverts two vectors string equivalent
  # Args:
  #   x:vector value for uploadid x 
  # y:vector value for uploadid y
  # alpha.Size: Alphabet size.
  # Returns:
  #   longeststring:longest common substring match between discretized value of x and y respectively stringX,stringY
  # percentage similarity between vector x and y
  if (length(x) != length(y)){
    normvalue = x
  }
  else if(length(x) == length(y)){
    normvalue = x
  }
  normvalue.Mean <- mean(normvalue)
  normvalue.Dev <- sd(normvalue)
  xnormalized <- (x - normvalue.Mean) / normvalue.Dev
  ynormalized <- (y - normvalue.Mean) / normvalue.Dev
  X.PAA = paa(xnormalized, length(x)) 
  y.PAA = paa(ynormalized,  length(y))
  xString.Value <- series_to_string(X.PAA, alpha.Size)
  yString.Value <- series_to_string(y.PAA, alpha.Size) 
  stringX <- xString.Value
  stringY <- yString.Value
  longeststring<-LCSn(c(stringX,stringY))
  return (list(longeststring, stringX, stringY, (levenshteinSim(xString.Value, yString.Value))))
}


IndexRange<- function(values){
  #computes the range of matching character between string values and common subsequence
  # Args:
  #   values:output from stringcnvert function 
  # Returns:
  #   Loc:Matching Ranges
  strings.Values <- as.character(c(values[2],values[3]))
  common.SubSequence <- as.character(values[1])
  loc <- str_locate(strings.Values, common.SubSequence)
  return(list(loc))
}


ExtractDuplicateIndex <- function(x, y, IndexRange){
  ##computes the duplicated values for each vectors and their indexes 
  # Args:
  #   x & y: vectors
  # Returns:
  #   duplicated.X:duplicated value for vextor x
  # duplicated.Y:duplicated value for vextor y
  # index.X:duplicated values index for vector x
  # index.Y:duplicated values index for vector y
  duplicate.X <- x[IndexRange[[1]][1,][1] : IndexRange[[1]][1,][2], "value"]
  duplicate.Y <- y[IndexRange[[1]][2,][1] : IndexRange[[1]][2,][2], "value"]
  index.X <- row.names(x[IndexRange[[1]][1,][1] : IndexRange[[1]][1,][2],])
  index.Y <- row.names(y[IndexRange[[1]][2,][1] : IndexRange[[1]][2,][2],])
  return(list(duplicate.X, duplicate.Y, index.X, index.Y))
}


ExtractVectorIndex<- function(x){
  ##computes a list of indexes 
  # Args:
  #   x: vectors
  # Returns:
  #   duplicate.Index:duplicated value index
  for (i in 1:length(x))
    indexnum <- c(x[[i]]) 
  duplicate.Index<-as.numeric(indexnum)
  return(duplicate.Index)
}