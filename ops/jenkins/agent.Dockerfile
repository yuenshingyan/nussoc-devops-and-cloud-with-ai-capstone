FROM jenkins/inbound-agent:jdk21@sha256:64a27e807d216d527a7f5224e6ff9733b5cbd8650db3b5dfd0aea3b94949460f AS remoting
FROM ghcr.io/astral-sh/uv:0.9.21@sha256:15f68a476b768083505fe1dbfcc998344d0135f0ca1b8465c4760b323904f05a AS uv
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
ENV JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/java/openjdk/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy
RUN python --version && uv --version && git --version && java -version
USER jenkins
WORKDIR /home/jenkins/agent
ENTRYPOINT ["/usr/local/bin/jenkins-agent"]
