# This code demonstrates the basic trend analysis of anonymized Tidepool data sets
# Special focus is given to carb intake and daily BG effects

#library(readxl)
library(ggplot2)
library(hexbin)

#Set working directory to folder containing data
setwd("YOUR_WORKING_DIRECTORY")
files = dir()

#Create empty elements to fill from each file
total_daily_carbs = c()
all_carb_entries = c()
meanBG = c()
medianBG = c()
stddevBG = c()
daily_range = c()
daily_25_75_IQR = c()
daily_CV = c()

#These elements will be used to verify quality of data
daily_cgm_events = c()
file_tracker = c()
day_tracker = c()
mean_insulin_sensitivity = c()

#Run time tracking for console time-to-complete estimate
run_time = c()

#Loop through each file collecting all data and appending to respecting elements.
real_run_start = Sys.time()

#Keep track of skipped files
skipped_files = c()
no_carb_files = 0
no_bg_files = 0

#Keep track of total number of days with carbs and bg entries for each user
user_days_count = c()
total_days_analyzed = 0
total_sets_analyzed = 0

############## START FILE PROCESSING ##################

for(file_number in 1:length(files)){

  #Start time tracking for each file's processing time
  start_time <- Sys.time()
  
  #For all remaining files, estimate time remaining on every 100th file
  if(file_number%%100==0){
    cat(paste("Files complete: ", toString(file_number), "/", toString(length(files))," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:length(files)])$size))), " min\n", sep="" ))
  }
  
  ################ Use only for xlsx files ###################
  
  #carb_data = tryCatch(read_excel(files[file_number],sheet="bolus"), error=function(e) NA)
  #bg_data = tryCatch(read_excel(files[file_number],sheet="cbg"), error=function(e) NA)
  
  #Skip current file if missing sheet resulted in an "NA"
  #if(length(carb_data)==1){
  #  skipped_files = c(skipped_files,files[file_number])
  #  no_carb_files = no_carb_files + 1
  #  next
  #}
  
  #if(length(bg_data)==1){
  #  skipped_files = c(skipped_files,files[file_number])
  #  no_bg_files = no_bg_files + 1
  #  next
  #}
  
  ############################################################
  
  #Load data
  data = read.csv(files[file_number], stringsAsFactors = FALSE)
  
  if(!is.null(data$deviceTime)){
    data$deviceTime[which(data$deviceTime=="")]= "XTY"
  
    #Add a "day" column from deviceTime
    timestamp_vec = unlist(strsplit(data$deviceTime,"T"))
    data$day = timestamp_vec[seq(1,length(timestamp_vec),2)]
  }
  
  #Isolate carb, bg data
  carb_data = data[which(data$type=="bolus"),]
  bg_data = data[which(data$type=="cbg"),]
  

  
  #Remove duplicated timestamps
  #Use either deviceTime, time, utcTime, or est.localTime
  carb_data = carb_data[which(!duplicated(carb_data$deviceTime)),]
  bg_data = bg_data[which(!duplicated(bg_data$deviceTime)),]
  
  #Remove rows with empty/0 Carbs and BG
  carb_data = carb_data[!is.na(carb_data$carbInput),]
  carb_data = carb_data[carb_data$carbInput>0,]
  bg_data = bg_data[!is.na(bg_data$value),]
  
  #Skip current file if no carb input is available
  if(nrow(carb_data)<=1){
    skipped_files = c(skipped_files,files[file_number])
    no_carb_files = no_carb_files + 1
    next
  }
  
  #Skip current file if no bg input is available
  if(nrow(bg_data)<=1){
    skipped_files = c(skipped_files,files[file_number])
    no_bg_files = no_bg_files + 1
    next
  }
  
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
  unique_bg_days = unique(bg_data$day)
  unique_carb_days = unique(carb_data$day)
  days_to_analyze = unique_bg_days[unique_bg_days %in% unique_carb_days]
  user_days_count = c(user_days_count, length(days_to_analyze))
  
  #Store all carb events for this user
  all_carb_entries = c(all_carb_entries, carb_data$carbInput)
    
  #Set limit of how many days to take from each data set
  if(length(days_to_analyze)>90){
    limited_days = 90
  } else {
    limited_days = length(days_to_analyze)
  }
  
  #Fill elements for data frame of daily carb intake and mean BG 
  # (add additional metrics as needed)
  
  for(i in 1:limited_days){
    
    #Skip if there is bg data longer than 1 day or less than 2/3 of the day
    if(length(which(bg_data$day==days_to_analyze[i]))>288 | length(which(bg_data$day==days_to_analyze[i]))<192){
      next
    }
    
    #Skip if < 3 meals in the day
    if(length(carb_data$carbInput[which(carb_data$day==days_to_analyze[i])])<3){
      next
    }
    
    daily_cgm_events = c(daily_cgm_events, length(which(bg_data$day==days_to_analyze[i])))
    file_tracker = c(file_tracker, files[file_number])
    day_tracker = c(day_tracker, days_to_analyze[i])
    total_daily_carbs = c(total_daily_carbs, sum(carb_data$carbInput[which(carb_data$day==days_to_analyze[i])]))
    meanBG = c(meanBG,mean(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    medianBG = c(medianBG,median(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    stddevBG = c(stddevBG,sd(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    daily_range = c(daily_range, max(bg_data$value[which(bg_data$day==days_to_analyze[i])])-min(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    daily_25_75_IQR = c(daily_25_75_IQR, quantile(bg_data$value[which(bg_data$day==days_to_analyze[i])])[3]-quantile(bg_data$value[which(bg_data$day==days_to_analyze[i])])[2])
    daily_CV = c(daily_CV, 100*sd(bg_data$value[which(bg_data$day==days_to_analyze[i])])/mean(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    
    total_days_analyzed = total_days_analyzed + 1
    
  }
  
  #Calculate and print estimate time remaining
  end_time = Sys.time()
  run_time = c(run_time, difftime(end_time,start_time,units="mins")/file.info(files[file_number])$size)
  
  if(file_number==1){
    cat(paste("Files complete: ", toString(file_number), "/", toString(length(files))," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(files[file_number:length(files)])$size))), " min\n", sep="" ))
    }
}
total_sets_analyzed = length(unique(file_tracker))
real_run_end = Sys.time()
cat(paste("Total Run Time: ", toString(round(difftime(real_run_end,real_run_start,units="mins"))), " minutes",sep=""))
  
#Bind all elements into dataframe
df = data.frame(total_daily_carbs,meanBG,medianBG,stddevBG,daily_range,daily_25_75_IQR,daily_CV)


#Import file metadata
metaData = read.csv("metaData.csv", stringsAsFactors = FALSE)
metaData$hashID = paste(metaData$hashID, ".csv",sep="")
analyzedFile_metaData = which(metaData$hashID %in% unique(file_tracker))
metaData$age = as.integer(round(difftime(Sys.time(),as.Date(metaData$bDay))/365))

#Metadata details for analyzed files
count_type1 = which(metaData$diagnosisType[analyzedFile_metaData]=="type1")
count_type2 = which(metaData$diagnosisType[analyzedFile_metaData]=="type2")
count_lada = which(metaData$diagnosisType[analyzedFile_metaData]=="lada")
count_gestational = which(metaData$diagnosisType[analyzedFile_metaData]=="gestational")
count_prediabetes = which(metaData$diagnosisType[analyzedFile_metaData]=="prediabetes")
count_other = which(metaData$diagnosisType[analyzedFile_metaData]=="other")
count_blank = which(metaData$diagnosisType[analyzedFile_metaData]=="")

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

count_age_1_5 = which(metaData$age[analyzedFile_metaData]>=1 & metaData$age[analyzedFile_metaData] <=5)
count_age_6_8 = which(metaData$age[analyzedFile_metaData]>=6 & metaData$age[analyzedFile_metaData] <=8)
count_age_9_11 = which(metaData$age[analyzedFile_metaData]>=9 & metaData$age[analyzedFile_metaData] <=11)
count_age_12_14 = which(metaData$age[analyzedFile_metaData]>=12 & metaData$age[analyzedFile_metaData] <=14)
count_age_15_17 = which(metaData$age[analyzedFile_metaData]>=15 & metaData$age[analyzedFile_metaData] <=17)
count_age_18_20 = which(metaData$age[analyzedFile_metaData]>=18 & metaData$age[analyzedFile_metaData] <=20)
count_age_21_24 = which(metaData$age[analyzedFile_metaData]>=21 & metaData$age[analyzedFile_metaData] <=24)
count_age_25_29 = which(metaData$age[analyzedFile_metaData]>=25 & metaData$age[analyzedFile_metaData] <=29)
count_age_30_34 = which(metaData$age[analyzedFile_metaData]>=30 & metaData$age[analyzedFile_metaData] <=34)
count_age_35_39 = which(metaData$age[analyzedFile_metaData]>=35 & metaData$age[analyzedFile_metaData] <=39)
count_age_40_49 = which(metaData$age[analyzedFile_metaData]>=40 & metaData$age[analyzedFile_metaData] <=49)
count_age_50_59 = which(metaData$age[analyzedFile_metaData]>=50 & metaData$age[analyzedFile_metaData] <=59)
count_age_60_69 = which(metaData$age[analyzedFile_metaData]>=60 & metaData$age[analyzedFile_metaData] <=69)
count_age_70_88 = which(metaData$age[analyzedFile_metaData]>=70 & metaData$age[analyzedFile_metaData] <=88)

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

#######
# Optional Code to run
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
 
