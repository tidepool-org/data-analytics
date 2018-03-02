# data-analytics
Home for code we use to analyze data for the Tidepool Big Data Donation project and similar.

## About our use of Python
We use the [Anaconda](https://www.anaconda.com/) distribution of Python.  
You do not require the full Anaconda installer, you only need to use Miniconda to get started.

## Getting started
1. Install [Miniconda](https://conda.io/miniconda.html) for your platform. You can also install the full Anaconda package if you prefer.
1. In a terminal, change into the directory of the tool you wish to use.
1. Run `conda env create`. This will download all of the package dependencies and install them in a virtual environment.

## To list the Virtual Environments
Run `conda env list`

## To use the Virtual Envrionment
Run `conda activate <tool>`, for example `conda activate get-donor-data`.  
Once you have finished running the tools, you can run `conda deactivate`.  
