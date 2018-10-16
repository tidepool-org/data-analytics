#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parts of this file were taken from
https://packaging.python.org/tutorials/packaging-projects/
"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tidals",
    version="0.0.1",
    author="Ed Nykaza",
    author_email="ed@tidepool.org",
    description="Tidepool Data Analytics or Analysis Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tidepool-org/data-analytics/tree/master/tidals",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD-2-Clause",
        "Operating System :: OS Independent",
    ],
)
