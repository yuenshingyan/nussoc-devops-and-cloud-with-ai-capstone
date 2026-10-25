FROM moby/buildkit:v0.34.1-rootless@sha256:f68752a5a94acfcdad2d07867b7075601a421638e17fc5f28efc1c814d0c4f89 AS buildkit
FROM jenkins/inbound-agent:jdk21@sha256:64a27e807d216d527a7f5224e6ff9733b5cbd8650db3b5dfd0aea3b94949460f AS remoting
FROM ghcr.io/astral-sh/uv:0.9.21@sha256:15f68a476b768083505fe1dbfcc998344d0135f0ca1b8465c4760b323904f05a AS uv
FROM python:3.14.7-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56 AS scanner
ARG TARGETARCH
# The local Jenkins worker is ARM64. Reject another target rather than install the wrong binary.
RUN test "$TARGETARCH" = "arm64"
# This immutable release asset was verified with GitHub attestations and its Sigstore bundle.
ADD --checksum=sha256:e174dff2a6dba5e3ae41f8d0537a6324405bd08132497340304c6b20e0f16a1f https://github.com/aquasecurity/trivy/releases/download/v0.76.1/trivy_0.76.1_Linux-ARM64.tar.gz /tmp/trivy.tar.gz
RUN tar -xzf /tmp/trivy.tar.gz -C /usr/local/bin trivy && chmod 0755 /usr/local/bin/trivy

FROM python:3.14.7-slim-bookworm@sha256:82bc3c539b8813ada9d68c63b40158fa002f7f33de9bf3312a3dfdc0620dff56

# Keep the approved interpreter: uv 0.9.21's download catalogue lacks Python 3.14.7.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends git libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 jenkins \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash jenkins \
    && mkdir -p /home/jenkins/agent \
    && chown jenkins:jenkins /home/jenkins/agent
COPY --from=remoting /opt/java/openjdk /opt/java/openjdk
COPY --from=remoting /usr/share/jenkins/agent.jar /usr/share/jenkins/agent.jar
COPY --from=remoting /usr/local/bin/jenkins-agent /usr/local/bin/jenkins-agent
COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=buildkit /usr/bin/buildctl /usr/local/bin/buildctl
COPY --from=scanner /usr/local/bin/trivy /usr/local/bin/trivy
ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
RUN python --version && uv --version && git --version && java -version && buildctl --version && trivy --version
USER jenkins
WORKDIR /home/jenkins/agent
ENTRYPOINT ["/usr/local/bin/jenkins-agent"]
