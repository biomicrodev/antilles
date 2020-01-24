# Antilles
An image processing pipeline for profiling the cellular response around microdevices.

# Installation
## Installing openslide
Download the Windows binary for openslide-python for the appropriate architecture (32-bit vs 64-bit), and unzip into a known location.

Unfortunately, the dll search paths in Windows contain dlls that have the same name as the dlls required for openslide, so the path to the bin folder in the Windows binary has to be added to the beginning of the path directly, using the <code>os</code> python library.

This can be done by putting the following code at the top of the file:

```python
import os
os.environ['PATH'] = r'C:\path\to\openslide\bin' + ';' + os.environ['PATH']
```
