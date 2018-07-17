############################################################################
# description: Load donor data in Microsoft xls format into r data frame by 
#              invidual sheet or as a merged data frame.
# version: 0.0.1
# created: 2018-07-2018
# author: Kyle Bolduc
# dependencies:
#     * requires tidepool analysis environment (see readme for instructions)
#     * readxl
#     * readr
#     * dplyr
# 
# license: BSD-2-Clause
############################################################################


###Example of how to load a Microsoft Excel file from Tidepool into R:

#Step 1, you need R package: readxl.  If it is not already installed in your system, then install it:

if (require("readxl") == FALSE) {install.packages("readxl")}

#Then load it:

library(readxl)

#Step 2, identify the pathway to the file:

pathway = file.path("..", "..", "example-data", "example-from-j-jellyfish.xlsx")


#Step 3: Use the read_excel function to save the file as an object with any name you choose:

tidepoolxl = read_excel(pathway, sheet = 1)

#You need to load one sheet at a time into R.  The example Tidepool .xls file has 8 total sheets.  So repeat the above with sheet = 2 through 8
# and rename the object each time if you want all sheets.


#Step 4: Now that the .xls file is an R object, you can call commands on it:

#Summary Statistics on each variable in the dataset.
summary(tidepoolxl) 

#Structure of each variable with data type and examples 
str(tidepoolxl)  

#Open a spreadsheet in R of the data
View(tidepoolxl) 
 
#Look at the first 10 rows
head(tidepoolxl, 10)  


#As an alternative to the above, you can "save as" the Microsoft Excel file as a .csv file and load it as a .csv file using the read.csv() function.   


#To save the file as a .csv file:
#Set outpath:
outpath = file.path("..", "..", "example-data", "example-from-j-jellyfish2.csv")

write.csv(tidepoolxl, file = outpath)


#To combine all Excel sheets into a single dataframe:


#Install the readr package.
if (require("readr") == FALSE) {install.packages("readr")}
library(readr)


#Run xl_sheet_import function:
xl_sheet_import <- function(path=pathway, n=1){
  
  #Import the data into an unnamed dataframe:
  df = read_excel(path, sheet = n, col_names = FALSE)[-1,]
  
  #Collect the column names (first row of the sheet):
  namesxl = read_excel(path, sheet = n, col_names = FALSE)[1,]
  
  #Apply the names to the dataframe:

  colnames(df) = namesxl

  return(df)
}

#Run merge_sheets function to collect and merge all of the sheets, using a recursive full_join() with the above xl_sheet_import():

merge_sheets <- function(path=pathway, n=length(excel_sheets(pathway))){

    if (n <= 1) {
      return(xl_sheet_import(path))
    }else{
      return(full_join(merge_sheets(path, n = n - 1), xl_sheet_import(path, n)))
    }
  
}

#Finally, use the readr function, type_convert(), to detect the data types of each column:
combinedxl = readr::type_convert(merge_sheets(path = pathway))


#Inspect the results:
str(combinedxl)

dim(combinedxl)

View(combinedxl)






