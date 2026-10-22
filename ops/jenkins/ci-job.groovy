pipelineJob('finsecure-ci') {
    description('Application CI: locked dependencies, Ruff, pytest reports, coverage, and packages. No image publishing or cloud deployment. First run requires Jenkinsfile on main; manual triggering in Step 4.2.')
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
