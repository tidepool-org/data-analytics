
################################################################################################
#
# This code demonstrates the basic trend analysis of Tidepool data sets
#
# Special focus is given to carb intake and daily BG effects
#
################################################################################################

library(data.table)
library(lubridate)


##### Import Custom Fonts #####

font_import(paths="A:/Fonts")
#font_import(paths = NULL, recursive = TRUE, prompt = TRUE,pattern = NULL)

##### Data Collection Filtering Options #####

# Set a minimum # of days available for each file
# Files with less than this will be skipped
minimum_days = 14

# Set a minimum # of daily carb entries for each day
# Days with less than this will be skipped
minimum_carb_entries = 3

# Set a minimum % of cgm data points for each day
# Days with less than this will be skipped
minimum_cgm_percentage = 80
minimum_cgm_points = round(288*minimum_cgm_percentage/100)

# Set the time when a day starts/ends
daily_hour_start = 6

################ End Options ################
  
#Import file metadata
setwd("YOUR METADATA FILE DIRECTORY")
metaData = read.csv("YOUR_METADATA_FILENAME.csv", stringsAsFactors = FALSE)

#Use either hashID.csv or PHI-userID.csv
#metaData$hashID = paste(metaData$hashID, ".csv",sep="")
metaData$hashID = paste("PHI-",metaData$userID, ".csv",sep="")

#Set working directory to folder containing data
setwd("YOUR DATA FILE WORKING DIRECTORY")
files = dir()

#Use this files command if you are re-running the program with a specific set of known files
#files = unique(file_tracker)

#Create empty elements to fill from each file
total_daily_carbs = vector(mode="list", length=200000)
all_carb_entries = vector(mode="list", length=200000)
carb_timestamps = vector(mode="list", length=200000)

#Statistical measurements
meanBG = vector(mode="list", length=200000)
medianBG = vector(mode="list", length=200000)
stddevBG = vector(mode="list", length=200000)
daily_range = vector(mode="list", length=200000)
daily_25_75_IQR = vector(mode="list", length=200000)
daily_CV = vector(mode="list", length=200000)
daily_below54 = vector(mode="list", length=200000)
daily_below70 = vector(mode="list", length=200000)
daily_70_180 = vector(mode="list", length=200000)
daily_above180 = vector(mode="list", length=200000)
daily_above250 = vector(mode="list", length=200000)

daily_hypo54_count = vector(mode="list", length=200000)
daily_hypo70_count = vector(mode="list", length=200000)
daily_hyper180_count = vector(mode="list", length=200000)
daily_hyper250_count = vector(mode="list", length=200000)

#Big data structure elements
big.filename = vector(mode="list", length=200000)
big.bg = vector(mode="list", length=200000)
big.timestamp = vector(mode="list", length=200000)
big.carbs = vector(mode="list", length=200000)
big.day = vector(mode="list", length=200000)
big.age = vector(mode="list", length=200000)

#These elements will be used to verify quality of data
daily_cgm_events = vector(mode="list", length=200000)
daily_carb_events = vector(mode="list", length=200000)
file_tracker = vector(mode="list", length=200000)
day_tracker = vector(mode="list", length=200000)
age_tracker = vector(mode="list", length=200000)
diff_time_tracker = vector(mode="list", length=200000)
#mean_insulin_sensitivity = c()

#Run time tracking for console time-to-complete estimate
run_time = c()

#Loop through each file collecting all data and appending to respecting elements.
real_run_start = Sys.time()

#Keep track of skipped file/day counts
skipped_files_no_carbs = 0
skipped_files_no_bg = 0
skipped_files_not_enough_days = 0
skipped_days_not_enough_cgm_data = 0
skipped_days_too_much_cgm_data = 0
skipped_days_not_enough_carb_data = 0

#Keep track of total number of days with carbs and bg entries for each user
user_days_count = c()
current_user_days_analyzed = 0
total_days_analyzed = 0
total_sets_analyzed = 0

#THIS IS THE INDEX FOR ALL LARGE VECTORS
day_num=1

#Set how many files to process
files_to_process = length(files)
#files_to_process = 200


############# Complexity Analsyis Timing Variables ####################
single_full_loop = c()
code_block1 = c()
code_block2 = c()
code_block3 = c()
code_block4 = c()

############## START FILE PROCESSING ##################


for(file_number in 1:files_to_process){
  start_single_full_loop = Sys.time()
  
  start_code_block1 = Sys.time()
  
  #Start time tracking for each file's processing time
  start_time <- Sys.time()
  
  #For all remaining files, estimate time remaining on every 100th file
  if(file_number%%50==0){
    #cat(paste("Files complete: ", toString(file_number), "/", toString(files_to_process)," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:files_to_process])$size))), " min\n", sep="" ))
  }
  
  #Load data
  #data = read.csv(files[file_number], stringsAsFactors = FALSE)
  data = fread(files[file_number],stringsAsFactors=FALSE,verbose=FALSE,showProgress = FALSE)
  data = data.frame(data)
  #Isolate carb and bg data before beginning
  
  #Use "bolus" with anonymized data, "wizard" with PHI data
  #carb_data = data[which(data$type=="bolus"),]
  carb_data = data[which(data$type=="wizard"),]
  bg_data = data[which(data$type=="cbg"),]
  
  #Skip current file if no carb input is available
  if(nrow(carb_data)<=1){
    skipped_files_no_carbs = skipped_files_no_carbs + 1
    next
  }
  
  #Skip current file if no bg input is available
  if(nrow(bg_data)<=1){
    skipped_files_no_bg = skipped_files_no_bg + 1
    next
  }
  
  #Use est.localTime as main datetime metric
  if(!is.null(data$est.localTime)){
    
    #Remove all rows with a est.type method of "UNCERTAIN"
    data = data[which(data$est.type!="UNCERTAIN"),]
    
    #Convert all times into POSIXct data frame
    #Timezone is UTC to overcome internal DST problems
    data$est.localTime = strptime(data$est.localTime,"%Y-%m-%d %H:%M:%S",tz="UTC")
    
    #Add a day column
    data$day = as.character(as.Date(data$est.localTime))
    #Create virtual time frame for comparing "days" as set by the daily_hour_start
    data$virtualTime = data$est.localTime-(daily_hour_start*60*60)
  }
  
  #Optional: Use deviceTime as main datetime metric
  
  #if(!is.null(data$deviceTime)){
  #  #Remove NAs from missing deviceTime rows -- NO don't do this. This will remove healthkit data
  #  data = data[which(data$deviceTime!=""),]
  #
  #  #Convert all times into POSIXct data frame
  #  #Timezone is UTC to overcome internal DST problems
  #  data$deviceTime = strptime(data$deviceTime,"%Y-%m-%dT%H:%M:%S",tz="UTC)
  #
  #  #Create virtual time frame for comparing "days" as set by the daily_hour_start
  #  data$virtualTime = data$deviceTime-(daily_hour_start*60*60)
  #  data$virtualDay = as.character(as.Date(data$virtualTime))
  #}
  
  
  code_block1 = c(code_block1, difftime(Sys.time(),start_code_block1))
  
  start_code_block2 = Sys.time()
  #################### DUPLICATE REMOVAL ###########################
  
  #Sort data by uploadId and upload date (newest to oldest)
  unique_uploadId = unique(data$uploadId)
  upload_dates = vector(mode="list", length=length(unique_uploadId))
  
  #Get associated date of each uploadId
  for(idVal in 1:length(unique_uploadId)){
    upload_dates[[idVal]] = as.POSIXct(data$est.localTime[which(data$uploadId==unique_uploadId[idVal])[1]])
  }
  
  upload_dates = unlist(upload_dates)
  
  ordered_id = unique_uploadId[order(upload_dates,decreasing=TRUE)]
  sorted_data = data[order(factor(data$uploadId,levels=ordered_id)),]
  data = sorted_data
  rm(sorted_data)
  
  #Replace blank deviceTimes (healthkit data)
  #Use a unique value to save healthkit data from duplicated deletion
  data$deviceTime[which(data$deviceTime=="")] = data$id[which(data$deviceTime=="")]
  
  #Remove all duplicated rows based on deviceTime (this will remove duplicated uploads)
  data = data[which(!duplicated(data$deviceTime)), ]
  
  #Sort data by est.localTime (this will remix uploadIds)
  data = data[order(data$est.localTime,decreasing=TRUE), ]
  
  #Split sorted data in carb and bg data
  carb_data = data[which(data$type=="wizard"),]
  bg_data = data[which(data$type=="cbg"),]
  
  #Round all virtual timestamps to nearest 5 minutes
  #There should never be a cgm timestamp less than 5 minutes apart.
  bg_data$virtualTime = round_date(bg_data$virtualTime,"5 minutes")
  
  #Remove duplicated bg timestamps using the new rounded time
  #Reminder: virtualTime is an offset of est.localTime
  bg_data = bg_data[which(!duplicated(bg_data$virtualTime)),]
  
  #Remove rows with empty/0 Carbs and BG
  carb_data = carb_data[!is.na(carb_data$carbInput),]
  carb_data = carb_data[carb_data$carbInput>0,]
  bg_data = bg_data[!is.na(bg_data$value),]
  
  #Round all virtual carb timestamps to the nearest 5 minutes
  carb_data$virtualTime = round_date(carb_data$virtualTime,"5 minutes")
  
  #Add a day column to compare unique daily bg/carb data in virtual timeframe
  carb_data$virtualDay = as.character(as.Date(carb_data$virtualTime))
  bg_data$virtualDay = as.character(as.Date(bg_data$virtualTime))
  
  
  #Set units and their conversion multiplier to "mg/dL" or "mmol/L"
  units = "mg/dL"
  
  if(units=="mg/dL") {
    
    multiplier = 18.01559
    
  } else {
    
    multiplier = 1/18.01559    
    
  }
  
  #Check each BG for appropriate units, and convert if needed
  bg_data$value[which(bg_data$units!=units)]=bg_data$value[which(bg_data$units!=units)]*multiplier
  #carb_data$insulinSensitivity[which(carb_data$units!=units)]=carb_data$insulinSensitivity[which(carb_data$units!=units)]*multiplier
  
  #Find days where both carbs and BG data is available
  unique_bg_days = unique(bg_data$virtualDay)
  unique_carb_days = unique(carb_data$virtualDay)
  days_to_analyze = unique_bg_days[unique_bg_days %in% unique_carb_days]
  
  #Skip file if # of days available is less than the minimum required from the Filter Options
  if(length(days_to_analyze) < minimum_days){
    skipped_files_not_enough_days = skipped_files_not_enough_days + 1
    next
  }
  
  code_block2 = c(code_block2,difftime(Sys.time(),start_code_block2))
  
  start_code_block3 = Sys.time()
  ###### Start day-to-day metric collection for the current file ######
  
  for(i in 1:length(days_to_analyze)){
    
    #Skip day if there is cgm data less than minimum required by Filter Options
    if(length(which(bg_data$virtualDay==days_to_analyze[i])) < minimum_cgm_points){
      skipped_days_not_enough_cgm_data = skipped_days_not_enough_cgm_data + 1
      next
    }
    
    #Skip day if there is bg data longer that 1 day (indicates duplicated data)
    if(length(which(bg_data$virtualDay==days_to_analyze[i])) > 288){
      skipped_days_too_much_cgm_data = skipped_days_too_much_cgm_data + 1
      next
    }
    
    #Skip day if the # of carb entries does not meet the minimum required by Filter Options
    if(length(carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])]) < minimum_carb_entries){
      skipped_days_not_enough_carb_data = skipped_days_not_enough_carb_data + 1
      next
    }
    
    #Store all carb events for this user
    all_carb_entries[[day_num]] = carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])]
    carb_timestamps[[day_num]] = as.character(round_date(carb_data$est.localTime[which(carb_data$virtualDay==days_to_analyze[i])],"5 minutes"))
    
    daily_cgm_events[[day_num]] = length(which(bg_data$virtualDay==days_to_analyze[i]))
    daily_carb_events[[day_num]] = length(which(carb_data$virtualDay==days_to_analyze[i]))
    file_tracker[[day_num]] = files[file_number]
    
    total_daily_carbs[[day_num]] = sum(carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])])
    meanBG[[day_num]] = mean(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    medianBG[[day_num]] = median(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    stddevBG[[day_num]] = sd(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    daily_range[[day_num]] = max(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])-min(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    daily_25_75_IQR[[day_num]] = quantile(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])[3]-quantile(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])[2]
    daily_CV[[day_num]] = 100*sd(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])/mean(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    
    #Tracking time in range
    daily_below54[[day_num]] = 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<54))/length(which(bg_data$virtualDay==days_to_analyze[i]))
    daily_below70[[day_num]] = 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<70))/length(which(bg_data$virtualDay==days_to_analyze[i]))
    daily_70_180[[day_num]] = 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>=70 & bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<=180))/length(which(bg_data$virtualDay==days_to_analyze[i]))
    daily_above180[[day_num]] = 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>180))/length(which(bg_data$virtualDay==days_to_analyze[i]))
    daily_above250[[day_num]] = 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>250))/length(which(bg_data$virtualDay==days_to_analyze[i]))
    
    #Tracking daily number of hypo/hyper episodes
    daily_hypo54_count[[day_num]] = length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<54)))$lengths>=3))
    daily_hypo70_count[[day_num]] = length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<70)))$lengths>=3))
    daily_hyper180_count[[day_num]] = length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>180)))$lengths>=3))
    daily_hyper250_count[[day_num]] = length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>250)))$lengths>=3))
    
    
    total_days_analyzed = total_days_analyzed + 1
    current_user_days_analyzed = current_user_days_analyzed + 1
    age_tracker = c(age_tracker, as.integer(round(difftime(carb_data$day[which(carb_data$virtualDay==days_to_analyze[i])[1]],as.Date(metaData$bDay[which(metaData$hashID==files[file_number])]))/365)))
    #Day tracker tracker gets normal day (not virtual day)
    day_tracker = c(day_tracker, carb_data$day[which(carb_data$virtualDay==days_to_analyze[i])[1]])
    
    #Start tracking EVERY individual glucose level with associated data to prepare for one BIG data frame
    #This is used for tracking overall %TIR
    big.filename[[day_num]] = rep(files[file_number],length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    big.bg[[day_num]] = bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]
    big.day[[day_num]] = rep(carb_data$day[which(carb_data$virtualDay==days_to_analyze[i])[1]],length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    big.timestamp[[day_num]] = as.character(round_date(bg_data$est.localTime[which(bg_data$virtualDay==days_to_analyze[i])],"5 minutes"))
    big.carbs[[day_num]] = rep(sum(carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])]),length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    big.age[[day_num]] = rep(as.integer(round(difftime(days_to_analyze[i],as.Date(metaData$bDay[which(metaData$hashID==files[file_number])]))/365)),length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    
    day_num = day_num+1
  }
  
  #Track how many days are provided by each user
  user_days_count = c(user_days_count, current_user_days_analyzed)
  current_user_days_analyzed = 0
  
  #Calculate and print estimate time remaining
  end_time = Sys.time()
  run_time = c(run_time, difftime(end_time,start_time,units="mins")/file.info(files[file_number])$size)
  
  #Print estimated time remaining after first file completes
  if(length(file_tracker)==1){
    #cat(paste("Files complete: ", toString(file_number), "/", toString(length(files))," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:length(files)])$size))), " min\n", sep="" ))
  }
  
  code_block3 = c(code_block3,difftime(Sys.time(),start_code_block3))
  
  cat(paste("Files complete: ", toString(file_number), "/", toString(files_to_process),"\n", sep=""))
  
  single_full_loop = c(single_full_loop, difftime(Sys.time(), start_single_full_loop))
  
} 
######################## END FILE PARSING LOOP #####################################

#File parsing information
total_sets_analyzed = length(unique(file_tracker))
real_run_end = Sys.time()
cat(paste("Total Run Time: ", toString(round(difftime(real_run_end,real_run_start,units="mins"))), " minutes",sep=""))

#Unpack all the list structures for analysis
total_daily_carbs = unlist(total_daily_carbs)
all_carb_entries = unlist(all_carb_entries)
carb_timestamps = unlist(carb_timestamps)
meanBG = unlist(meanBG)
medianBG = unlist(medianBG)
stddevBG = unlist(stddevBG)
daily_range = unlist(daily_range)
daily_25_75_IQR = unlist(daily_25_75_IQR)
daily_CV = unlist(daily_CV)
daily_below54 = unlist(daily_below54)
daily_below70 = unlist(daily_below70)
daily_70_180 = unlist(daily_70_180)
daily_above180 = unlist(daily_above180)
daily_above250 = unlist(daily_above250)
daily_hypo54_count = unlist(daily_hypo54_count)
daily_hypo70_count = unlist(daily_hypo70_count)
daily_hyper180_count = unlist(daily_hyper180_count)
daily_hyper250_count = unlist(daily_hyper250_count)
big.filename = unlist(big.filename)
big.bg = unlist(big.bg)
big.timestamp = unlist(big.timestamp)
big.carbs = unlist(big.carbs)
big.day = unlist(big.day)
big.age = unlist(big.age)
daily_cgm_events = unlist(daily_cgm_events)
daily_carb_events = unlist(daily_carb_events)
file_tracker = unlist(file_tracker)
day_tracker = unlist(day_tracker)
age_tracker = unlist(age_tracker)
diff_time_tracker = unlist(diff_time_tracker)

#Bind all elements into three separate dataframes
# df is for all daily SUMMARY information combined
# big.df is for EVERY CGM value collected and associated daily statistics next to each BG

#Convert timestamps to POSIX
carb_timestamps = strptime(carb_timestamps,"%Y-%m-%d %H:%M:%S",tz="UTC")
carb_timestamp_hours = format(carb_timestamps, "%H:%M")
big.timestamp = strptime(big.timestamp,"%Y-%m-%d %H:%M:%S",tz="UTC")
big.timestamp_hours = format(big.timestamp, "%H:%M")

df = data.frame(daily_cgm_events, daily_carb_events, age_tracker,day_tracker, total_daily_carbs,meanBG,medianBG,stddevBG,daily_range,daily_25_75_IQR,daily_CV, daily_below54,daily_below70,daily_70_180,daily_above180,daily_above250,daily_hypo54_count,daily_hypo70_count,daily_hyper180_count,daily_hyper250_count)
big.df = data.frame(big.filename,big.bg,big.day,big.carbs,big.age)

#Add age group and carb group columns to df
carb_by_group = cut(total_daily_carbs,breaks=seq(0,500,25),labels=c("1-25","26-50","51-75","76-100","101-125","126-150","151-175","176-200","201-225","226-250","251-275","276-300","301-325","326-350","351-375","376-400","401-425","426-450","451-475","476-500"))
levels(carb_by_group) <- c(levels(carb_by_group),"500+")
carb_by_group[is.na(carb_by_group)] = as.factor("500+")
age_by_group = cut(age_tracker,breaks=c(0,2,5,8,11,14,17,20,24,29,34,39,49,59,69,88),labels=c("0-2","3-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-49","50-59","60-69","70-88"))
df$carb_group = carb_by_group
df$age_group = age_by_group

#Add age group and carb group columns to big.df
carb_by_group = cut(big.df$big.carbs,breaks=seq(0,500,25),labels=c("1-25","26-50","51-75","76-100","101-125","126-150","151-175","176-200","201-225","226-250","251-275","276-300","301-325","326-350","351-375","376-400","401-425","426-450","451-475","476-500"))
levels(carb_by_group) <- c(levels(carb_by_group),"500+")
carb_by_group[is.na(carb_by_group)] = as.factor("500+")
age_by_group = cut(big.df$big.age,breaks=c(0,2,5,8,11,14,17,20,24,29,34,39,49,59,69,88),labels=c("0-2","3-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-49","50-59","60-69","70-88"))
big.df$carb_group = carb_by_group
big.df$age_group = age_by_group

