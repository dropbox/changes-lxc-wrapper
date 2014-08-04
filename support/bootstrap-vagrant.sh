#!/bin/bash -eux

export DEBIAN_FRONTEND=noninteractive

sudo apt-get update -y

# Install lxc
sudo apt-get install -y libcgmanager0 lxc

# Install fpm
sudo apt-get install -y ruby-dev gcc
sudo gem install fpm --no-ri --no-rdoc
