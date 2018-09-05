# tidas.py (Tidepool Analysis Tools)
This python package contains analysis tools and utility functions that
may be helpful when loading, cleaning, and analyzing Tidepool data. This
package is currently in development and you will need to add the following
code snippet to your script to load the package:

```python
nameDataAnalyticsRepository = "data-analytics"
packagePath = cwd[:(cwd.find(nameDataAnalyticsRepository) +
                    len(nameDataAnalyticsRepository) + 1)]
sys.path.append(packagePath)
sys.path.append(os.path.join(packagePath, "tidas"))
import tidas as td
```

## Adding modules and functions to the package
If you want to add to this package, please add the function under the
tpanalyze directory, AND please update the \__init\__.py so that the
function is initiated when the package is loaded.

## Example
An example of loading the package is located here:

```/data-analytics/examples/load-tidas-package.py```
