#! /bin/bash

set +x

# pwd shall contains requirements.txt

VENVDIR=./venv
USE_SYSTEM_PACKAGES=1

if [ ! -d $VENVDIR ]; then
   echo "create Python Virtualenv: VENVDIR=${VENVDIR}"
   if [ "$USE_SYSTEM_PACKAGES" == "1" ]; then
      python -m venv --system-site-packages $VENVDIR
   else
      python -m venv $VENVDIR
   fi
   . $VENVDIR/bin/activate
   # Install local dependencies
   python -m pip install -e ./python_magnetsetup
   python -m pip install -e ./python_magnetcooling
   python -m pip install -e .
   deactivate
fi

# add option to properly quit python_magnetapi-venv using deactivate
