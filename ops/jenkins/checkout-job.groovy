pipelineJob('finsecure-checkout') {
    description('Manual setup diagnostic: trusted main checkout/tool checks only. Automatic application CI now belongs to finsecure-ci.')
    parameters {
        stringParam('EXPECTED_REVISION', '', 'Optional exact Git SHA for a manually verified checkout.')
    }
    // Retain the diagnostic job without duplicating application CI polling.
    configure { job ->
        job / 'properties' / 'org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty'
    }
    definition {
        cps {
            sandbox()
            script('''
properties([
    parameters([string(name: 'EXPECTED_REVISION', defaultValue: '', description: 'Optional exact Git SHA')]),
    disableConcurrentBuilds()
])
timeout(time: 5, unit: 'MINUTES') {
    node('python') {
        stage('Checkout') {
            deleteDir()
            def source = checkout([
                $class: 'GitSCM',
                branches: [[name: '*/main']],
                userRemoteConfigs: [[url: 'https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git']],
                extensions: [[$class: 'CloneOption', timeout: 2]]
            ])
            if (params.EXPECTED_REVISION && source.GIT_COMMIT != params.EXPECTED_REVISION) {
                error('Checked-out revision does not match EXPECTED_REVISION')
            }
            echo('SOURCE_REVISION=' + source.GIT_COMMIT)
            sh('set -eu; git --version; uv --version; python --version; java -version')
            echo('CHECKOUT_ONLY: application tests, scans, image delivery, and deployment have NOT run.')
        }
    }
}
''')
        }
    }
}
