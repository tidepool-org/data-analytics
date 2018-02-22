#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: load environment variables (secrets into the workspace)
version: 0.0.1
created: 2018-02-21
author: Ed Nykaza
license: BSD-2-Clause
"""

# settings.py
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)
