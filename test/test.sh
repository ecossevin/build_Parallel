#!/bin/bash

#Generate code to test (in loki and tmp repo)
./parallel.sh

#Run test
./diff_parallel.sh
