# This code demonstrates the basic trend analysis of anonymized Tidepool data sets
# Special focus is given to carb intake and daily BG effects

library(readxl)
library(ggplot2)
library(hexbin)

#Set working directory to folder containing xlsx data
setwd("C:/YOUR_WORKING_DIRECTORY")
xlsx_files = dir()

#Create empty elements to fill from each file
total_daily_carbs = c()
all_carb_entries = c()
meanBG = c()
medianBG = c()
stddevBG = c()

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


for(file_number in 1:length(xlsx_files)){
  #Start time tracking for each file's processing time
  start_time <- Sys.time()
  carb_data = tryCatch(read_excel(xlsx_files[file_number],sheet="bolus"), error=function(e) NA)
  bg_data = tryCatch(read_excel(xlsx_files[file_number],sheet="cbg"), error=function(e) NA)
  
  #Skip current file if missing sheet resulted in an "NA"
  if(length(carb_data)==1){
    skipped_files = c(skipped_files,xlsx_files[file_number])
    no_carb_files = no_carb_files + 1
    next
  }
  
  if(length(bg_data)==1){
    skipped_files = c(skipped_files,xlsx_files[file_number])
    no_bg_files = no_bg_files + 1
    next
  }
  
  #Remove rows with empty/0 Carbs and BG
  carb_data = carb_data[!is.na(carb_data$carbInput),]
  carb_data = carb_data[carb_data$carbInput>0,]
  bg_data = bg_data[!is.na(bg_data$value),]
  
  
  #Skip current file if no carb input is available
  if(nrow(carb_data)<=1){
    skipped_files = c(skipped_files,xlsx_files[file_number])
    no_carb_files = no_carb_files + 1
    next
  }
  
  #Set units and their conversion multiplier to "mg/dL" or "mmol/L"
  units = "mg/dL"
  
  if(units=="mg/dL") {
    
    multiplier = 18.0156
    
  } else {
    
      multiplier = 1/18.0156    
    
  }
  
  #Check each BG for appropriate units, and convert if needed
  bg_data$value[which(bg_data$units!=units)]=bg_data$value[which(bg_data$units!=units)]*multiplier
  carb_data$insulinSensitivity[which(carb_data$units!=units)]=carb_data$insulinSensitivity[which(carb_data$units!=units)]*multiplier
  
  #Add a "day" column to BG data and carb data
  timestamp_vec = unlist(strsplit(bg_data$est.localTime," "))
  bg_data$day = timestamp_vec[seq(1,length(timestamp_vec),2)]
  
  timestamp_vec = unlist(strsplit(carb_data$est.localTime," "))
  carb_data$day = timestamp_vec[seq(1,length(timestamp_vec),2)]
  
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
    
    total_daily_carbs = c(total_daily_carbs, sum(carb_data$carbInput[which(carb_data$day==days_to_analyze[i])]))
    meanBG = c(meanBG,mean(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    medianBG = c(medianBG,median(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
    stddevBG = c(stddevBG,sd(bg_data$value[which(bg_data$day==days_to_analyze[i])]))
  }
  
  total_days_analyzed = total_days_analyzed + limited_days
  total_sets_analyzed = total_sets_analyzed + 1
  
  #Calculate and print estimate time remaining
  end_time = Sys.time()
  run_time = c(run_time, difftime(end_time,start_time,units="mins")/file.info(xlsx_files[file_number])$size)
  
  if(file_number%%100==0 | file_number==1){
    cat(paste("Files complete: ", toString(file_number), "/", toString(length(xlsx_files))," -- ", sep=""))
    cat(paste("Estimated time remaining: ", toString(round(mean(run_time)*sum(file.info(xlsx_files[file_number:length(xlsx_files)])$size))), " min\n", sep="" ))
    }
}
real_run_end = Sys.time()
cat(paste("Total Run Time: ", toString(round(difftime(real_run_end,real_run_start,units="mins"))), " minutes",sep=""))
  
#Bind all elements into dataframe
df = data.frame(cbind(total_daily_carbs,meanBG,medianBG))

#######
# Optional Code to run
#######

#Write data frame to file
#write.csv(df,file="tidepool_carb-bg-data.csv",row.names = FALSE)

#Basic histogram
ggplot(data=df) + 
  geom_histogram(aes(total_daily_carbs),bins=60)+
  theme_classic()+
  xlab("Daily Median Blood Glucose (mg/dL)")+
  ylab("Count")+ 
  labs(title="Daily Median Blood Glucose Histogram")+
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
  geom_hex(aes(x=total_daily_carbs, y=stddevBG), bins=45,color="black")+
  theme_classic()+
  scale_fill_gradientn("Density", colours = rev(rainbow(10, end = 4/6)))+
  xlab("Total Daily Carb Intake (g)")+
  ylab("BG Standard Deviation (mg/dL)")+ 
  labs(title="Carb Intake vs of Blood Glucose SD")+
  scale_x_continuous(breaks=seq(0,800,50))

#Bin elements of each carb section and make binned boxplot
df$bin_type = cut(df$total_daily_carbs,breaks=seq(0,500,50))

ggplot(data=df) + 
  geom_boxplot(aes(x=bin_type,y=stddevBG)) + 
  theme_classic() + 
  xlab("Total Daily Carb Intake Range (g)")+
  ylab("BG Standard Deviation (mg/dL)")+ 
  labs(title="Carb Intake vs Blood Glucose SD (10g bins)")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))
