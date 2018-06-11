###Example of how to load a .json file from Tidepool into R:

#Step 1, you need R package: jsonlite.  If it is not already installed in your system, then install it:

if(require("jsonlite")==FALSE){install.packages("jsonlite")}

#Then load it:

library("jsonlite")


#Step 2, identify the pathway to the file. You can copy and paste this from your file explorer.  
#Add the name of the file to the end.  Be sure to double the \\ because a single \ indicates an escape character in R.

pathway<-"C:\\Users\\kybol\\Documents\\Github_Tidepool\\data-analytics\\example-data\\example-from-j-jellyfish.json"



#Step 3: Use the fromJSON function to save the file as an object with any name you choose:
tidepooljson<-fromJSON(pathway)

#Step 4: Now that the .csv file is an R object, you can call commands on it:

summary(tidepooljson) #Summary Statistics on each variable in the dataset.

str(tidepooljson)  #Structure of each variable with data type and examples 

View(tidepooljson) #Open a spreadsheet in R of the data
 
head(tidepooljson, 10)  #Look at the first 10 rows







