###############################################################################
# description:  The folowing code will compile summary statistics on the number
#               and frequency of duplications of basal, bolus and cgm data on a 
#               file of Tidepool user data.     
# version: 0.0.1
# created: 2018-11-27
# author: Kyle Bolduc
# dependencies:
#     * requires tidepool analysis environment (see readme for instructions)
#     * tidyverse
#     * lubridate
#    
# license: BSD-2-Clause
##############################################################################


#Load Dependencies:
if (require("tidyverse") == FALSE) {install.packages("tidyverse")}
library("tidyverse")

if (require("lubridate") == FALSE) {install.packages("lubridate")}
library("lubridate")

# The time_dup_summary function takes a Tidepool user file and identifies the duplicated values
# using the R base 'duplicated' function. The duplicated function returns a logical vector
# indicating TRUE when a record is duplicated with respect to the given elements.  The first
# occurrence is not considered a duplicate.  However, the time_dup_summary function tags all
# duplicate occurrences, regardles of the order of appearence, in order to allow the analyst 
# to determine which record to retain.  All duplicates are tagged by running the base::duplicated 
# function twice, once from the top and a second time in reverse, thereby capturing all 
# duplicated events.  All results for duplicated data are then consolidated in the duplicated_data
# column.

time_dup_summary = function(tp_user) {

#initial duplicate tracking columns:
  
  tp_user$duplicated = NA
  tp_user$duplicated2 = NA
  tp_user$duplicated_data = NA
  
#Tag basal duplicates (in forward and then reverse order with respect to the columns listed):  
  tp_user[tp_user$type == 'basal',]$duplicated = duplicated(tp_user[tp_user$type == 'basal', 
                                                                          c("deviceTime",
                                                                            "deliveryType",
                                                                            "duration",
                                                                            "rate")])
  
  
  tp_user[tp_user$type == 'basal',]$duplicated2 = duplicated(tp_user[tp_user$type == 'basal', 
                                                                           c("deviceTime",
                                                                             "deliveryType",
                                                                             "duration",
                                                                             "rate")], fromLast = TRUE)
  
#Tag Bolus duplicates:
  tp_user[tp_user$type == 'bolus',]$duplicated = duplicated(tp_user[tp_user$type == 'bolus', 
                                                                          c("deviceTime",
                                                                            "normal")])
  
  
  
  tp_user[tp_user$type == 'bolus',]$duplicated2 = duplicated(tp_user[tp_user$type == 'bolus', 
                                                                           c("deviceTime",
                                                                             "normal")], fromLast = TRUE)

#Tag cbg duplicated (with deviceTime):
  
  tp_user[!is.na(tp_user$deviceTime) & tp_user$type == 'cbg',]$duplicated = duplicated(tp_user[!is.na(tp_user$deviceTime) & tp_user$type == 'cbg', 
                                                        c("deviceTime",
                                                          "value")])
  
  
  tp_user[!is.na(tp_user$deviceTime) & tp_user$type == 'cbg',]$duplicated2 = duplicated(tp_user[!is.na(tp_user$deviceTime) & tp_user$type == 'cbg', 
                                                         c("deviceTime",
                                                           "value")], fromLast = TRUE)

#Tag smbg duplicates:
  
  tp_user[tp_user$type == 'smbg',]$duplicated = duplicated(tp_user[tp_user$type == 'smbg', 
                                                         c("deviceTime",
                                                           "value")])
  
  
  tp_user[tp_user$type == 'smbg',]$duplicated2 = duplicated(tp_user[tp_user$type == 'smbg', 
                                                         c("deviceTime",
                                                           "value")], fromLast = TRUE)

#Consolidate all flagged duplicates to a single column: duplicated_data    
  tp_user$duplicated_data = ifelse(tp_user$duplicated | tp_user$duplicated2, TRUE, FALSE)
  
#Remove columns no longer required:
  tp_user$duplicated = NULL
  tp_user$duplicated2 = NULL
  
#Convert deviceTime and est.localTime to type datetime with lubridate
  tp_user$deviceTime = ymd_hms(tp_user$deviceTime)
  
  tp_user$est.localTime = ymd_hms(tp_user$est.localTime)

#Calculate difference between deviceTime and est.localTime, rounded to nearest hour: 
  tp_user$timedelta_hrs = round(difftime(time1 = tp_user$deviceTime, 
                                       time2 = tp_user$est.localTime, 
                                       units = c('hours')), 0)
  
  
#Fill in computerTimes
  tp_user = 
  tp_user %>%
    arrange(uploadId, time) %>%
    fill(computerTime, .direction = c("up"))
  
##################################
#######Aggregate Stats for output:
  

  Num_Records = nrow(tp_user)
  
  Num_cbg_all = nrow(tp_user[tp_user$type == 'cbg',])
  Num_cbg_dT = nrow(tp_user[tp_user$type == 'cbg' & !is.na(tp_user$deviceTime),])
  Num_cbg_dups = sum(tp_user[tp_user$type == 'cbg',]$duplicated_data, na.rm = TRUE)
  cbg_dup_density = if (Num_cbg_dups > 0) {round(Num_cbg_dups / Num_cbg_dT * 100, 2)}else{0}
  
  Num_basal = nrow(tp_user[tp_user$type == 'basal',])
  Num_basal_dups = sum(tp_user[tp_user$type == 'basal',]$duplicated_data, na.rm = TRUE)
  basal_dup_density = if (Num_basal_dups > 0) {round(Num_basal_dups / Num_basal * 100, 2)}else{0}
  
  Num_bolus = nrow(tp_user[tp_user$type == 'bolus',])
  Num_bolus_dups = sum(tp_user[tp_user$type == 'bolus',]$duplicated_data, na.rm = TRUE)
  bolus_dup_density = if (Num_bolus_dups > 0) {round(Num_bolus_dups / Num_bolus * 100, 2)}else{0}
  
  Num_smbg = nrow(tp_user[tp_user$type == 'smbg',])
  Num_smbg_dups = sum(tp_user[tp_user$type == 'smbg',]$duplicated_data, na.rm = TRUE)
  smbg_dup_density = if (Num_smbg_dups > 0) {round(Num_smbg_dups / Num_smbg * 100, 2)}else{0}
  
  time_sync_ratio_all = if (sum(!is.na(tp_user$timedelta_hrs), na.rm = TRUE) > 0) {
    round(sum(tp_user$timedelta_hrs == 0, na.rm = TRUE) / sum(!is.na(tp_user$timedelta_hrs), na.rm = TRUE) * 100, 2)
    }else{0}
  
  time_sync_ratio_cbg = if ( sum(tp_user$type == 'cbg' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) > 0) {
    round(sum(tp_user$timedelta_hrs == 0 & tp_user$type == 'cbg', na.rm = TRUE) / sum(tp_user$type == 'cbg' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) * 100, 2)
    }else{0}
  
  time_sync_ratio_basal = if (sum(tp_user$type == 'basal' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) > 0) {
    round(sum(tp_user$timedelta_hrs == 0 & tp_user$type == 'basal', na.rm = TRUE) / 
                                  sum(tp_user$type == 'basal' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) * 100, 2)
    }else{0}
  
  time_sync_ratio_bolus = if (sum(tp_user$type == 'bolus' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) > 0) {
    round(sum(tp_user$timedelta_hrs == 0 & tp_user$type == 'bolus', na.rm = TRUE) / 
            sum(tp_user$type == 'bolus' & !is.na(tp_user$timedelta_hrs), na.rm = TRUE) * 100, 2)
    }else{0}
  
  max_timedelta = max(tp_user$timedelta_hrs, na.rm = TRUE)
  min_timedelta = min(tp_user[tp_user$timedelta_hrs != 0,]$timedelta_hrs, na.rm = TRUE)
  hour12_diff = if (12 %in% abs(tp_user$timedelta_hrs)) {TRUE}else{FALSE}
  hour24_diff = if (24 %in% abs(tp_user$timedelta_hrs)) {TRUE}else{FALSE}
  year_diff = if (max_timedelta >= 8760 | min_timedelta <= -8760) {TRUE}else{FALSE}

#return the results  
  return(c(  Num_Records,
             Num_cbg_all,
             Num_cbg_dT,
             Num_cbg_dups,
             cbg_dup_density,
             Num_basal,
             Num_basal_dups,
             basal_dup_density,
             Num_bolus,
             Num_bolus_dups,
             bolus_dup_density,
             Num_smbg,
             Num_smbg_dups,
             smbg_dup_density,
             time_sync_ratio_all,
             time_sync_ratio_cbg,
             time_sync_ratio_basal,
             time_sync_ratio_bolus,
             max_timedelta,
             min_timedelta,
             hour12_diff,
             hour24_diff,
             year_diff ))
  
}
######################

# The apply_to_file function applies the time_dup_summary function to each Tidepool user file within a directory
# and stores the resulting summary statistics in a labeled data frame which is outpu as a .csv file.

apply_to_file = function(directory, .func) {
  
  filenames = list.files(directory, pattern = ".csv")
  
  output = data.frame(matrix(nrow = 0, ncol = 25))
  colnames(output) = c('HashId',
                       'Num_Records',
                       'Num_cbg_all',
                       'Num_cbg_dT',
                       'Num_cbg_dups',
                       'cbg_dup_density',
                       'Num_basal',
                       'Num_basal_dups',
                       'basal_dup_density',
                       'Num_bolus',
                       'Num_bolus_dups',
                       'bolus_dup_density',
                       'Num_smbg',
                       'Num_smbg_dups',
                       'smbg_dup_density',
                       'time_sync_ratio_all',
                       'time_sync_ratio_cbg',
                       'time_sync_ratio_basal',
                       'time_sync_ratio_bolus',
                       'max_timedelta',
                       'min_timedelta',
                       'hour12_diff',
                       'hour24_diff',
                       'year_diff',
                       'Missing Cols'
  )
  
  for (i in seq_along(filenames)) {
  
    filepath = file.path(directory, filenames[[i]])
    subject = read_csv(filepath, col_types = cols(.default = 'c'))
    print(i)
    output[i,1] = filenames[i]
    
    required_columns = c('deviceTime', 'deliveryType', 'duration', 'rate', 'normal', 'value', 'est.localTime', 'computerTime')
    
    if ( sum( required_columns %in% colnames(subject) ) == 8 ) {
    

      output[i, 25] = FALSE
      
    }else{
      
      output[i, 25] = TRUE
      
      if ( !('deviceTime' %in% colnames(subject)) ) {subject$deviceTime = NA}
      if ( !('deliveryType' %in% colnames(subject)) ) {subject$deliveryType = NA}
      if ( !('duration' %in% colnames(subject)) ) {subject$duration = NA}
      if ( !('rate' %in% colnames(subject)) ) {subject$rate = NA}
      if ( !('normal' %in% colnames(subject)) ) {subject$normal = NA}
      if ( !('value' %in% colnames(subject)) ) {subject$value = NA}
      if ( !('est.localTime' %in% colnames(subject)) ) {subject$est.localTime = NA}
      if ( !('computerTime' %in% colnames(subject)) ) {subject$computerTime = NA}
      
    }
  
    output[i, 2:24] = .func(subject)
    
  }
  
  write_csv(output, file.path("time_and_duplication_diagnostic.csv"))  
  
}

#Set the directory:
directory = file.path("2018-09-28-anonimized-local-time-estimate")

#Execute the apply_to_file function.
apply_to_file(directory, .func = time_dup_summary)

