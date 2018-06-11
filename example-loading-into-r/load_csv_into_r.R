###Example of how to load a .csv file from Tidepool into R:

#Step 1, identify the pathway to the file. You can copy and paste this from your file explorer.  
#Add the name of the file to the end.  Be sure to double the \\ because a single \ indicates an escape character in R.

pathway<-"C:\\Users\\kybol\\Documents\\Github_Tidepool\\data-analytics\\example-data\\example-from-j-jellyfish.csv"


#Step 2: Use the read.csv function to save the file as an object with any name you choose:
tidepoolcsv<-read.csv(pathway)

#Step 3: Now that the .csv file is an R object, you can call commands on it:

summary(tidepoolcsv) #Summary Statistics on each variable in the dataset.

str(tidepoolcsv)  #Structure of each variable with data type and examples 

View(tidepoolcsv) #Open a spreadsheet in R of the data
 
head(tidepoolcsv,10)  #Look at the first 10 rows




