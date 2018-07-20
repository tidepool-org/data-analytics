############################################################################
# description: Load donor data in csv format into r data frame
# version: 0.0.1
# created: 2018-07-2018
# author: Kyle Bolduc
# dependencies:
#     * requires tidepool analysis environment (see readme for instructions)
#     * base R only - no dependencies
# 
# license: BSD-2-Clause
############################################################################


###Example of how to load a .csv file from Tidepool into R:


#Step 1, identify the pathway to the file. 

pathway = file.path("..", "..", "example-data", "example-from-j-jellyfish.csv")


#Step 2: Use the read.csv function to save the file as an object with any name you choose:
tidepoolcsv = read.csv(pathway)

#Step 3: Now that the .csv file is an R object, you can call commands on it:

#Summary Statistics on each variable in the dataset.
summary(tidepoolcsv) 

#Structure of each variable with data type and examples
str(tidepoolcsv)   

#Open a spreadsheet in R 
View(tidepoolcsv) 
 
#Look at the first 10 rows
head(tidepoolcsv, 10)  


#To save the .csv file:
#Set outpath:
outpath = file.path("..", "..", "example-data", "example-from-j-jellyfish2.csv")

write.csv(tidepoolcsv, file = outpath)


