# Daily Blood Glucose vs Carb Analysis

### About

This code parses through Tidepool formatted .xlsx files and reports information regarding daily blood glucose averages, daily carb intake, and the relationships between these two.

### Usage

This code can be run with R or RStudio using R version 3.4.3 or newer
Required libraries: `readxl`, `ggplot2`, and `hexbin`
Install these packages from the R console using the commands:

```
install.packages('readxl')
install.packages('ggplot2')
install.packages('hexbin')
```

### Options

Before running, set your working directory and preferred blood glucose value units.  
The code can be run as a whole, or line by line. 

### Output Variables

The following variables are collected for analysis:

`total_daily_carbs`: A vector of the sums of total carbs recorded for each day  
`meanBG`: A vector of the average blood glucose values for each day  
`medianBG`: A vector of the median blood glucose values for each day  
`stddevBG`: A vector of the standard deviation of blood glucose values for each day  

### Graphical Output

This version provides the following graphical output:

- Histogram of total daily carbs consumed for the analyzed set
- Continuous density scatterplot
- Hexbin density scatterplot
- Boxplot of binned daily carb consumption vs variable of choice (e.g. 0-10 carbs, 10-20 carbs, 20-30 carbs, etc)


