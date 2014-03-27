#!/bin/bash
export BUILD_DIR=/tmp/bricks-occupant

echo "--------------------------"
echo "Prepare build env"
echo "--------------------------"

#Make build dirs
mkdir $BUILD_DIR
cd $BUILD_DIR

echo "--------------------------"
echo "Installing deps"
echo "--------------------------"

apt-get update
apt-get install -y git python-dev gcc supervisor python-pip

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
