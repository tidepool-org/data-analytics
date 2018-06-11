###Example of how to load a .json file from Tidepool into R:

#Step 1, you need R package: jsonlite.  If it is not already installed in your system, then install it:

if(require("jsonlite")==FALSE){install.packages("jsonlite")}

#Then load it:

library("jsonlite")


#Step 2, identify the pathway to the file:

pathway<-"../example-data/example-from-j-jellyfish.json"


#Step 3: Use the fromJSON function to save the file as an object with any name you choose:
tidepooljson<-fromJSON(pathway)

#Step 4: Now that the .json file is an R object, you can call commands on it:

#Summary Statistics on each variable in the dataset.
summary(tidepooljson) 

#Structure of each variable with data type and examples
str(tidepooljson)   

#Open a spreadsheet in R of the data
View(tidepooljson) 

#Look at the first 10 rows 
head(tidepooljson, 10)

#To save the data as a .csv file:
#Set outpath:
outpath<-"../example-data/example-from-j-jellyfish2.csv"
write.csv(tidepooljson, file=outpath)







