<template>
  <main :class="['app-shell', `app-shell-${activeView}`]">
    <header class="topbar">
      <a class="brand" href="#" aria-label="TenantRelay 首页" @click.prevent="activeView = 'chat'">
        <span class="brand-mark">TR</span><span class="brand-name">TenantRelay</span>
      </a>
      <nav class="view-nav" aria-label="工作区">
        <button :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'">对话</button>
        <button :class="{ active: activeView === 'operations' }" @click="openOperations">SaaS 工作台</button>
        <button :class="{ active: activeView === 'knowledge' }" @click="activeView = 'knowledge'">知识库</button>
        <button :class="{ active: activeView === 'evaluation' }" @click="activeView = 'evaluation'">评测</button>
      </nav>
      <div class="topbar-tools">
        <span class="environment-pill"><i :class="healthOk ? 'online' : 'offline'"></i>{{ currentApi.label }}</span>
        <a class="docs-link" :href="docsUrl" target="_blank" rel="noreferrer">API 文档</a>
        <button class="avatar-button" title="当前用户">{{ userInitial }}</button>
      </div>
    </header>

    <div v-if="toast" class="toast" role="status">{{ toast }}</div>

    <section v-if="activeView === 'chat'" class="page page-chat">
      <div class="page-heading">
        <div class="heading-copy"><span class="kicker">Multi-agent support lab</span><h1>B2B SaaS 智能支持</h1><p>观察租户认证、意图识别、Agent 协作、RAG 检索和真实工具调用。</p></div>
        <div class="heading-actions"><span class="session-label">{{ settings.conversationId || '新会话' }}</span><button class="quiet-button" @click="clearConversation">清空</button></div>
      </div>

      <div class="chat-layout">
        <section class="chat-stage">
          <div class="stage-bar"><div class="stage-context"><span class="context-dot"></span><span>{{ currentApi.baseUrl }}</span></div><span>{{ settings.tenantId }} · {{ settings.environment }}</span></div>
          <div class="messages" ref="messageList">
            <article v-for="item in messages" :key="item.id" :class="['message', item.role]">
              <div class="message-meta"><span>{{ item.role === 'user' ? '你' : 'TenantRelay Agent' }}</span><small v-if="item.meta">{{ item.meta }}</small></div>
              <p>{{ item.content }}</p>
              <div v-if="item.sources?.length" class="source-list"><strong>知识来源</strong><span v-for="(source, index) in item.sources" :key="index">{{ source.title || source.source || `来源 ${index + 1}` }}</span></div>
              <div v-if="item.trace" class="message-trace">
                <div class="trace-head"><span>工具调用</span><small>#{{ item.trace.requestId || '-' }}</small></div>
                <div v-if="item.trace.toolCalls?.length" class="trace-calls">
                  <details v-for="(call, index) in item.trace.toolCalls" :key="index" open><summary><strong>{{ call.tool_name || 'unknown_tool' }}</strong><span>{{ call.success ? '成功' : '失败' }}</span></summary><pre>{{ formatJson(call.input || {}) }}</pre></details>
                </div>
                <p v-else class="trace-note">{{ item.trace.toolsUsed?.length ? `已调用：${item.trace.toolsUsed.join(' · ')}` : '本次没有工具调用。' }}</p>
              </div>
            </article>
            <div v-if="messages.length === 0" class="empty-state">
              <div class="empty-symbol">✦</div><h2>从一个真实 SaaS 支持问题开始</h2><p>请先在右侧填写演示租户认证信息。</p>
              <div class="starter-prompts"><button @click="usePrompt('Python SDK 调用上传接口返回 403，我们刚降级到 basic 套餐')">SDK 403 + 套餐</button><button @click="usePrompt('生产环境 webhook 连续失败，request_id 是 req_20260916')">Webhook 故障</button><button @click="usePrompt('企业版支持哪些功能？请给我一份接入步骤')">功能与接入</button></div>
            </div>
          </div>
          <form class="composer" @submit.prevent="sendMessage">
            <textarea v-model="draft" rows="3" placeholder="描述 API、SDK、Webhook、套餐或故障问题……" @keydown.meta.enter.prevent="sendMessage" @keydown.ctrl.enter.prevent="sendMessage"></textarea>
            <div class="composer-bottom"><span>⌘ / Ctrl + Enter 发送</span><button type="submit" :disabled="busy || !draft.trim()">{{ busy ? '处理中' : '发送' }}</button></div>
          </form>
        </section>

        <aside class="chat-sidebar" ref="sidebarRef"><div class="chat-sidebar-scroll">
          <section class="side-card session-card">
            <div class="card-heading"><div><span class="kicker">Tenant context</span><h2>当前上下文</h2></div><span class="status-copy muted">{{ settings.environment }}</span></div>
            <div class="session-grid"><div><span>租户</span><strong>{{ settings.tenantId || '-' }}</strong></div><div><span>产品</span><strong>{{ settings.product || '-' }}</strong></div><div><span>用户</span><strong>{{ settings.userId || '-' }}</strong></div><div><span>会话</span><strong>{{ settings.conversationId || '自动生成' }}</strong></div></div>
          </section>

          <section class="side-card connection-card">
            <div class="card-heading"><div><span class="kicker">Connection</span><h2>连接配置</h2></div><span class="status-copy" :class="healthOk ? 'success' : 'muted'">{{ healthLabel }}</span></div>
            <label><span>API 地址</span><input v-model="settings.baseUrl" @change="persist" placeholder="/api" /></label>
            <div class="field-grid"><label><span>租户 ID</span><input v-model="settings.tenantId" @change="persist" placeholder="demo-tenant" /></label><label><span>用户 ID</span><input v-model="settings.userId" @change="persist" placeholder="user_001" /></label></div>
            <label><span>API Key（只保存在当前浏览会话）</span><input v-model="settings.apiKey" type="password" @change="persist" placeholder="demo-key-change-me" autocomplete="off" /></label>
            <div class="field-grid"><label><span>产品</span><input v-model="settings.product" @change="persist" placeholder="AcmeCloud" /></label><label><span>环境</span><select v-model="settings.environment" @change="persist"><option>production</option><option>staging</option><option>development</option></select></label></div>
            <div class="side-actions"><button @click="checkHealth">检查连接</button><button class="quiet-button" @click="refreshConsole">刷新</button></div>
          </section>

          <section class="side-card trace-card">
            <div class="card-heading"><div><span class="kicker">Last trace</span><h2>最近一次请求</h2></div><span class="trace-status" :class="lastResponse ? 'has-data' : ''"></span></div>
            <div v-if="lastResponse" class="trace-body">
              <div class="latency"><span>响应耗时</span><strong>{{ lastResponse.latencyMs || '-' }}<small> ms</small></strong></div>
              <dl class="detail-list"><div><dt>主 Agent</dt><dd>{{ lastResponse.primaryAgent || lastResponse.agentType || '-' }}</dd></div><div><dt>协作 Agent</dt><dd>{{ lastResponse.supportingAgents.join(', ') || '-' }}</dd></div><div><dt>主意图</dt><dd>{{ lastResponse.intent || '-' }}</dd></div><div><dt>次级意图</dt><dd>{{ lastResponse.secondaryIntents.join(', ') || '-' }}</dd></div><div><dt>路由置信度</dt><dd>{{ formatPercent(lastResponse.routingConfidence) }}</dd></div><div><dt>工具</dt><dd>{{ lastResponse.toolsUsed.join(', ') || '-' }}</dd></div><div><dt>知识库</dt><dd :class="lastResponse.knowledgeUsed ? 'success' : 'muted'">{{ lastResponse.knowledgeUsed ? '已使用' : '未使用' }}</dd></div><div><dt>工单</dt><dd>{{ lastResponse.ticketId || '-' }}</dd></div></dl>
              <p v-if="lastResponse.routingReason" class="routing-reason">{{ lastResponse.routingReason }}</p>
            </div><p v-else class="side-empty">发送消息后显示意图、Agent 路由、工具和 RAG 来源。</p>
          </section>

          <section class="side-card monitor-card">
            <div class="card-heading"><div><span class="kicker">Runtime</span><h2>运行状态</h2></div><button class="link-button" @click="loadMonitor">刷新</button></div>
            <div class="mini-stats"><div><strong>{{ totalRequests }}</strong><span>请求</span></div><div><strong>{{ agentCount }}</strong><span>Agent</span></div><div><strong>{{ activeAlerts.length }}</strong><span>告警</span></div></div><p v-if="activeAlerts.length" class="alert-note">{{ activeAlerts[0].detail || activeAlerts[0].title }}</p><p v-else class="healthy-note">当前没有活跃告警。</p>
          </section>
        </div></aside>
      </div>
    </section>

    <section v-else-if="activeView === 'operations'" class="page page-operations">
      <div class="page-heading"><div class="heading-copy"><span class="kicker">Tenant operations</span><h1>SaaS 工作台</h1><p>读取租户、套餐、功能权限和白名单服务状态，创建或查询真实持久化工单。</p></div><button @click="loadSaasOverview" :disabled="busy">刷新租户数据</button></div>
      <div class="operation-grid">
        <section class="workspace-card"><div class="card-heading"><div><span class="kicker">Tenant</span><h2>租户配置</h2></div><code>GET /saas/tenants/current</code></div><pre v-if="tenantData" class="data-block">{{ formatJson(tenantData) }}</pre><div v-else class="workspace-empty">填写租户认证后刷新。</div></section>
        <section class="workspace-card"><div class="card-heading"><div><span class="kicker">Subscription</span><h2>套餐与权限</h2></div><code>GET /saas/subscription</code></div><pre v-if="subscriptionData" class="data-block">{{ formatJson(subscriptionData) }}</pre><div v-else class="workspace-empty">暂无订阅信息。</div></section>
        <section class="workspace-card"><div class="card-heading"><div><span class="kicker">Status</span><h2>服务状态</h2></div><button class="link-button" @click="loadServiceStatus">检查</button></div><pre v-if="serviceData" class="data-block">{{ formatJson(serviceData) }}</pre><div v-else class="workspace-empty">只访问数据库中配置的白名单地址。</div></section>
      </div>
      <div class="operation-grid ticket-grid">
        <section class="workspace-card">
          <div class="card-heading"><div><span class="kicker">Create ticket</span><h2>创建支持工单</h2></div><code>POST /saas/tickets</code></div>
          <label><span>标题</span><input v-model="ticketForm.title" placeholder="Python SDK 403 需要协助" /></label><label><span>问题描述</span><textarea v-model="ticketForm.description" rows="5" placeholder="描述影响范围、环境和 request_id；不要粘贴密钥。"></textarea></label><label><span>优先级</span><select v-model="ticketForm.priority"><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label><button @click="submitTicket" :disabled="busy || !ticketForm.title.trim() || !ticketForm.description.trim()">确认创建工单</button>
        </section>
        <section class="workspace-card"><div class="card-heading"><div><span class="kicker">Ticket status</span><h2>查询工单</h2></div><code>GET /saas/tickets/:id</code></div><div class="search-line"><input v-model="ticketQuery" placeholder="TR-XXXXXXXXXX" @keydown.enter="lookupTicket" /><button @click="lookupTicket" :disabled="busy || !ticketQuery.trim()">查询</button></div><pre v-if="ticketData" class="data-block">{{ formatJson(ticketData) }}</pre><div v-else class="workspace-empty">创建后可使用真实工单编号再次查询。</div></section>
      </div>
    </section>

    <section v-else-if="activeView === 'knowledge'" class="page page-knowledge">
      <div class="page-heading"><div class="heading-copy"><span class="kicker">Tenant-aware RAG</span><h1>知识库</h1><p>按租户、产品和版本检索或导入支持文档。</p></div><div class="count-display"><strong>{{ knowledgeCount }}</strong><span>chunks</span></div></div>
      <div class="knowledge-layout">
        <section class="workspace-card search-workspace"><div class="card-heading"><div><span class="kicker">Retrieval</span><h2>检索知识</h2></div><code>POST /search</code></div><div class="search-line"><input v-model="searchQuery" placeholder="例如：Python SDK 403" @keydown.enter="searchKnowledge" /><button @click="searchKnowledge" :disabled="busy || !searchQuery.trim()">搜索</button></div><div v-if="searchResults.length" class="result-list"><article v-for="(item, index) in searchResults" :key="item.id || index" class="result-item"><span class="result-number">{{ String(index + 1).padStart(2, '0') }}</span><div><div class="result-title"><strong>{{ item.title || '未命名文档' }}</strong><small>score {{ item.score ?? '-' }}</small></div><p>{{ item.content }}</p></div></article></div><div v-else class="workspace-empty">输入问题开始检索。</div></section>
        <section class="workspace-card import-workspace"><div class="card-heading"><div><span class="kicker">Ingestion</span><h2>添加租户知识</h2></div><code>ChromaDB</code></div><label><span>标题</span><input v-model="docTitle" placeholder="SDK 排障手册" /></label><label><span>内容</span><textarea v-model="docContent" rows="7" placeholder="输入产品说明或排障流程"></textarea></label><div class="side-actions"><button @click="submitKnowledge" :disabled="busy || !docTitle.trim() || !docContent.trim()">添加文档</button><label class="upload-button">上传文件<input type="file" accept=".txt,.md,.json" @change="handleUpload" /></label></div></section>
      </div>
      <section class="workspace-card skills-workspace"><div class="card-heading"><div><span class="kicker">Loaded skills</span><h2>已加载能力</h2></div><button class="link-button" @click="reloadSkillSet">重新加载</button></div><div class="skill-table"><div v-for="skill in skillsData.skills" :key="skill.name" class="skill-item"><span class="skill-dot"></span><strong>{{ skill.name }}</strong><span>{{ skill.description || '业务规则' }}</span><small>{{ skill.content_chars || 0 }} chars</small></div><div v-if="!skillsData.skills.length" class="workspace-empty">暂无已加载 Skill。</div></div></section>
    </section>

    <section v-else class="page page-evaluation">
      <div class="page-heading"><div class="heading-copy"><span class="kicker">Evaluation lab</span><h1>评测 Agent</h1><p>运行内置 SaaS 用例；简历指标只引用真实执行结果。</p></div><button @click="runEvaluation" :disabled="busy">{{ busy ? '运行中...' : '运行评测' }}</button></div>
      <div v-if="evalData" class="evaluation-content"><div class="evaluation-summary"><div class="score-hero"><span>Pass rate</span><strong>{{ formatPercent(evalData.pass_rate) }}</strong><small>{{ evalData.passed }} / {{ evalData.total }} cases passed</small></div><div><span>通过</span><strong>{{ evalData.passed }}</strong></div><div><span>总数</span><strong>{{ evalData.total }}</strong></div><div><span>回归</span><strong :class="evalData.regressions?.length ? 'danger' : 'success'">{{ evalData.regressions?.length || 0 }}</strong></div></div><div class="evaluation-layout"><section class="workspace-card"><div class="card-heading"><div><span class="kicker">Scores</span><h2>平均评分</h2></div></div><div class="score-list"><div v-for="(value, key) in evalData.avg_scores" :key="key"><span>{{ key }}</span><i><b :style="{ width: `${Math.min(Number(value) * 10, 100)}%` }"></b></i><strong>{{ Number(value).toFixed(2) }}</strong></div></div></section><section class="workspace-card"><div class="card-heading"><div><span class="kicker">Recommendations</span><h2>优化建议</h2></div></div><div v-if="evalData.recommendations?.length" class="recommendations"><p v-for="(item, index) in evalData.recommendations" :key="index">{{ item }}</p></div><div v-else class="workspace-empty">本次没有额外建议。</div></section></div></div><div v-else class="evaluation-empty"><div class="empty-symbol">◎</div><h2>还没有评测结果</h2><p>点击右上角运行一次评测。</p></div>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { addKnowledge, apiMeta, createInitialSettings, createSupportTicket, reloadSkills, requestChat, requestCurrentTenant, requestHealth, requestKnowledgeStats, requestMonitor, requestSearch, requestServiceStatus, requestSkills, requestSubscription, requestTicket, requestToolTrace, runEvaluation as requestEvaluation, saveSettings, uploadKnowledge } from './lib/api'

const settings = reactive(createInitialSettings())
const activeView = ref('chat')
const messages = ref([])
const draft = ref('')
const busy = ref(false)
const healthOk = ref(false)
const healthLabel = ref('未检查')
const knowledgeCount = ref('-')
const searchQuery = ref('Python SDK 403 套餐权限')
const searchResults = ref([])
const docTitle = ref('SDK 排障补充说明')
const docContent = ref('当 SDK 返回 403 时，请同时核对套餐权限、租户功能开关和 IP 白名单。')
const messageList = ref(null)
const sidebarRef = ref(null)
const monitorData = ref({ agent_stats: {}, tool_stats: {}, active_alerts: [], suggestions: [] })
const skillsData = ref({ count: 0, skills: [], errors: [] })
const lastResponse = ref(null)
const lastTrace = ref(null)
const evalData = ref(null)
const tenantData = ref(null)
const subscriptionData = ref(null)
const serviceData = ref(null)
const ticketData = ref(null)
const ticketQuery = ref('')
const ticketForm = reactive({ title: '', description: '', priority: 'medium' })
const toast = ref('')
let toastTimer
let messageSequence = 0
let sidebarObserver

const currentApi = computed(() => apiMeta(settings))
const docsUrl = computed(() => `${currentApi.value.baseUrl}/docs`)
const userInitial = computed(() => (settings.userId || 'U').slice(0, 1).toUpperCase())
const activeAlerts = computed(() => monitorData.value.active_alerts || [])
const agentCount = computed(() => Object.keys(monitorData.value.agent_stats || {}).length)
const totalRequests = computed(() => Object.values(monitorData.value.agent_stats || {}).reduce((sum, item) => sum + Number(item.total || 0), 0))

watch(() => settings.conversationId, persist)
onMounted(() => { refreshConsole(); updateSidebarHeight(); if (typeof ResizeObserver !== 'undefined') { sidebarObserver = new ResizeObserver(updateSidebarHeight); if (sidebarRef.value) sidebarObserver.observe(sidebarRef.value) } window.addEventListener('resize', updateSidebarHeight) })
onBeforeUnmount(() => { sidebarObserver?.disconnect?.(); window.removeEventListener('resize', updateSidebarHeight) })

function persist() { saveSettings(settings) }
function updateSidebarHeight() { if (sidebarRef.value) sidebarRef.value.style.setProperty('--sidebar-height', `${Math.max(320, Math.floor(sidebarRef.value.getBoundingClientRect().height))}px`) }
async function refreshConsole() { await Promise.allSettled([checkHealth(), loadStats(), loadMonitor(), loadSkills()]) }
async function checkHealth() { try { const data = await requestHealth(settings); healthOk.value = data.status === 'ok'; healthLabel.value = data.status || 'ok' } catch { healthOk.value = false; healthLabel.value = '不可用' } }
async function loadStats() { try { const data = await requestKnowledgeStats(settings); knowledgeCount.value = data.total_chunks ?? '-' } catch { knowledgeCount.value = '-' } }
async function loadMonitor() { try { monitorData.value = await requestMonitor(settings) } catch { monitorData.value = { agent_stats: {}, tool_stats: {}, active_alerts: [], suggestions: [] } } }
async function loadSkills() { try { skillsData.value = await requestSkills(settings) } catch { skillsData.value = { count: 0, skills: [], errors: [] } } }
async function reloadSkillSet() { busy.value = true; try { skillsData.value = await reloadSkills(settings); showToast('Skills 已重新加载') } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function sendMessage() {
  const content = draft.value.trim(); if (!content || busy.value) return
  persist(); messages.value.push({ id: createMessageId(), role: 'user', content }); draft.value = ''; busy.value = true
  try { const response = await requestChat(settings, content); if (response.conversationId && !settings.conversationId) settings.conversationId = response.conversationId; persist(); lastResponse.value = response; lastTrace.value = await loadToolTrace(response.requestId); const meta = [response.intent, response.primaryAgent || response.agentType, response.knowledgeUsed ? 'RAG' : '', response.ticketId || ''].filter(Boolean).join(' · '); messages.value.push({ id: createMessageId(), role: 'assistant', content: response.response, meta, sources: response.knowledgeSources, trace: lastTrace.value?.trace || null }); await loadMonitor() }
  catch (error) { messages.value.push({ id: createMessageId(), role: 'assistant', content: error.message, meta: '请求失败' }) }
  finally { busy.value = false; await nextTick(); messageList.value?.scrollTo({ top: messageList.value.scrollHeight, behavior: 'smooth' }) }
}
function usePrompt(prompt) { draft.value = prompt }
function clearConversation() { messages.value = []; lastResponse.value = null; lastTrace.value = null; settings.conversationId = ''; persist() }
async function loadToolTrace(requestId) { try { return await requestToolTrace(settings, requestId) } catch { return null } }
async function openOperations() { activeView.value = 'operations'; await loadSaasOverview() }
async function loadSaasOverview() { persist(); busy.value = true; const [tenant, subscription, services] = await Promise.allSettled([requestCurrentTenant(settings), requestSubscription(settings), requestServiceStatus(settings)]); tenantData.value = tenant.status === 'fulfilled' ? tenant.value : null; subscriptionData.value = subscription.status === 'fulfilled' ? subscription.value : null; serviceData.value = services.status === 'fulfilled' ? services.value : null; if ([tenant, subscription, services].some((item) => item.status === 'rejected')) showToast('部分数据读取失败，请检查租户认证'); busy.value = false }
async function loadServiceStatus() { busy.value = true; try { serviceData.value = await requestServiceStatus(settings); showToast('服务状态已更新') } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function submitTicket() { if (!window.confirm('确认要为当前租户创建真实持久化工单吗？')) return; busy.value = true; try { ticketData.value = await createSupportTicket(settings, { ...ticketForm, request_id: lastResponse.value?.requestId || crypto.randomUUID() }); ticketQuery.value = ticketData.value.ticket_id || ''; showToast(`工单 ${ticketQuery.value} 已创建`) } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function lookupTicket() { busy.value = true; try { ticketData.value = await requestTicket(settings, ticketQuery.value.trim()); showToast('工单状态已更新') } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function searchKnowledge() { busy.value = true; try { const data = await requestSearch(settings, searchQuery.value, 5); searchResults.value = data.results || []; showToast(`返回 ${searchResults.value.length} 条结果`) } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function submitKnowledge() { busy.value = true; try { await addKnowledge(settings, [{ title: docTitle.value.trim(), content: docContent.value.trim() }]); await loadStats(); showToast('文档已添加') } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function handleUpload(event) { const file = event.target.files?.[0]; event.target.value = ''; if (!file) return; busy.value = true; try { await uploadKnowledge(settings, file); await loadStats(); showToast(`${file.name} 导入成功`) } catch (error) { showToast(error.message) } finally { busy.value = false } }
async function runEvaluation() { busy.value = true; try { evalData.value = await requestEvaluation(settings); showToast('评测完成') } catch (error) { showToast(error.message) } finally { busy.value = false } }
function formatPercent(value) { const number = Number(value || 0); return `${(number <= 1 ? number * 100 : number).toFixed(1)}%` }
function formatJson(value) { try { return JSON.stringify(value ?? {}, null, 2) } catch { return String(value ?? '') } }
function createMessageId() { messageSequence += 1; return `message-${Date.now()}-${messageSequence}` }
function showToast(message) { toast.value = message; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.value = '' }, 3000) }
</script>
