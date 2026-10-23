{{- define "churn-api.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "churn-api.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "churn-api.labels" -}}
app.kubernetes.io/name: {{ include "churn-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "churn-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "churn-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
