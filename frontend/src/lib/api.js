const DEFAULT_API_URL = '/api'

export function createInitialSettings() {
  const saved = readSettings()
  return {
    baseUrl: saved.baseUrl || runtimeConfig().apiUrl || import.meta.env.VITE_API_URL || DEFAULT_API_URL,
    userId: saved.userId || 'user_001',
    conversationId: saved.conversationId || '',
    tenantId: saved.tenantId || 'demo-tenant',
    apiKey: sessionStorage.getItem('tenantrelay.apiKey') || '',
    product: saved.product || 'AcmeCloud',
    environment: saved.environment || 'production'
  }
}

export function saveSettings(settings) {
  localStorage.setItem('tenantrelay.frontend.settings', JSON.stringify({
    baseUrl: settings.baseUrl,
    userId: settings.userId,
    conversationId: settings.conversationId,
    tenantId: settings.tenantId,
    product: settings.product,
    environment: settings.environment
  }))
  if (settings.apiKey) sessionStorage.setItem('tenantrelay.apiKey', settings.apiKey)
  else sessionStorage.removeItem('tenantrelay.apiKey')
}

export function apiMeta(settings) {
  return {
    label: 'TenantRelay API',
    baseUrl: normalizeBaseUrl(settings.baseUrl || DEFAULT_API_URL)
  }
}

export function requestHealth(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/health')
}

export function requestMonitor(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/monitor')
}

export function requestSkills(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/skills')
}

export function reloadSkills(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/skills/reload', { method: 'POST' })
}

export function requestKnowledgeStats(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/knowledge/stats')
}

export function runEvaluation(settings, body = null) {
  return requestJson(apiMeta(settings).baseUrl, '/eval/run', {
    method: 'POST',
    headers: jsonHeaders(settings, false),
    body: body ? JSON.stringify(body) : undefined
  })
}

export function requestSearch(settings, query, topK = 5) {
  const params = new URLSearchParams({
    query,
    top_k: String(topK),
    product: settings.product || 'AcmeCloud',
    version: 'latest'
  })
  return requestJson(apiMeta(settings).baseUrl, `/search?${params}`, {
    method: 'POST',
    headers: authHeaders(settings)
  })
}

export async function requestChat(settings, message) {
  const raw = await requestJson(apiMeta(settings).baseUrl, '/chat', {
    method: 'POST',
    headers: jsonHeaders(settings),
    body: JSON.stringify({
      message,
      user_id: settings.userId || 'anonymous',
      conv_id: settings.conversationId || undefined,
      product: settings.product || 'AcmeCloud',
      environment: settings.environment || 'production'
    })
  })
  return normalizeChatResponse(raw)
}

export async function requestToolTrace(settings, requestId) {
  if (!requestId) return null
  const raw = await requestJson(
    apiMeta(settings).baseUrl,
    `/trace/tool/${encodeURIComponent(requestId)}`
  )
  return normalizeToolTraceResponse(raw)
}

export function addKnowledge(settings, documents) {
  const normalized = documents.map((document) => ({
    ...document,
    product: document.product || settings.product || 'AcmeCloud',
    version: document.version || 'latest',
    visibility: document.visibility || 'tenant'
  }))
  return requestJson(apiMeta(settings).baseUrl, '/knowledge/add', {
    method: 'POST',
    headers: jsonHeaders(settings),
    body: JSON.stringify({ documents: normalized })
  })
}

export function uploadKnowledge(settings, file) {
  const form = new FormData()
  form.append('file', file)
  return requestJson(apiMeta(settings).baseUrl, '/knowledge/upload', {
    method: 'POST',
    headers: authHeaders(settings),
    body: form
  })
}

export function requestCurrentTenant(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/saas/tenants/current', {
    headers: authHeaders(settings)
  })
}

export function requestSubscription(settings) {
  return requestJson(apiMeta(settings).baseUrl, '/saas/subscription', {
    headers: authHeaders(settings)
  })
}

export function requestServiceStatus(settings, serviceName = '') {
  const suffix = serviceName ? `?service_name=${encodeURIComponent(serviceName)}` : ''
  return requestJson(apiMeta(settings).baseUrl, `/saas/services/status${suffix}`, {
    headers: authHeaders(settings)
  })
}

export function createSupportTicket(settings, ticket) {
  return requestJson(apiMeta(settings).baseUrl, '/saas/tickets', {
    method: 'POST',
    headers: jsonHeaders(settings),
    body: JSON.stringify(ticket)
  })
}

export function requestTicket(settings, ticketId) {
  return requestJson(
    apiMeta(settings).baseUrl,
    `/saas/tickets/${encodeURIComponent(ticketId)}`,
    { headers: authHeaders(settings) }
  )
}

function authHeaders(settings) {
  return {
    'X-Tenant-ID': String(settings.tenantId || ''),
    'X-API-Key': String(settings.apiKey || '')
  }
}

function jsonHeaders(settings, includeAuth = true) {
  return {
    'Content-Type': 'application/json',
    ...(includeAuth ? authHeaders(settings) : {})
  }
}

function normalizeChatResponse(raw) {
  return {
    conversationId: raw.conversation_id || raw.conversationId || raw.conv_id || '',
    requestId: raw.request_id || raw.requestId || '',
    response: raw.response || '',
    intent: raw.intent || 'other',
    secondaryIntents: raw.secondary_intents || raw.secondaryIntents || [],
    intentGroup: raw.intent_group || raw.intentGroup || 'other',
    agentType: raw.agent_type || raw.agentType || '',
    agentTypes: raw.agent_types || raw.agentTypes || [],
    primaryAgent: raw.primary_agent || raw.primaryAgent || '',
    supportingAgents: raw.supporting_agents || raw.supportingAgents || [],
    toolsUsed: raw.tools_used || raw.toolsUsed || [],
    routingReason: raw.routing_reason || raw.routingReason || '',
    routingConfidence: Number(raw.routing_confidence ?? raw.routingConfidence ?? 0),
    entities: raw.entities || {},
    intentConfidence: Number(raw.intent_confidence ?? raw.intentConfidence ?? 0),
    intentSourceScores: raw.intent_source_scores || raw.intentSourceScores || {},
    escalated: Boolean(raw.escalated),
    latencyMs: Number(raw.latency_ms ?? raw.latencyMs ?? 0),
    knowledgeUsed: Boolean(raw.knowledge_used ?? raw.knowledgeUsed),
    knowledgeSources: raw.knowledge_sources || raw.knowledgeSources || [],
    ticketId: raw.ticket_id || raw.ticketId || null,
    tenantId: raw.tenant_id || raw.tenantId || '',
    raw
  }
}

function normalizeToolTraceResponse(raw) {
  const trace = raw?.trace || {}
  return {
    requestId: raw?.request_id || raw?.requestId || '',
    found: Boolean(raw?.found),
    trace: {
      ...trace,
      toolsUsed: trace.tools_used || trace.toolsUsed || [],
      toolCalls: trace.tool_calls || trace.toolCalls || []
    },
    raw
  }
}

async function requestJson(baseUrl, path, options = {}) {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}${path}`, options)
  const text = await response.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!response.ok) {
    const detail = typeof data === 'string' ? data : data?.detail || JSON.stringify(data)
    throw new Error(`${response.status} ${response.statusText}: ${detail}`)
  }
  return data
}

function normalizeBaseUrl(value) {
  return String(value || '').replace(/\/+$/, '')
}

function readSettings() {
  try {
    return JSON.parse(localStorage.getItem('tenantrelay.frontend.settings') || '{}')
  } catch {
    return {}
  }
}

function runtimeConfig() {
  if (typeof window === 'undefined') return {}
  return window.__TENANTRELAY_CONFIG__ || {}
}
