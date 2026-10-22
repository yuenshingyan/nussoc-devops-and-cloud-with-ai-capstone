FROM jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --latest=false --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY --chown=jenkins:jenkins jenkins.yaml /usr/share/jenkins/jenkins.yaml
COPY --chown=jenkins:jenkins checkout-job.groovy /usr/share/jenkins/checkout-job.groovy
ENV CASC_JENKINS_CONFIG=/usr/share/jenkins/jenkins.yaml
