pipelineJob('finsecure-ci') {
    description('Trusted main CI: five-minute SCM polling, tests/reports, packages, and local image export. No registry publishing or cloud deployment.')
    // Keep scheduling outside Jenkinsfile so inline review jobs remain manual.
    // Seeding restores polling on restart, without needing another manual build.
    configure { job ->
        job / 'properties' / 'org.jenkinsci.plugins.workflow.job.properties.DisableConcurrentBuildsJobProperty'
        job / 'properties' / 'org.jenkinsci.plugins.workflow.job.properties.PipelineTriggersJobProperty' / 'triggers' / 'hudson.triggers.SCMTrigger' {
            spec('H/5 * * * *')
            ignorePostCommitHooks(false)
        }
    }
    definition {
        cpsScm {
            scm {
                git {
                    remote {
                        url('https://github.com/yuenshingyan/nussoc-devops-and-cloud-with-ai-capstone.git')
                    }
                    branch('*/main')
                    extensions {
                        cloneOptions {
                            timeout(2)
                        }
                    }
                }
            }
            scriptPath('Jenkinsfile')
            lightweight(true)
        }
    }
}
