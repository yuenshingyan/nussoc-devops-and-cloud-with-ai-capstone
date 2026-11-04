import hudson.ExtensionList
import hudson.model.Job
import hudson.model.Node
import hudson.model.Queue
import hudson.model.queue.CauseOfBlockage
import hudson.model.queue.QueueTaskDispatcher

// This is administrator-owned startup code, never loaded from an upstream build artifact.
class FinsecureReleaseBlockage extends CauseOfBlockage {
    final String message

    FinsecureReleaseBlockage(String message) { this.message = message }

    @Override String getShortDescription() { message }
}

class FinsecureReleaseDispatcher extends QueueTaskDispatcher {
    static final String POLICY_VERSION = '2'
    static final String RELEASE_NODE = 'finsecure-release'
    static final Set<String> TRUSTED_JOBS = Collections.unmodifiableSet([
        'finsecure-release/verify-boundaries',
        'finsecure-release/verify-scheduling',
        'finsecure-release/delivery',
    ] as Set)

    static String rejection(String nodeName, String ownerName, boolean flyweight) {
        // Pipeline orchestration can start on the controller without acquiring a workspace.
        if (flyweight) {
            return nodeName == RELEASE_NODE ? 'FINSECURE_RELEASE_FLYWEIGHT_DENIED' : null
        }
        if (nodeName == RELEASE_NODE && !TRUSTED_JOBS.contains(ownerName)) {
            return 'FINSECURE_RELEASE_JOB_DENIED'
        }
        if (ownerName?.startsWith('finsecure-release/') && nodeName != RELEASE_NODE) {
            return 'FINSECURE_RELEASE_WRONG_NODE'
        }
        return null
    }

    @Override CauseOfBlockage canTake(Node node, Queue.BuildableItem item) {
        def owner
        try {
            owner = item.task.getOwnerTask()
        } catch (RuntimeException ignored) {
            return new FinsecureReleaseBlockage('FINSECURE_RELEASE_OWNER_UNAVAILABLE')
        }
        String ownerName = owner instanceof Job ? owner.fullName : null
        String reason = rejection(node.nodeName, ownerName, item.task instanceof Queue.FlyweightTask)
        return reason == null ? null : new FinsecureReleaseBlockage(reason)
    }
}

// Refuse an ambiguous duplicate instead of silently replacing an active policy.
def dispatchers = ExtensionList.lookup(QueueTaskDispatcher.class)
assert !dispatchers.any { it.class.name == 'FinsecureReleaseDispatcher' }
dispatchers.add(new FinsecureReleaseDispatcher())
println('FinSecure release scheduling policy v2 installed')
