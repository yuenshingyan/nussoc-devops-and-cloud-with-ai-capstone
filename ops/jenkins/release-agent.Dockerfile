FROM jenkins/inbound-agent:alpine-jdk21@sha256:eccf1a2fcfb675946e53bae9964ed0a77e9ccd93411b5d801b074c051c807a0e AS remoting
FROM python:3.14.9-alpine3.24@sha256:dbeb11d16bb95c3a7e3c25c842cb9f20cbc8c18f8be0461a4a0dcc861ad386a0

ARG TARGETARCH
RUN test "$TARGETARCH" = arm64
# ADC support in the GKE plugin avoids installing a second SDK or borrowing the host login.
RUN apk add --no-cache bash curl libstdc++ \
    && addgroup -g 1000 jenkins \
    && adduser -D -u 1000 -G jenkins -s /bin/bash jenkins \
    && mkdir -p /home/jenkins/agent \
    && chown jenkins:jenkins /home/jenkins/agent \
    && curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 \
       https://github.com/google/go-containerregistry/releases/download/v0.22.1/go-containerregistry_Linux_arm64.tar.gz \
       -o /tmp/crane.tar.gz \
    && echo '898c0cff975f898a33e8c4580bdafb0e7c02c7faa33374e946762f97c4ab7110  /tmp/crane.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/crane.tar.gz -C /usr/local/bin crane \
    && curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 \
       https://dl.google.com/dl/cloudsdk/channels/rapid/components/google-cloud-sdk-gke-gcloud-auth-plugin-linux-arm-20261016073856.tar.gz \
       -o /tmp/gke-plugin.tar.gz \
    && echo '9f53cf95d4bebfe313cd61741d75971b4cd34194fdf00780d754611d22a03528  /tmp/gke-plugin.tar.gz' | sha256sum -c - \
    && tar -xzf /tmp/gke-plugin.tar.gz -C /tmp bin/gke-gcloud-auth-plugin \
    && mv /tmp/bin/gke-gcloud-auth-plugin /usr/local/bin/ \
    && curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 15 --max-time 120 \
       https://dl.k8s.io/release/v1.36.4/bin/linux/arm64/kubectl -o /usr/local/bin/kubectl \
    && echo '0ecf44450ee6063bf19dd166a103ee6df4a9034455c2abce626e6eea657d73fb  /usr/local/bin/kubectl' | sha256sum -c - \
    && chmod 0755 /usr/local/bin/crane /usr/local/bin/gke-gcloud-auth-plugin /usr/local/bin/kubectl \
    && rm -rf /tmp/crane.tar.gz /tmp/gke-plugin.tar.gz /tmp/bin
COPY --from=remoting /opt/java/openjdk /opt/java/openjdk
COPY --from=remoting /usr/share/jenkins/agent.jar /usr/share/jenkins/agent.jar
COPY --from=remoting /usr/local/bin/jenkins-agent /usr/local/bin/jenkins-agent
ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin
# This worker executes reviewed standard-library release tooling, not package installation.
RUN python -c 'from pathlib import Path; from shutil import rmtree; import sysconfig; p=Path(sysconfig.get_path("purelib")); [rmtree(x) for x in p.glob("pip*") if x.is_dir()]; rmtree(Path(sysconfig.get_path("stdlib"))/"ensurepip")' \
    && python --version && java -version && crane version \
    && kubectl version --client=true -o json && gke-gcloud-auth-plugin --version
USER jenkins
WORKDIR /home/jenkins/agent
ENTRYPOINT ["/usr/local/bin/jenkins-agent"]
