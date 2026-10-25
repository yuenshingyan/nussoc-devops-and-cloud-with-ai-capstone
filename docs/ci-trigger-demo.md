# Isolated Step 4.4 CI gate demonstration

This branch is deliberately separate from main and must never be merged into it.
Its Jenkinsfile is unchanged from reviewed main at f167a76. The branch will receive
one passing health-contract test, one deliberately incorrect expected response,
and a revert restoring the passing test. Application code remains unchanged.

Only this repository's administrator-controlled demo job may use this branch.
No registry/cloud credentials, image publishing, or deployment are part of the demo.
The final passing branch head and disabled job history are retained as evidence.
