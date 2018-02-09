FROM amazonlinux:latest
RUN yum update -y && yum -y install \
    wget \
    which \
    python27-pip \
    nfs-utils \
    sudo \
    shadow-utils.x86_64
RUN pip install awscli && pip install --upgrade awscli
RUN wget https://github.com/jmespath/jp/releases/download/0.1.2/jp-linux-amd64 -O /usr/local/bin/jp \
&& sudo chmod +x /usr/local/bin/jp
RUN useradd -ms /bin/bash batch
RUN mkdir /mnt/efs && chown batch:batch /mnt/efs
RUN mkdir /batch && chown batch:batch /batch
RUN echo "batch ALL=(root) NOPASSWD:SETENV: /batch/mount_efs.sh" >> /etc/sudoers
USER batch
WORKDIR /batch
ADD mount_efs.sh /batch/
ADD run.sh /batch/
ENTRYPOINT ["/batch/run.sh"]
