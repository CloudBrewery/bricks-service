#!/bin/bash
export BUILD_DIR=/tmp/bricks-occupant

echo "--------------------------"
echo "Prepare build env"
echo "--------------------------"

echo "
deb mirror://mirrors.ubuntu.com/mirrors.txt precise main restricted universe multiverse
deb mirror://mirrors.ubuntu.com/mirrors.txt precise-updates main restricted universe multiverse
deb mirror://mirrors.ubuntu.com/mirrors.txt precise-backports main restricted universe multiverse
deb mirror://mirrors.ubuntu.com/mirrors.txt precise-security main restricted universe multiverse
"|cat - /etc/apt/sources.list > /tmp/out && mv /tmp/out /etc/apt/sources.list

#Make build dirs
mkdir $BUILD_DIR
cd $BUILD_DIR

echo "--------------------------"
echo "Installing occupant"
echo "--------------------------"

git clone https://bitbucket.org/clouda/bricks-occupant.git 
cd bricks-occupant
pip install -r requirements.txt 
python setup.py install
cd /
rm -Rf $BUILD_DIR

echo "--------------------------"
echo "Configure supervisor"
echo "--------------------------"

echo "[program:bricks_occupant]
command = bricks_occupant
autorestart = true" > /etc/supervisor/conf.d/bricks_occupant.conf

service supervisor stop
service supervisor start
