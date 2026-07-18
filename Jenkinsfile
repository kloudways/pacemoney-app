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
                    .venv/bin/pytest tests/ -v --tb=short
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
                      -t ${ECR_REGISTRY}/${ECR_REPO}:latest \
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
                    docker push ${ECR_REGISTRY}/${ECR_REPO}:latest
                """
            }
        }

        stage('Helm Deploy') {
            steps {
                withCredentials([string(credentialsId: 'db-url', variable: 'DB_URL')]) {
                    sh """
                        kops export kubecfg ${CLUSTER_NAME} \
                          --state ${KOPS_STATE_STORE} --admin
                        helm upgrade --install pacemoney ./deploy/helm/pacemoney \
                          --namespace pacemoney --create-namespace \
                          --set image.repository=${ECR_REGISTRY}/${ECR_REPO} \
                          --set image.tag=${env.IMAGE_TAG} \
                          --set database.url=\${DB_URL} \
                          --wait --timeout 5m
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

    post {
        always {
            sh "docker rmi ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG} || true"
            sh "docker rmi ${ECR_REGISTRY}/${ECR_REPO}:latest || true"
            cleanWs()
        }
        success {
            echo "Deployed ${ECR_REGISTRY}/${ECR_REPO}:${env.IMAGE_TAG} to ${CLUSTER_NAME}."
        }
        failure {
            echo 'Pipeline failed — check stage logs above.'
        }
    }
}
