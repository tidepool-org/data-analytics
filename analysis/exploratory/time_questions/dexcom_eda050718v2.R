
#set location of files:

pathway<-"C:\\Users\\kybol\\OneDrive - Kyle Bolduc\\TidePool\\dexcom_json"

# Create funtion to count days with estimated timezone, and count days with
# timezones that are not the home (most frequent) timezone.  Find the percentage
# out of home timezone.

days.away<- function(pathway) {
  
  #install packages (if necessary) and load:
  if(require("dplyr")==FALSE){install.packages("dplyr")}
  library("dplyr")
  
  if(require("lubridate")==FALSE){install.packages("lubridate")}
  library("lubridate")
  
  if(require("jsonlite")==FALSE){install.packages("jsonlite")}
  library("jsonlite")
  
  id<-c()             #initialize lists         
  est.days<-c()
  outoftz<-c()
  
#  timezones<-
#    read_csv("C:\\Users\\kybol\\OneDrive - Kyle Bolduc\\TidePool\\timezones.csv")
 
  jsonnames<-list.files(pathway)        #get list of files in directory
  
  for(i in 1:length(jsonnames)){        #loop through files in directory
    
    filepath<-paste0(pathway,"\\",jsonnames[[i]])     #point to file in dir.
    pwd<-fromJSON(filepath)                         #load in json file

    pwd <- pwd[!is.na(pwd$est.timezone),] #keep only dates with an estimated timezone
    
    pwd$utc_offset<-
    tzoffset(pwd$est.timezone)  #custom function to convert all timezone alias to standard UTC offset string.
       
    hometz<-names(which.max(table(pwd$utc_offset)))  #find most frequent timezone "home"

    pwd$day<-as.Date(ymd_hms(pwd$est.localTime))  #convert variable to Date & single day  

    pwd$travel<-ifelse(pwd$utc_offset==hometz,0,1) #code travel, 0 is no 1 is yes

    travelday<-           #look at all records in the day and see if ANY are 1,
      pwd %>%                 #if yes, then its a travel day.
        group_by(day) %>%
        summarise(away=max(travel))      #the max of 0s & 1s will take a 1.

    id[i]<-jsonnames[i]                   #save the id
    est.days[i]<- length(unique(pwd$day))  #save the count of days with tz estimate
    outoftz[i]<- sum(travelday$away)      #save the count of traveldays  
  }  
  
    traveltrack<-data.frame(id,est.days,outoftz)  #load the saved features in dateframe
    
    traveltrack$percent_travel<-with(traveltrack, outoftz/est.days)  #add percent travel column
    
    return(traveltrack)  #function return of the new dataframe
}

tt<-
  days.away(pathway)   #call the funtion with pathway to the files.
  

tt

write_csv(tt,"C:\\Users\\kybol\\OneDrive - Kyle Bolduc\\TidePool\\traveldays.csv")
