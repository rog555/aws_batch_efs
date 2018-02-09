#!/bin/bash
# mount EFS filesystem to mount point and chown to user
if [[ $# -lt 2 ]]; then
  echo "$0 <efs_name> <mount_point> [efs_ip]"; exit 1
fi
EFS_NAME=$1
EFS_MOUNT_POINT=$2
EFS_IP=$3

# get EFS IP for EFS in current subnet - role policy needs IAM permissions
# elasticfilesystem:DescribeMountTargets and elasticfilesystem:DescribeFileSystems
if [[ -z $EFS_IP ]]; then 

  # needed to find jp
  export PATH=/usr/local/bin:$PATH

  # get region and subnet from instance metadata
  AWS_AVAIL_ZONE=`curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone`
  AWS_REGION=${AWS_AVAIL_ZONE::-1}
  INTERFACE=$(curl --silent http://169.254.169.254/latest/meta-data/network/interfaces/macs/)
  SUBNET_ID=$(curl --silent http://169.254.169.254/latest/meta-data/network/interfaces/macs/${INTERFACE}/subnet-id)

  # get filesystem ID
  EFS_ID=$(aws efs describe-file-systems --region $AWS_REGION | jp -u "FileSystems[?Name=='$EFS_NAME'].FileSystemId | [0]")
  if [[ $? -ne 0 || -z $EFS_ID || $EFS_ID == "null" ]]; then
    echo "$0: unable to find EFS ID for EFS name '$EFS_NAME'"; exit 1
  fi

  # get mount targets for filesystem ID
  EFS_IP=$(aws efs describe-mount-targets --file-system-id $EFS_ID --region $AWS_REGION | jp -u "MountTargets[?SubnetId=='$SUBNET_ID'].IpAddress | [0]")
  if [[ $? -ne 0 || -z $EFS_IP || $EFS_IP == "null" ]]; then
    echo "$0: unable to find EFS mount target / IP in subnet $SUBNET_ID for EFS name '$EFS_NAME'"; exit 1
  fi
fi

# mount
mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2 $EFS_IP:/ $EFS_MOUNT_POINT
if [[ $? -ne 0 ]]; then
  echo "unable to mount EFS $EFS_NAME IP $EFS_IP to $EFS_MOUNT_POINT, exit code $?"; exit 1
fi
echo "$0: mounted EFS $EFS_NAME in subnet $SUBNET_ID with IP $EFS_IP to $EFS_MOUNT_POINT"