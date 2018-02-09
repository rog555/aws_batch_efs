# aws_batch_efs

Example on how to mount an AWS EFS filesystem from within running AWS Batch job

## Setup

 1. Ensure VPC private subnet has auto-assign public IP enabled or is behind NAT gateway or batch job will remain at RUNNABLE
 2. Create ECS IAM Role for batch job with inline policy
    ```
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "1",
                "Effect": "Allow",
                "Action": [
                    "elasticfilesystem:DescribeMountTargets",
                    "elasticfilesystem:DescribeFileSystems"
                ],
                "Resource": "*"
            }
        ]
    }
    ```
 3. Create managed batch compute environment with private subnet
 4. Create job definition `aws_batch_efs` with IAM role created above
 5. Create batch job queue `aws_batch_efs_queue`
 6. Create ECR repository `aws_batch_efs`
 7. Create EFS filesystem with name `batch` and enable mount target in same subnet(s) as batch compute environment
 8. Install docker and build image: `./build.sh`
 9. Update `AWS_ACCOUNT_ID` in `push.sh` and any other variables required and push docker image to ECR: `./push.sh`
 11. submit job either through the console or using `submit_job.py` (need to `pip install gevent boto3` if not already installed)

## Example Output

```
$ ./batch.py submit -q aws_batch_efs_queue -d aws_batch_efs -j aws_batch_efs_1 -e EFS_NAME=batch
submitted job aws_batch_efs_1 from definition ID aws_batch_efs:1 with ID 6278155d-5f3b-4b4f-b1a7-4cc33947a4cb
2018-02-09T00:27:27Z status is SUBMITTED
2018-02-09T00:27:37Z status is RUNNABLE
2018-02-09T00:27:47Z status is RUNNING
2018-02-09T00:27:57Z status is SUCCEEDED
* df -h
Filesystem                                                                                        Size  Used Avail Use% Mounted on
/dev/mapper/docker-202:1-263304-c6aaf921c8d8ffccd40e2ag49a1e21c1efd8cb033b89ea2f44e352acbe2a760d  9.8G  382M  8.9G   5% /
tmpfs                                                                                             3.9G     0  3.9G   0% /dev
tmpfs                                                                                             3.9G     0  3.9G   0% /sys/fs/cgroup
/dev/xvda1                                                                                        7.8G  662M  7.1G   9% /etc/hosts
shm                                                                                                64M     0   64M   0% /dev/shm
/batch/mount_efs.sh: mounted EFS batch in subnet subnet-957cd9a2 with IP 10.0.1.102 to /mnt/efs/batch
* df -h
Filesystem                                                                                        Size  Used Avail Use% Mounted on
/dev/mapper/docker-202:1-263304-c6aaf921c8d8ffccd40e2ag49a1e21c1efd8cb033b89ea2f44e352acbe2a760d  9.8G  382M  8.9G   5% /
tmpfs                                                                                             3.9G  4.0K  3.9G   1% /dev
tmpfs                                                                                             3.9G     0  3.9G   0% /sys/fs/cgroup
/dev/xvda1                                                                                        7.8G  662M  7.1G   9% /etc/hosts
shm                                                                                                64M     0   64M   0% /dev/shm
10.0.1.102:/                                                                                      8.0E     0  8.0E   0% /mnt/efs/batch
* ls -l /mnt/efs/batch/*
ls: cannot access /mnt/efs/batch/*: No such file or directory
* mkdir /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc
* ls -l /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/*
ls: cannot access /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/*: No such file or directory
* writing /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/test_file.txt
* ls -l /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/*
-rw-r--r-- 1 batch batch 28 Feb  9 00:27 /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/test_file.txt
* reading /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc/test_file.txt
Fri Feb 9 00:27:46 UTC 2018
* removing /mnt/efs/batch/58e88733-1d61-4912-a8bg-934249940edc
* ls -l /mnt/efs/batch/*
ls: cannot access /mnt/efs/batch/*: No such file or directory
COMPLETE
```





