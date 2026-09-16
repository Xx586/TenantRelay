import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiMeta, createInitialSettings, requestChat, saveSettings } from './api'

function memoryStorage() {
  const values = new Map()
  return {
    clear: () => values.clear(),
    getItem: (key) => values.has(key) ? values.get(key) : null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, String(value))
  }
}

Object.defineProperty(globalThis, 'localStorage', { value: memoryStorage(), configurable: true })
Object.defineProperty(globalThis, 'sessionStorage', { value: memoryStorage(), configurable: true })

describe('TenantRelay API client', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it('does not persist the API key in localStorage', () => {
    saveSettings({
      baseUrl: '/api', userId: 'u1', conversationId: 'c1', tenantId: 'tenant-a',
      apiKey: 'top-secret', product: 'AcmeCloud', environment: 'production'
    })

    expect(localStorage.getItem('tenantrelay.frontend.settings')).not.toContain('top-secret')
    expect(sessionStorage.getItem('tenantrelay.apiKey')).toBe('top-secret')
    expect(createInitialSettings().apiKey).toBe('top-secret')
  })

  it('normalizes the configured API URL', () => {
    expect(apiMeta({ baseUrl: 'http://localhost:8000///' }).baseUrl).toBe('http://localhost:8000')
  })

  it('sends tenant authentication and normalizes SaaS response fields', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({
      conv_id: 'conv-1', request_id: 'req-1', response: 'ok', intent: 'sdk_error',
      secondary_intents: ['permission_request'], supporting_agents: ['subscription'],
      tools_used: ['lookup_api_error'], knowledge_sources: [{ title: 'SDK guide' }]
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    const settings = {
      baseUrl: '/api', userId: 'u1', conversationId: '', tenantId: 'tenant-a',
      apiKey: 'secret', product: 'AcmeCloud', environment: 'production'
    }
    const result = await requestChat(settings, 'SDK 返回 403')
    const [, options] = fetchMock.mock.calls[0]

    expect(options.headers['X-Tenant-ID']).toBe('tenant-a')
    expect(options.headers['X-API-Key']).toBe('secret')
    expect(result.secondaryIntents).toEqual(['permission_request'])
    expect(result.toolsUsed).toEqual(['lookup_api_error'])
    expect(result.knowledgeSources[0].title).toBe('SDK guide')
  })
})
