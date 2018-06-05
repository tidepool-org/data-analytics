###Example of how to load a Microsoft Excel file from Tidepool into R:

#Step 1, you need R package: readxl.  If it is not already installed in your system, then install it:

if(require("readxl")==FALSE){install.packages("readxl")}

#Then load it:

library("readxl")


#Step 2, identify the pathway to the file. You can copy and paste this from your file explorer.  
#Add the name of the file to the end.  Be sure to double the \\ because a single \ indicates an escape character in R.

pathway<-"C:\\Users\\kybol\\Documents\\Github_Tidepool\\data-analytics\\example-data\\example-from-j-jellyfish.xlsx"


#Step 3: Use the read_excel function to save the file as an object with any name you choose:

tidepoolxl<-read_excel(pathway,sheet=1)

#You need to load one sheet at a time into R.  The example Tidepool .xls file has 8 total sheets.  So repeat the above with sheet = 2 through 8
# and rename the object each time if you want all sheets.


#Step 4: Now that the .xls file is an R object, you can call commands on it:

summary(tidepoolxl) #Summary Statistics on each variable in the dataset.

str(tidepoolxl)  #Structure of each variable with data type and examples 

View(tidepoolxl) #Open a spreadsheet in R of the data
 
head(tidepoolxl, 10)  #Look at the first 10 rows



#As an alternative to the above, you can "save as" the Microsoft Excel file as a .csv file and load it as a .csv file using read.csv.   
#Excel will only allow you to save a single sheet as .csv at a time.  So again, this approach requires multiple loads.




