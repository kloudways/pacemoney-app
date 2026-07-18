{{- define "pacemoney.name" -}}
{{- .Chart.Name }}
{{- end }}

{{- define "pacemoney.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "pacemoney.labels" -}}
app.kubernetes.io/name: {{ include "pacemoney.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "pacemoney.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pacemoney.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
