# tpanalyze.py (Tidepool Analysis Tools)
This python package contains analysis tools and utility functions that
may be helpful when analyzing Tidepool data. This package is currently in
development and you will need to add the following code snippet to your
script to load the package:

```python
import sys
import os
cwd = os.getcwd()
packagePath = cwd[:(cwd.find("data-analytics") + 15)]
sys.path.append(packagePath)
sys.path.append(os.path.join(packagePath, "tpanalyze"))
import tpanalyze as tp
```

## Adding modules and functions to the package
If you want to add to this package, please add the function under the
tpanalyze directory, AND please update the _____init___.py so that the
function is initiated when the package is loaded.

## Example
An example of loading the pacakge is located here:

```/data-analytics/examples/load-tpanalyze-package.py```
