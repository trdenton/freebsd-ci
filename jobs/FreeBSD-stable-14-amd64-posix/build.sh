#!/bin/sh

export TARGET=amd64
export TARGET_ARCH=amd64

export USE_TEST_SUBR="
disable-dtrace-tests.sh
disable-zfs-tests.sh
disable-notyet-tests.sh
run-ltp-posix.sh
run.py
fixes.patch
format_junit.py
"

export USE_DL_CONTENT="
https://github.com/linux-test-project/ltp/releases/download/20230929/ltp-full-20230929.tar.xz
"

sh -x freebsd-ci/scripts/test/run-tests.sh
