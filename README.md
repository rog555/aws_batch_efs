# aws_batch_efs

Example on how to mount an AWS EFS filesystem from within a managed AWS Batch job using standard [Amazon ECS-Optimized AMI](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html)

Reason to do this is when >~8GB of disk is required and you don't wan't to use a custom AMI that 
involves messing around with EBS volumes and SSH'ing into instances (see "Creating the custom AMI for AWS Batch" 
[here](https://aws.amazon.com/blogs/compute/building-high-throughput-genomic-batch-workflows-on-aws-batch-layer-part-3-of-4/))

Good AWS forum post [How much disk space comes on a managed environment?](https://forums.aws.amazon.com/thread.jspa?threadID=250705) highlighting the current limitation

> Managed Compute Environments currently launch the ECS Optimized AMI which includes an 8GB volume for the operating system and a 22GB volume for Docker image and metadata storage. The default Docker configuration allocates up to 10GB of this storage to each container instance. You can read more about this AMI at:

> http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html

> For now, your best option is to use Unmanaged Compute Environments which allow you to run instances using any AMI meeting our minimum system requirements. 

Downside is that EFS costs 3x more than EBS, maybe when the [ECS Agent supports volume drivers](https://github.com/aws/amazon-ecs-agent/issues/236) this will be easier & cheaper

Mounting EFS from within running batch container is only possible with the batch [job definition parameter](https://docs.aws.amazon.com/batch/latest/userguide/job_definition_parameters.html) set to True 

> When this parameter is true, the container is given elevated privileges on the host container instance (similar to the root user). This parameter maps to Privileged in the Create a container section of the Docker Remote API and the --privileged option to docker run.

### Unmanaged AWS Batch

For unmanaged batch compute environments, see:

 1. [How do I increase the default 10 GiB storage limit with Docker container volumes for ECS?](https://aws.amazon.com/premiumsupport/knowledge-center/increase-default-ecs-docker-limit/)
 2. [Bootstrapping Container Instances with Amazon EC2 User Data](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/bootstrap_container_instance.html)

### General AWS Batch Links

 1. [AWS re:Invent 2017: AWS Batch: Easy and Efficient Batch Computing on AWS (CMP323)](https://www.youtube.com/watch?v=8dApnlJLY54)

## Setup

NOTE: this bit isnt fully tested, but should be enough to give you an idea

 1. Ensure VPC private subnet has auto-assign public IP enabled or is behind NAT gateway or batch job
    will remain at RUNNABLE state
 2. Create ECS IAM Role for batch job with inline policy:
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
 3. Create managed batch compute environment with private subnet above (with `Enable user-specified AMI ID` unchecked)
 4. Create a **privileged** batch job definition `aws_batch_efs` using IAM role created above
 5. Create batch job queue `aws_batch_efs_queue`
 6. Create ECR repository `aws_batch_efs`
 7. Create EFS filesystem with name `batch` and enable mount target in same subnet(s) as batch compute environment
 8. Install docker and build image: `./build.sh`
 9. Update `AWS_ACCOUNT_ID` in `push.sh` and any other variables required and push docker image to ECR: `./push.sh`
 11. submit job either through the console or using `batch.py` (need to `pip install gevent boto3` if not already installed)

## Output

The following is happening here:

 1. `batch.py` submits job passing in environment variable `EFS_NAME=batch` and then waits for it to complete before dumping the log of the job
 2. AWS Batch container starts and invokes `run.sh` entrypoint
 3. `run.sh` sudo executes `mount_efs.sh` passing the name of the EFS filesystem `batch` and mount point `/mnt/efs/batch`
 4. `mount_efs.sh` looks up the EFS mount target IP for the subnet the batch container is running in and mounts it
 5. `run.sh` creates a unique temporary directory below `/mnt/efs/batch` based on `AWS_BATCH_JOB_ID` environment variable
    that AWS Batch makes available to the container
 6. `run.sh` writes and reads a file
 7. `run.sh` deletes temporary directory from EFS

```
$ ./batch.py submit -q aws_batch_efs_queue -d aws_batch_efs -j aws_batch_efs_1 -e EFS_NAME=batch
submitted job aws_batch_efs_1 from definition ID aws_batch_efs:1 with ID 58e88733-1d61-4912-a8bg-934249940edc
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

## batch.py other stuff

Some other functionality of `batch.py`

### list jobs

```
$ export BATCH_QUEUE=aws_batch_efs_queue
$ ./batch.py jobs
SUBMITTED       PENDING         RUNNABLE        STARTING        RUNNING         SUCCEEDED       FAILED
                                                                                                aws_batch_efs_2
                                                                                aws_batch_efs_1
                                aws_batch_efs_3
```

### get job logs

```
$ export BATCH_QUEUE=aws_batch_efs_queue
$ ./batch.py log -j aws_batch_efs_2
/batch/run.sh EFS_NAME and/or AWS_BATCH_JOB_ID environment variables not set
```

### wait for submitted job to complete

```
$ export BATCH_QUEUE=aws_batch_efs_queue
$ ./batch.py wait -j aws_batch_efs_3
2018-02-09T02:21:09Z status is SUBMITTED
2018-02-09T02:21:19Z status is RUNNABLE
```

### submit unique job based on name

```
$ export BATCH_QUEUE=aws_batch_efs_queue
$ export BATCH_DEFN_NAME=aws_batch_efs
$ ./batch.py submit -j aws_batch_efs_3
ERROR: job 'aws_batch_efs_3' already processing with status RUNNABLE
```


