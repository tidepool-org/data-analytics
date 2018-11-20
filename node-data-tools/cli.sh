#!/bin/sh
# -*- coding: utf-8, tab-width: 2 -*-
for PROG in node{js,}; do
  </dev/null "$PROG" 2>/dev/null && break
done

exec -a "$0" "$PROG" -r esm -- index.js "$@"; exit $?

