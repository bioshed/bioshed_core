#!/bin/bash
cmdline=("$@")
cmd=$1
cimg=$2
if [ $cmd == "runlocal" ]
then
  args=${cmdline[@]:1}
  runcmd="sudo docker run 700080227344.dkr.ecr.us-west-2.amazonaws.com/${cimg,,}:latest "${args// / }
  echo $runcmd
  $runcmd
fi
