# tidals.py (<u>tid</u>epool-<u>da</u>ta-an<u>al</u>ysis too<u>ls</u>)
This python package contains analysis tools and utility functions that
may be helpful when loading, cleaning, and analyzing Tidepool data. This
package is currently in development.

## Use our analysis tools

If you want to use these tools, you have two options:

1. Load our conda environment (see our repository [readme](https://github.com/tidepool-org/data-analytics/blob/master/README.md) for details), or
2. Add the tidals path to your python script. Here is an example:

```python
import os
import sys

nameDataAnalyticsRepository = "data-analytics"
packagePath = os.getcwd()[:(os.getcwd().find(nameDataAnalyticsRepository) +
                          len(nameDataAnalyticsRepository) + 1)]
sys.path.append(os.path.abspath(os.path.join(packagePath, "tidepool-analysis-tools")))
import tidals as td
```

## Contribute to the tidals package
If you want to add to this package, please submit a pull request
