FROM moby/buildkit:v0.34.1-rootless@sha256:f68752a5a94acfcdad2d07867b7075601a421638e17fc5f28efc1c814d0c4f89

# Populate the named socket volume from this image before the client mounts it read-only.
# Share only the BuildKit socket directory, not RootlessKit's other runtime sockets.
RUN mkdir -p /run/user/1000/buildkit && chmod 0700 /run/user/1000/buildkit
