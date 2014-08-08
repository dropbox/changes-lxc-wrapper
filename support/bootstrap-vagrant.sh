#!/bin/bash -eux

export DEBIAN_FRONTEND=noninteractive

sudo apt-get install -y python-software-properties software-properties-common
sudo add-apt-repository -y ppa:awstools-dev/awstools

sudo apt-get update -y

# Install aws cli tools
sudo apt-get install -y awscli

# Install lxc
sudo apt-get install -y libcgmanager0 lxc

# Install fpm
sudo apt-get install -y ruby-dev gcc
sudo gem install fpm --no-ri --no-rdoc
