
################################################################################################
#
# This code demonstrates the basic trend analysis of Tidepool data sets
#
# Special focus is given to carb intake and daily BG effects
#
################################################################################################

library(ggplot2)
library(hexbin)
library(lubridate)

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
#This helps speed up processing time by using only known unskipped files
#files = unique(file_tracker)

#Create empty elements to fill from each file
total_daily_carbs = c()
all_carb_entries = c()
carb_timestamps = c()

#Statistical measurements
meanBG = c()
medianBG = c()
stddevBG = c()
daily_range = c()
daily_25_75_IQR = c()
daily_CV = c()
daily_below54 = c()
daily_below70 = c()
daily_70_180 = c()
daily_above180 = c()
daily_above250 = c()

daily_hypo54_count = c()
daily_hypo70_count = c()
daily_hyper180_count = c()
daily_hyper250_count = c()

#Big data structure elements
big.filename = c()
big.bg = c()
big.carbs = c()
big.day = c()
big.age = c()

#These elements will be used to verify quality of data
daily_cgm_events = c()
daily_carb_events = c()
file_tracker = c()
day_tracker = c()
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

#Set how many files to process
#files_to_process = length(files)
files_to_process = 50

############## START FILE PROCESSING ##################

for(file_number in 1:files_to_process){

  #Start time tracking for each file's processing time
  start_time <- Sys.time()
  
  #For all remaining files, estimate time remaining on every 100th file
  if(file_number%%100==0){
    cat(paste("Files complete: ", toString(file_number), "/", toString(files_to_process)," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:files_to_process])$size))), " min\n", sep="" ))
  }
  
  #Load data
  data = read.csv(files[file_number], stringsAsFactors = FALSE)
  
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
  #  #Remove NAs from missing deviceTime rows
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
  
  #Isolate carb, bg data
  
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
  
  #Round all bg data timestamps to nearest 5 minutes
  #There should never be a cgm timestamp less than 5 minutes apart.
  bg_data$virtualTime = round_date(bg_data$virtualTime,"5 minutes")
  
  #Remove duplicated timestamps
  #Use deviceTime, est.localTime, or a rounded virtual time.
  carb_data = carb_data[which(!duplicated(carb_data$est.localTime)),]
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

  #Store all carb events for this user
  all_carb_entries = c(all_carb_entries, carb_data$carbInput)
  carb_timestamps = c(carb_timestamps,carb_data$est.localTime)
  
  #Find days where both carbs and BG data is available
  unique_bg_days = unique(bg_data$virtualDay)
  unique_carb_days = unique(carb_data$virtualDay)
  days_to_analyze = unique_bg_days[unique_bg_days %in% unique_carb_days]
  
  #Skip file if # of days available is less than the minimum required from the Filter Options
  if(length(days_to_analyze) < minimum_days){
    skipped_files_not_enough_days = skipped_files_not_enough_days + 1
    next
  }

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
    
    daily_cgm_events = c(daily_cgm_events, length(which(bg_data$virtualDay==days_to_analyze[i])))
    daily_carb_events = c(daily_carb_events, length(which(carb_data$virtualDay==days_to_analyze[i])))
    file_tracker = c(file_tracker, files[file_number])
    
    total_daily_carbs = c(total_daily_carbs, sum(carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])]))
    meanBG = c(meanBG,mean(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    medianBG = c(medianBG,median(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    stddevBG = c(stddevBG,sd(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    daily_range = c(daily_range, max(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])-min(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    daily_25_75_IQR = c(daily_25_75_IQR, quantile(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])[3]-quantile(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])[2])
    daily_CV = c(daily_CV, 100*sd(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])/mean(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])]))
    
    #Tracking time in range
    daily_below54 = c(daily_below54, 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<54))/length(which(bg_data$virtualDay==days_to_analyze[i])))
    daily_below70 = c(daily_below70, 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<70))/length(which(bg_data$virtualDay==days_to_analyze[i])))
    daily_70_180 = c(daily_70_180, 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>=70 & bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<=180))/length(which(bg_data$virtualDay==days_to_analyze[i])))
    daily_above180 = c(daily_above180, 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>180))/length(which(bg_data$virtualDay==days_to_analyze[i])))
    daily_above250 = c(daily_above250, 100*length(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>250))/length(which(bg_data$virtualDay==days_to_analyze[i])))
    
    #Tracking daily number of hypo/hyper episodes
    daily_hypo54_count = c(daily_hypo54_count, length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<54)))$lengths>=3)))
    daily_hypo70_count = c(daily_hypo70_count, length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]<70)))$lengths>=3)))
    daily_hyper180_count = c(daily_hyper180_count, length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>180)))$lengths>=3)))
    daily_hyper250_count = c(daily_hyper250_count, length(which(rle(diff(which(bg_data$value[(which(bg_data$virtualDay==days_to_analyze[i]))]>250)))$lengths>=3)))
    
    
    total_days_analyzed = total_days_analyzed + 1
    current_user_days_analyzed = current_user_days_analyzed + 1
    
    #Day tracker and hourly tracker gets normal day (not virtual day)
    day_tracker = c(day_tracker, carb_data$day[which(carb_data$virtualDay==days_to_analyze[1])[1]])
    
    #Start tracking EVERY individual glucose level with associated data to prepare for one BIG data frame
    big.filename = c(big.filename, rep(files[file_number],length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])))
    big.bg = c(big.bg,bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])
    big.day = c(big.day, rep(carb_data$day[which(carb_data$virtualDay==days_to_analyze[1])[1]],length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])))
    big.carbs = c(big.carbs, rep(sum(carb_data$carbInput[which(carb_data$virtualDay==days_to_analyze[i])]),length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])))
    big.age = c(big.age, rep(as.integer(round(difftime(days_to_analyze[i],as.Date(metaData$bDay[which(metaData$hashID==files[i])]))/365)),length(bg_data$value[which(bg_data$virtualDay==days_to_analyze[i])])))
  }
  
  #Track how many days are provided by each user
  user_days_count = c(user_days_count, current_user_days_analyzed)
  current_user_days_analyzed = 0
  
  #Calculate and print estimate time remaining
  end_time = Sys.time()
  run_time = c(run_time, difftime(end_time,start_time,units="mins")/file.info(files[file_number])$size)
  
  #Print estimated time remaining after first file completes
  if(length(file_tracker)==1){
    cat(paste("Files complete: ", toString(file_number), "/", toString(length(files))," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:length(files)])$size))), " min\n", sep="" ))
    }
} 

#File parsing information
total_sets_analyzed = length(unique(file_tracker))
real_run_end = Sys.time()
cat(paste("Total Run Time: ", toString(round(difftime(real_run_end,real_run_start,units="mins"))), " minutes",sep=""))
 
 
######################## END FILE PARSING #####################################


######################## BEGIN DATA ANALYSIS #####################################
 
#Bind all elements into dataframe
df = data.frame(total_daily_carbs,meanBG,medianBG,stddevBG,daily_range,daily_25_75_IQR,daily_CV)
big.df = data.frame(big.filename,big.bg,big.day,big.carbs,big.age)

#Use previously imported file metadata
metaData$age = as.integer(round(difftime(Sys.time(),as.Date(metaData$bDay))/365))
analyzedFile_metaData = which(metaData$hashID %in% unique(file_tracker))

#Filter metadata to only include files from the analysis
filtered_metaData = metaData[analyzedFile_metaData,]

#Metadata details for analyzed files
count_type1 = which(filtered_metaData$diagnosisType=="type1")
count_type2 = which(filtered_metaData$diagnosisType=="type2")
count_lada = which(filtered_metaData$diagnosisType=="lada")
count_gestational = which(filtered_metaData$diagnosisType=="gestational")
count_prediabetes = which(filtered_metaData$diagnosisType=="prediabetes")
count_other = which(filtered_metaData$diagnosisType=="other")
count_blank = which(filtered_metaData$diagnosisType=="")

types = c("Type 1", "Type 2", "LADA", "Gestational", "Prediabetes", "Other")
type_counts = c(length(count_type1),length(count_type2),length(count_lada),length(count_gestational),length(count_prediabetes), length(count_other))
type_counts_df = data.frame(types, type_counts)
ggplot(data=type_counts_df,aes(x=types,y=type_counts))+
  geom_bar(stat = "identity",fill="grey",color="black")+
  scale_x_discrete(limits=type_counts_df$types)+
  theme_classic()+
  xlab("Diabetes Diagnosis Type")+
  ylab("Count Analyzed")+ 
  labs(title="Data Sets Analyzed by Diabetes Type")

#Find the filename count for each age group in the analyzed data
count_age_1_5 = which(filtered_metaData$age>=1 & filtered_metaData$age <=5)
count_age_6_8 = which(filtered_metaData$age>=6 & filtered_metaData$age <=8)
count_age_9_11 = which(filtered_metaData$age>=9 & filtered_metaData$age <=11)
count_age_12_14 = which(filtered_metaData$age>=12 & filtered_metaData$age <=14)
count_age_15_17 = which(filtered_metaData$age>=15 & filtered_metaData$age <=17)
count_age_18_20 = which(filtered_metaData$age>=18 & filtered_metaData$age <=20)
count_age_21_24 = which(filtered_metaData$age>=21 & filtered_metaData$age <=24)
count_age_25_29 = which(filtered_metaData$age>=25 & filtered_metaData$age <=29)
count_age_30_34 = which(filtered_metaData$age>=30 & filtered_metaData$age <=34)
count_age_35_39 = which(filtered_metaData$age>=35 & filtered_metaData$age <=39)
count_age_40_49 = which(filtered_metaData$age>=40 & filtered_metaData$age <=49)
count_age_50_59 = which(filtered_metaData$age>=50 & filtered_metaData$age <=59)
count_age_60_69 = which(filtered_metaData$age>=60 & filtered_metaData$age <=69)
count_age_70_88 = which(filtered_metaData$age>=70 & filtered_metaData$age <=88)

#Get the total days for donors above age 20
#Get the total amount of days where carbs exceeded the national mean (CDC)
above_20 = c(count_age_21_24, count_age_25_29, count_age_30_34,count_age_35_39,count_age_40_49,count_age_50_59,count_age_60_69,count_age_70_88)
carbs_over_260_above_20 = c()
days_above_20 = c()
for(donor in 1:length(above_20)){
  carbs_over_260_above_20 = c(carbs_over_242_above_20, length(which(total_daily_carbs[which(file_tracker==filtered_metaData$hashID[above_20[donor]])]>242)))
  days_above_20 = c(days_above_20, length(which(file_tracker==filtered_metaData$hashID[above_20[donor]])))
}

#Plot the number of data sets analyzed by age
ages = c("1-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-49","50-59","60-69","70-88")
age_counts = c(length(count_age_1_5), length(count_age_6_8), length(count_age_9_11), length(count_age_12_14), length(count_age_15_17), length(count_age_18_20), length(count_age_21_24), length(count_age_25_29), length(count_age_30_34), length(count_age_35_39), length(count_age_40_49), length(count_age_50_59), length(count_age_60_69), length(count_age_70_88))
age_counts_df = data.frame(ages,age_counts)
ggplot(data=age_counts_df,aes(x=ages,y=age_counts))+
  geom_bar(stat = "identity",fill="grey",color="black")+
  scale_x_discrete(limits=age_counts_df$ages)+
  theme_classic()+
  xlab("Age")+
  ylab("Count Analyzed")+ 
  labs(title="Data Sets Analyzed by Age")

#How many days are contributed by each donor?
days_per_donor = c()
for(donor in 1:length(unique(file_tracker))){
  days_per_donor = c(days_per_donor, length(which(file_tracker==unique(file_tracker)[donor])))
}

days_per_age = c()
#How many days are contributed by each age group? (TBD)


######## Time in range plots

#Plot Time in Range distributions (normal)
hist(daily_below70,xlim=c(0,100),col=rgb(1,0,0,0.25),breaks=59,main ="%Time in Range Distributions",xlab="% Time in Range")
hist(daily_above180,col=rgb(0,0,1,0.25),breaks=100,add=T)
hist(daily_70_180,col=rgb(0,1,0,0.25),breaks=100,add=T)
legend("topright", inset=.02, title="Blood Glucose Ranges",c("Below 70 mg/dL","Between 70 - 180 mg/dL","Above 180 mg/dL"), fill=c(rgb(1,0,0,0.25),rgb(0,1,0,0.25),rgb(0,0,1,0.25)), cex=0.8)
box()

#Plot Time in Range distributions (log y)
TIR.df = data.frame(x = c(daily_below70,daily_70_180, daily_above180),y = rep(c('Below 70 mg/dL','Between 70 - 180 mg/dL','Above 180 mg/dL'),each = length(daily_below70)))
TIR.df$y = factor(TIR.df$y,levels=unique(TIR.df$y))

ggplot(TIR.df, aes(x=x, fill=as.factor(y))) +   
  geom_histogram(bins=100,col='black',alpha=0.5, position="identity")+
  scale_y_log10(expand = c(0,0))+
  theme_classic()+
  #scale_fill_manual(values=c("Desired colors"))+
  labs(fill='Blood Glucose Range',title = "% Time in Range Distributions", x = "% Time in Range", y = "Frequency (Log)")

#Create data frame grouped by carb intake and mean percent time in range
carb_by_group = cut(total_daily_carbs,breaks=seq(0,500,25))
group_names = levels(carb_by_group)
df_TIR = c()


for(carb_group in 1:length(group_names)){
  df_TIR = rbind(df_TIR, c(group_names[carb_group], mean(daily_above180[which(carb_by_group==group_names[carb_group])]), "Above 180"))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], mean(daily_70_180[which(carb_by_group==group_names[carb_group])]), "Between 70-180"))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], mean(daily_below70[which(carb_by_group==group_names[carb_group])]), "Below 70"))
}

df_TIR = data.frame(df_TIR)
colnames(df_TIR)=c("carb_group","time_in_range","range_name")
df_TIR$carb_group = factor(df_TIR$carb_group,levels=unique(df_TIR$carb_group))
df_TIR$range_name = factor(df_TIR$range_name,levels=unique(df_TIR$range_name))

ggplot(df_TIR, aes(fill=as.factor(range_name), y=as.double(as.character(time_in_range)), x=as.factor(carb_group))) + 
  geom_bar( stat="identity",position="dodge")+
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("Mean % Time in Range")+ 
  labs(title="Daily Carb Intake vs Mean % Time in Range")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))+
  scale_fill_manual(values=c("#BC9BE7","#77D3A7","#FF8C7D"))+
  labs(fill='Blood Glucose Range')
  #geom_text(aes(label=as.integer(as.character(time_in_range))), position=position_dodge(width=0.9), vjust=-0.25)

############ For use with big data frame ######################

carb_by_group = cut(big.df$big.carbs,breaks=seq(0,500,25))
age_by_group = cut(big.df$big.age,breaks=c(1,5,8,11,14,17,20,24,29,34,39,49,59,69,88),labels=c("1-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-49","50-59","60-69","70-88"))
levels(carb_by_group) <- c(levels(carb_by_group),"500+")
carb_by_group[is.na(carb_by_group)] = as.factor("500+")
big.df$carb_group = carb_by_group
big.df$age_group = age_by_group
group_names = levels(carb_by_group)
age_ranges = levels(age_by_group)
df_TIR = c()


for(carb_group in 1:length(group_names)){
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>=180))/length(which(big.df$carb_group==group_names[carb_group])), "Above 180"))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>70 & big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<180))/length(which(big.df$carb_group==group_names[carb_group])), "Between 70-180"))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<=70))/length(which(big.df$carb_group==group_names[carb_group])), "Below 70"))
}

df_TIR = data.frame(df_TIR)
colnames(df_TIR)=c("carb_group","time_in_range","range_name")
df_TIR$carb_group = factor(df_TIR$carb_group,levels=unique(df_TIR$carb_group))
df_TIR$range_name = factor(df_TIR$range_name,levels=unique(df_TIR$range_name))

## Plot All Glucose Range + Carb Ranges together
ggplot(df_TIR, aes(fill=as.factor(range_name), y=as.double(as.character(time_in_range)), x=as.factor(carb_group))) + 
  geom_bar( stat="identity",position="dodge")+
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("% Time in Range")+ 
  labs(title="Daily Carb Intake vs % Time in Range")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))+
  scale_fill_manual(values=c("#BC9BE7","#77D3A7","#FF8C7D"))+
  labs(fill='Blood Glucose Range')
#geom_text(aes(label=as.integer(as.character(time_in_range))), position=position_dodge(width=0.9), vjust=-0.25)

## Plot only Above 180 + Carb Ranges
ggplot(subset(df_TIR, range_name %in% c("Above 180")),aes(x=as.factor(carb_group),y=as.double(as.character(time_in_range)))) + 
  geom_bar(stat = "identity",aes(fill="#BC9BE7"))+
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("% Time in Range")+ 
  labs(title="Percent Time Above 180 mg/dL")+
  theme(legend.position="none",axis.text.x = element_text(angle = 90, hjust = 1))+
  scale_fill_manual(values=c("#BC9BE7"))
  #labs(fill='Blood Glucose Range')

## Plot only Between 70 and 180 + Carb Ranges
ggplot(subset(df_TIR, range_name %in% c("Between 70-180")),aes(x=as.factor(carb_group),y=as.double(as.character(time_in_range)))) + 
  geom_bar(stat = "identity",fill="#77D3A7")+
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("% Time in Range")+ 
  labs(title="Percent Time In Range (70 - 180 mg/dL)")+
  theme(legend.position="none",axis.text.x = element_text(angle = 90, hjust = 1))+
  scale_fill_manual(values=c("#77D3A7"))

## Plot only Below 70 + Carb Ranges
ggplot(subset(df_TIR, range_name %in% c("Below 70")),aes(x=as.factor(carb_group),y=as.double(as.character(time_in_range)))) + 
  geom_bar(stat = "identity",aes(fill="#FF8C7D"))+
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("% Time in Range")+ 
  labs(title=" Percent Time Below 70 mg/dL")+
  theme(legend.position="none",axis.text.x = element_text(angle = 90, hjust = 1))+
  scale_fill_manual(values=c("#FF8C7D"))


###########
# Use for Age + Carb + TIR figures
##########

carb_by_group = cut(big.df$big.carbs,breaks=seq(0,500,25))
age_by_group = cut(big.df$big.age,breaks=c(1,5,8,11,14,17,20,24,29,34,39,49,59,69,88),labels=c("1-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-49","50-59","60-69","70-88"))

levels(carb_by_group) <- c(levels(carb_by_group),"500+")
carb_by_group[is.na(carb_by_group)] = as.factor("500+")

big.df$carb_group = carb_by_group
big.df$age_group = age_by_group

group_names = levels(carb_by_group)
age_ranges = levels(age_by_group)
df_TIR = c()

for(carb_group in 1:length(group_names)){
  for(age_group in 1:length(age_ranges)){
  df_TIR = rbind(df_TIR, c(age_ranges[age_group],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>=180))/length(which(big.df$carb_group==group_names[carb_group])), "Above 180"))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>70 & big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<180))/length(which(big.df$carb_group==group_names[carb_group])), "Between 70-180"))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<=70))/length(which(big.df$carb_group==group_names[carb_group])), "Below 70"))
  }
}

df_TIR = data.frame(df_TIR)
colnames(df_TIR)=c("age_group","carb_group","time_in_range","range_name")
df_TIR$carb_group = factor(df_TIR$carb_group,levels=unique(df_TIR$carb_group))
df_TIR$age_group = factor(df_TIR$age_group,levels=unique(df_TIR$age_group))
df_TIR$range_name = factor(df_TIR$range_name,levels=unique(df_TIR$range_name))



#######
# General Distributions and Figures
#######

#Write data frame to file
#write.csv(df,file="tidepool_carb-bg-data.csv",row.names = FALSE)

#Basic Median BG histogram
ggplot(data=df) + 
  geom_histogram(aes(medianBG),bins=60)+
  theme_classic()+
  xlab("Daily Median Blood Glucose (mg/dL)")+
  ylab("Count")+ 
  labs(title="Daily Median Blood Glucose Histogram")+
  scale_x_continuous(breaks=seq(0,max(medianBG),50))

#Basic Total Daily Carbs histogram
ggplot(data=df) + 
  geom_histogram(aes(total_daily_carbs),bins=80)+
  theme_classic()+
  xlab("Total Daily Carb Intake (g)")+
  ylab("Count")+ 
  labs(title="Daily Carb Intake Histogram")+
  scale_x_continuous(breaks=seq(0,max(total_daily_carbs),50))


#Density Scatterplot
d = densCols(df$total_daily_carbs, df$medianBG, colramp = colorRampPalette(rev(rainbow(10, end = 4/6))))
ggplot(data=df) +
  geom_point(aes(x=total_daily_carbs, y=medianBG,colour=as.factor(d)), size = 1) +
  scale_color_identity()+
  theme_classic()+
  xlab("Total Daily Carb Intake (g)")+
  ylab("Median BG (mg/dL)")+ 
  labs(title="Carb Intake vs of Median Blood Glucose Level")+
  scale_x_continuous(breaks=seq(0,800,50))

#Hexbin Density Plot
ggplot(data=df)+
  geom_hex(aes(x=total_daily_carbs, y=stddevBG), bins=100,color="black")+
  theme_classic()+
  scale_fill_gradientn("Density", colours = rev(rainbow(10, end = 4/6)))+
  xlab("Total Daily Carb Intake (g)")+
  ylab("BG Standard Deviation (mg/dL)")+ 
  labs(title="Carb Intake vs of Blood Glucose SD")+
  scale_x_continuous(breaks=seq(0,800,50), limits=c(0,800))

#Bin elements of each carb section and make binned boxplot
df$bin_type = cut(df$total_daily_carbs,breaks=seq(0,500,50))

ggplot(data=df) + 
  geom_boxplot(aes(x=bin_type,y=meanBG)) + 
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("BG Standard Deviation (mg/dL)")+ 
  labs(title="Carb Intake vs Blood Glucose SD (10g bins)")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))

hist(as.Date(day_tracker),breaks=200,format = "%b %Y")

#One possible version of time of day and carb intake frequency
#x=as.factor(format(round_date(carb_data$est.localTime,"15 minutes"),"%H:%M"))
#hist(as.integer(x),breaks=100)
#axis(1,at=1:length(levels(x)),labels=levels(x))

##### Special age-defined scatterplots

#Density Scatterplot
d = densCols(total_daily_carbs[which(file_tracker %in% metaData$hashID[count_type1])], medianBG[which(file_tracker %in% metaData$hashID[count_type1])], colramp = colorRampPalette(rev(rainbow(10, end = 4/6))))
ggplot() +
  geom_point(aes(x=total_daily_carbs[which(file_tracker %in% metaData$hashID[count_type1])], y=medianBG[which(file_tracker %in% metaData$hashID[count_type1])],colour=as.factor(d)), size = 1) +
  scale_color_identity()+
  theme_classic()+
  xlab("Total Daily Carb Intake (g)")+
  ylab("Median BG (mg/dL)")+ 
  labs(title="Carb Intake vs of Median Blood Glucose Level")+
  scale_x_continuous(breaks=seq(0,800,50))

  #Bin elements of each carb section and make binned boxplot
  bin_type = cut(total_daily_carbs[which(file_tracker %in% metaData$hashID[count_type1])],breaks=seq(0,500,50))

ggplot() + 
  geom_boxplot(aes(x=bin_type,y=medianBG[which(file_tracker %in% metaData$hashID[count_type1])])) + 
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("BG Median (mg/dL)")+ 
  labs(title="Carb Intake vs Blood Glucose Median (50g bins)")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))
 
