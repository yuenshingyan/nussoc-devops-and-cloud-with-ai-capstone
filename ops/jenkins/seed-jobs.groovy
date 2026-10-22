import javaposse.jobdsl.dsl.DslScriptLoader
import javaposse.jobdsl.plugin.JenkinsJobManagement

// Seed after Jenkins has loaded its job registry, not during early JCasC adaptation.
// This is trusted administrator-owned image configuration, never repository build input.
def management = new JenkinsJobManagement(System.out, [:], new File('/var/jenkins_home'))
for (name in ['checkout-job', 'ci-job']) {
    def source = new File('/usr/share/jenkins/' + name + '.groovy').getText('UTF-8')
    new DslScriptLoader(management).runScript(source)
}
