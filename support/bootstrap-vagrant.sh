#!/bin/bash -eux

export DEBIAN_FRONTEND=noninteractive

sudo apt-get update -y
sudo apt-get install -y libcgmanager0 lxc
