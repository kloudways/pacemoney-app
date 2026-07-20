pipeline {
    agent any

    options {
        ansiColor('xterm')
    }

    environment {
        ECR_REGISTRY     = '684779207098.dkr.ecr.eu-west-2.amazonaws.com'
        ECR_REPO         = 'pacemoney'
        AWS_REGION       = 'eu-west-2'
        KOPS_STATE_STORE = 's3://pacemoney-kops-state'
        CLUSTER_NAME     = 'pacemoney.k8s.local'
        APP_URL          = 'http://pacemoney.kloudways.com'
    }

    stages {
        stage('Guard') {
            steps {
                script {
                    def author = sh(script: 'git log -1 --pretty=format:"%ae"', returnStdout: true).trim()
                    if (author == 'jenkins@kloudways.com') {
                        currentBuild.displayName = "#${currentBuild.number} [gitops]"
                        catchError(buildResult: 'SUCCESS', stageResult: 'ABORTED') {
                            error('GitOps image-tag commit — skipping pipeline.')
                        }
                    }
                }
            }
        }

        stage('CI/CD') {
            when {
                not {
                    expression { return currentBuild.displayName.contains('[gitops]') }
                }
            }
            stages {
                stage('Gitleaks') {
                    steps {
                        sh '''
                            docker run --rm \
                              -v ${WORKSPACE}:/repo \
                              ghcr.io/gitleaks/gitleaks:latest \
                              detect --source /repo --redact --verbose
                        '''
                    }
                }

                stage('Unit Tests') {
                    steps {
                        sh '''
                            python3 -m venv .venv
                            .venv/bin/pip install --quiet -r requirements.txt
                            .venv/bin/pytest tests/ -v --tb=short --cov=app --cov-report=xml:coverage.xml
                        '''
                    }
                }

                stage('SonarQube') {
                    steps {
                        withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                            sh '''
                                sonar-scanner \
                                  -Dsonar.host.url=https://sonarcloud.io \
                                  -Dsonar.login=${SONAR_TOKEN}
                            '''
                        }
                    }
                }

                stage('Checkov') {
                    steps {
                        sh '''
                            pip3 install --quiet --user checkov
                            ~/.local/bin/checkov -d . --quiet --framework dockerfile
                        '''
                    }
                }

                stage('Docker Build') {
                    steps {
                        script {
                            env.IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                        }
                        sh """
                            docker build \
                              -t ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG} \
                              .
                        """
                    }
                }

                stage('Trivy Scan') {
                    steps {
                        sh """
                            trivy image \
                              --exit-code 1 \
                              --severity HIGH,CRITICAL \
                              --ignore-unfixed \
                              --no-progress \
                              ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG}
                        """
                    }
                }

                stage('Push to ECR') {
                    steps {
                        sh """
                            aws ecr get-login-password --region ${AWS_REGION} | \
                              docker login --username AWS --password-stdin ${ECR_REGISTRY}
                            docker push ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG}
                        """
                    }
                }

                stage('Update Image Tag') {
                    steps {
                        withCredentials([usernamePassword(credentialsId: 'github-token', usernameVariable: 'GH_USER', passwordVariable: 'GH_TOKEN')]) {
                            sh """
                                git config --local user.email "jenkins@kloudways.com"
                                git config --local user.name "Jenkins"
                                sed -i "s|^  tag:.*|  tag: \"${env.IMAGE_TAG}\"|" deploy/helm/pacemoney/values.yaml
                                git add deploy/helm/pacemoney/values.yaml
                                git commit -m "chore: update image tag to ${env.IMAGE_TAG}"
                                git remote set-url origin https://\${GH_USER}:\${GH_TOKEN}@github.com/kloudways/pacemoney-app.git
                                git push origin HEAD:main
                            """
                        }
                    }
                }

                stage('OWASP ZAP') {
                    steps {
                        sh """
                            docker run --rm \
                              -v ${WORKSPACE}:/zap/wrk:rw \
                              ghcr.io/zaproxy/zaproxy:stable \
                              zap-baseline.py -t ${APP_URL} -r zap-report.html || true
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            sh "docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG} || true"
            archiveArtifacts artifacts: 'zap-report.html', allowEmptyArchive: true
            cleanWs()
        }
        success {
            echo "Image ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG} pushed — ArgoCD will sync to ${CLUSTER_NAME}."
        }
        failure {
            echo 'Pipeline failed — check stage logs above.'
        }
    }
}
