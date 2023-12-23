#!/bin/sh

echo
echo "--------------------------------------------------------------"
echo "start ltp posix tests!"
echo "--------------------------------------------------------------"

set +e
#fetch https://github.com/linux-test-project/ltp/releases/download/20230929/ltp-full-20230929.tar.xz
ls /meta
tar xf /meta/ltp-full-20230929.tar.xz

cd ltp-full-20230929
pkg inst -y gmake
pkg inst -y py32-junit-xml
python3 /meta/run.py test ltp_out.json
python3 /meta/format_junit.py ltp_out.json ltp_junit.xml
