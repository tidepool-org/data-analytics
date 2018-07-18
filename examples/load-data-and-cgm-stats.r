####################################################################################
# description: Example for loading Tidepool data and calculating cgm stats in R
# version: 0.0.1
# created: 2018-07-17
# author: Jason Meno
# license: BSD-2-Clause
####################################################################################


# Set location of data
dataPath = file.path("..","example-data")

# load csv data
data = read.csv(file.path(dataPath,
                       "example-from-j-jellyfish.csv"),
                       stringsAsFactors = FALSE)

# View the first 5 rows of data
head(data)

# Get a list of all data columns
colnames(data)

# Get the unique data types
unique(data$type)

# get just the cgm data
cgm = data[data$type=="cbg",]

# look at the first 5 rows of data
head(cgm)

# rename "value" field to "mmol_L"
colnames(cgm)[colnames(cgm)=="value"] = "mmol_L"

# convert mmol/L to mg/dL and create a new field
cgm$mg_dL = as.integer(cgm$mmol_L * 18.01559)

# view the cgm mg/dL data
head(cgm$mg_dL)

# define a function that captures the Ambulatory Glucose Profile statistics
# http://www.agpreport.org/agp/agpreports#CGM_AGP
get_stats = function(df){
    
    statsDF = data.frame(matrix(nrow=1,ncol=0))
    
    totalNumberCBGValues = length(df$mg_dL)
    statsDF$totalCgmValues = totalNumberCBGValues
    
    df$deviceTime = as.POSIXct(df$deviceTime,format="%Y-%m-%dT%H:%M:%S")
    firstDataPoint = min(df$deviceTime)
    lastDataPoint = max(df$deviceTime)
    
    if(grepl("FreeStyle", df$deviceId[1])==TRUE){
        dataFrequency = 15
    }else{
        dataFrequency = 5
    }
     
    totalPossibleCgmValues = round(as.integer(difftime(lastDataPoint, 
                                    firstDataPoint,
                                    units="min"))/dataFrequency)

    
    statsDF$totalPossibleCgmReadings = totalPossibleCgmValues
        
    statsDF$percentOfPossibleCgmReadings = 
                   totalNumberCBGValues / totalPossibleCgmValues
    
    statsDF$firstDataPoint = firstDataPoint 
    statsDF$lastDataPoint = lastDataPoint
    statsDF$daysOfCgmData = as.integer(
            difftime(as.Date(lastDataPoint), 
                     as.Date(firstDataPoint),
                     units="days"))
      
    mean_mgdL = mean(df$mg_dL)
    statsDF$mean_mgdL = mean_mgdL
    
    std_mgdL = sd(df$mg_dL)
    statsDF$std_mgdL = std_mgdL
    
    cov_mgdL = std_mgdL / mean_mgdL
    statsDF$cov_mgdL = cov_mgdL
    
    totalBelow54 = sum(df$mg_dL < 54)
    statsDF$percentBelow54 = totalBelow54 / totalNumberCBGValues
    
    totalBelow70 = sum(df$mg_dL < 70)    
    statsDF$percentBelow70 = totalBelow70 / totalNumberCBGValues
    
    total70to180 = sum((df$mg_dL >= 70) & (df$mg_dL <= 180))    
    statsDF$percentTimeInRange = total70to180 / totalNumberCBGValues
    
    totalAbove180 = sum(df$mg_dL > 180)
    statsDF$percentAbove180 = totalAbove180 / totalNumberCBGValues
    
    totalAbove250 = sum(df$mg_dL > 250)
    statsDF$percentAbove250 = totalAbove250 / totalNumberCBGValues

    statsDF$min_mgdL = min(df$mg_dL)
    statsDF$`10%` = quantile(df$mg_dL,0.10)
    statsDF$`25%` = quantile(df$mg_dL,0.25)
    statsDF$median = quantile(df$mg_dL,0.50)
    statsDF$`75%` = quantile(df$mg_dL,0.75)
    statsDF$`90%` = quantile(df$mg_dL,0.90)
    statsDF$max_mgdL = max(df$mg_dL)

    # get estimated HbA1c or Glucose Management Index (GMI)
    # GMI(%) = 3.31 + 0.02392 x [mean glucose in mg/dL]
    # https://www.jaeb.org/gmi/
    statsDF$GMI = 3.31 + (0.02392 * mean_mgdL)
    
    return(statsDF)
    
}

# apply function to get stats
cgmStats = get_stats(cgm)
t(cgmStats)
