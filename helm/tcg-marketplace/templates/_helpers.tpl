{{- define "tcg.fullname" -}}
{{ .Release.Name }}-tcg-marketplace
{{- end }}

{{- define "tcg.labels" -}}
app.kubernetes.io/name: tcg-marketplace
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "tcg.selectorLabels" -}}
app.kubernetes.io/name: tcg-marketplace
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
