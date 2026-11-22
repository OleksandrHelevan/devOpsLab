{{/*
Коротке ім'я чарта (можна перевизначити через nameOverride).
*/}}
{{- define "orders.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Повне ім'я об'єктів, побудоване з імені релізу.
Якщо ім'я релізу вже містить ім'я чарта, воно не дублюється (реліз "<x>-orders" -> "<x>-orders", а не "<x>-orders-orders").
*/}}
{{- define "orders.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Мітка helm.sh/chart: ім'я та версія чарта.
*/}}
{{- define "orders.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Мітки селектора (незмінні між оновленнями).
*/}}
{{- define "orders.selectorLabels" -}}
app.kubernetes.io/name: {{ include "orders.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Повний набір міток для всіх об'єктів.
*/}}
{{- define "orders.labels" -}}
helm.sh/chart: {{ include "orders.chart" . }}
{{ include "orders.selectorLabels" . }}
app.kubernetes.io/version: {{ include "orders.imageTag" . | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: devopslab
{{- end }}

{{/*
Тег образу: .Values.image.tag або appVersion чарта.
*/}}
{{- define "orders.imageTag" -}}
{{- default .Chart.AppVersion .Values.image.tag }}
{{- end }}

{{/*
Повне ім'я образу repository:tag.
*/}}
{{- define "orders.image" -}}
{{- printf "%s:%s" .Values.image.repository (include "orders.imageTag" .) }}
{{- end }}

{{/*
Імена ConfigMap / Secret / PVC.
*/}}
{{- define "orders.configMapName" -}}
{{- printf "%s-config" (include "orders.fullname" .) }}
{{- end }}

{{- define "orders.secretName" -}}
{{- default (printf "%s-secret" (include "orders.fullname" .)) .Values.secret.existingSecret }}
{{- end }}

{{- define "orders.pvcName" -}}
{{- printf "%s-data" (include "orders.fullname" .) }}
{{- end }}

{{/* Шаблон пода: спільний для Deployment і Rollout */}}
{{- define "orders.podTemplate" -}}
metadata:
  labels:
    {{- include "orders.labels" . | nindent 4 }}
  annotations:
    # Перезапуск подів при зміні конфігурації
    checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
spec:
  terminationGracePeriodSeconds: {{ .Values.terminationGracePeriodSeconds }}
  containers:
    - name: {{ .Chart.Name }}
      image: {{ include "orders.image" . | quote }}
      imagePullPolicy: {{ .Values.image.pullPolicy }}
      ports:
        - name: http
          containerPort: {{ .Values.containerPort }}
          protocol: TCP
      envFrom:
        - configMapRef:
            name: {{ include "orders.configMapName" . }}
      env:
        - name: ORDERS_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: {{ include "orders.secretName" . }}
              key: ORDERS_API_TOKEN
        {{- with .Values.env }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      resources:
        {{- toYaml .Values.resources | nindent 8 }}
      livenessProbe:
        httpGet:
          path: {{ .Values.probes.path }}
          port: http
        initialDelaySeconds: {{ .Values.probes.liveness.initialDelaySeconds }}
        periodSeconds: {{ .Values.probes.liveness.periodSeconds }}
        timeoutSeconds: 2
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: {{ .Values.probes.path }}
          port: http
        initialDelaySeconds: {{ .Values.probes.readiness.initialDelaySeconds }}
        periodSeconds: {{ .Values.probes.readiness.periodSeconds }}
        timeoutSeconds: 2
        failureThreshold: 3
      lifecycle:
        preStop:
          exec:
            command:
              - /bin/sh
              - -c
              - sleep 5
      securityContext:
        {{- toYaml .Values.securityContext | nindent 8 }}
      {{- if .Values.persistence.enabled }}
      volumeMounts:
        - name: data
          mountPath: {{ .Values.persistence.mountPath }}
      {{- end }}
  {{- if .Values.persistence.enabled }}
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: {{ include "orders.pvcName" . }}
  {{- end }}
{{- end }}
