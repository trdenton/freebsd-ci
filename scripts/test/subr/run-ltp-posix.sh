#!/bin/sh

echo
echo "--------------------------------------------------------------"
echo "start ltp posix tests!"
echo "--------------------------------------------------------------"

set +e
#fetch https://github.com/linux-test-project/ltp/releases/download/20230929/ltp-full-20230929.tar.xz
tar xf ltp-full-20230929.tar.xz


cd ./ltp-full-20230929
python3 ../run.py test ltp_out.json
python3 ../format_junit.py ltp_out.json ltp_junit.xml
