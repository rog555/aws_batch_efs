#!/bin/bash
if [[ -z $EFS_NAME || -z $AWS_BATCH_JOB_ID ]]; then
  echo "$0 EFS_NAME and/or AWS_BATCH_JOB_ID environment variables not set"; exit 1
fi

EFS_MOUNT_POINT=/mnt/efs/$EFS_NAME
mkdir $EFS_MOUNT_POINT

echo "* df -h"
df -h

# mount EFS filesystem to mount point and chown to batch user
# need -E so AWS_SHARED_CREDENTIALS_FILE env var is available to mount_efs.sh
sudo -E /batch/mount_efs.sh $EFS_NAME $EFS_MOUNT_POINT
if [[ $? -ne 0 ]]; then
  echo "$0: unable mount $EFS_NAME to $EFS_MOUNT_POINT"; exit 1
fi

echo "* df -h"
df -h

echo "* ls -l $EFS_MOUNT_POINT/*"
ls -l $EFS_MOUNT_POINT/*

BATCH_DIR=$EFS_MOUNT_POINT/$AWS_BATCH_JOB_ID
echo "* mkdir $BATCH_DIR"
mkdir $BATCH_DIR

echo "* ls -l $BATCH_DIR/*"
ls -l $BATCH_DIR/*

TEST_FILE=$BATCH_DIR/test_file.txt
echo "* writing $TEST_FILE"
echo $(date) > $TEST_FILE

echo "* ls -l $BATCH_DIR/*"
ls -l $BATCH_DIR/*

echo "* reading $TEST_FILE"
cat $BATCH_DIR/test_file.txt

echo "* removing $BATCH_DIR"
rm -rf $BATCH_DIR

echo "* ls -l $EFS_MOUNT_POINT/*"
ls -l $EFS_MOUNT_POINT/*

echo "COMPLETE"