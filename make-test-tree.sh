#!/bin/bash

mkdir test
mkdir test/1
mkdir test/2
mkdir test/2/3
dd if=/dev/zero of=test/a bs=1000 count=1
dd if=/dev/zero of=test/b bs=1200 count=1
dd if=/dev/zero of=test/1/c bs=1400 count=1
dd if=/dev/zero of=test/1/d bs=1600 count=1
dd if=/dev/zero of=test/2/e bs=1800 count=1
dd if=/dev/zero of=test/2/f bs=2000 count=1
dd if=/dev/zero of=test/2/3/g bs=2200 count=1
dd if=/dev/zero of=test/2/3/h bs=2400 count=1
