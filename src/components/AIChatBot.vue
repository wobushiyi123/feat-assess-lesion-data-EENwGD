<template>
  <div class="ai-bot-root" :style="rootStyle">
    <!-- 折叠态：悬浮按钮（可拖动） -->
    <button
      v-if="!open"
      class="ai-fab"
      :title="'RECIST 评估助手（可拖动）'"
      @pointerdown="startDrag"
      @click="onFabClick"
    >
      <svg viewBox="0 0 24 24" width="26" height="26" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="8" width="16" height="11" rx="3" fill="white"/>
        <circle cx="9" cy="13.5" r="1.6" fill="#185FA5"/>
        <circle cx="15" cy="13.5" r="1.6" fill="#185FA5"/>
        <rect x="10.5" y="16.5" width="3" height="1.6" rx="0.8" fill="#185FA5"/>
        <path d="M12 8V5M9 5.5h6" stroke="white" stroke-width="1.6" stroke-linecap="round"/>
        <circle cx="19" cy="5" r="1.3" fill="white"/>
      </svg>
      <span v-if="unread" class="ai-badge">{{ unread }}</span>
    </button>

    <!-- 展开态：聊天面板（标题栏可拖动） -->
    <div v-else class="ai-panel">
      <div class="ai-header">
        <div class="ai-header-title" @pointerdown="startDrag" title="按住拖动">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="8" width="16" height="11" rx="3" fill="white"/>
            <circle cx="9" cy="13.5" r="1.6" fill="#185FA5"/>
            <circle cx="15" cy="13.5" r="1.6" fill="#185FA5"/>
            <rect x="10.5" y="16.5" width="3" height="1.6" rx="0.8" fill="#185FA5"/>
            <path d="M12 8V5M9 5.5h6" stroke="white" stroke-width="1.6" stroke-linecap="round"/>
            <circle cx="19" cy="5" r="1.3" fill="white"/>
          </svg>
          <span>RECIST 评估助手</span>
        </div>
        <button class="ai-close" @click="open = false" title="收起">✕</button>
      </div>

      <div ref="msgBox" class="ai-messages">
        <div
          v-for="(m, i) in messages"
          :key="i"
          class="ai-msg"
          :class="m.role"
        >
          <div class="ai-bubble">
            <div class="ai-text">{{ m.text }}</div>
            <div v-if="m.links && m.links.length" class="ai-links">
              <router-link
                v-for="(lk, j) in m.links"
                :key="j"
                :to="lk.url"
                class="ai-link"
                @click="open = false"
              >🔗 {{ lk.label }}</router-link>
            </div>
          </div>
          <div v-if="m.role === 'bot' && m.suggestions && m.suggestions.length" class="ai-suggest">
            <button
              v-for="(s, k) in m.suggestions"
              :key="k"
              class="ai-chip"
              @click="send(s)"
            >{{ s }}</button>
          </div>
        </div>
        <div v-if="loading" class="ai-msg bot">
          <div class="ai-bubble"><span class="ai-typing">正在思考…</span></div>
        </div>
      </div>

      <div class="ai-input-bar">
        <input
          v-model="input"
          class="ai-input"
          type="text"
          placeholder="问标准 / 受试者 / 评估结果…"
          @keyup.enter="send()"
        />
        <button class="ai-send" :disabled="loading || !input.trim()" @click="send()">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import api from '../api'
import { useBatchStore } from '../store/batch'

const open = ref(false)
const unread = ref(0)
const input = ref('')
const loading = ref(false)
const messages = ref([])
const msgBox = ref(null)
const batchStore = useBatchStore()

// ───────────── 可拖动逻辑 ─────────────
const POS_KEY = 'ai_bot_pos'
const FAB = { w: 56, h: 56 }
const PANEL = { w: 372, h: 540 }
const pos = ref({ x: 0, y: 0 })
const dragged = ref(false)        // 用户是否手动拖动过（用于决定默认位置）
const justDragged = ref(false)    // 刚完成一次拖拽，用于抑制 FAB 的 click 误触发

const rootStyle = computed(() => ({
  left: pos.value.x + 'px',
  top: pos.value.y + 'px',
  right: 'auto',
  bottom: 'auto'
}))

const clamp = (x, y, box) => {
  const cx = Math.min(Math.max(8, x), window.innerWidth - box.w - 8)
  const cy = Math.min(Math.max(8, y), window.innerHeight - box.h - 8)
  return { x: cx, y: cy }
}

const setDefaultPos = (forOpen) => {
  const box = forOpen ? PANEL : FAB
  pos.value = clamp(window.innerWidth - 22 - box.w, window.innerHeight - 22 - box.h, box)
}

const loadPos = () => {
  try {
    const raw = localStorage.getItem(POS_KEY)
    if (raw) {
      pos.value = JSON.parse(raw)
      dragged.value = true
      return
    }
  } catch (e) { /* ignore */ }
  dragged.value = false
  setDefaultPos(false)
}

let dragState = null
const startDrag = (e) => {
  justDragged.value = false
  const rect = e.currentTarget.getBoundingClientRect()
  dragState = { dx: e.clientX - rect.left, dy: e.clientY - rect.top, moved: false }
  window.addEventListener('pointermove', onDrag)
  window.addEventListener('pointerup', stopDrag)
  e.preventDefault()
}
const onDrag = (e) => {
  if (!dragState) return
  const box = open.value ? PANEL : FAB
  let nx = e.clientX - dragState.dx
  let ny = e.clientY - dragState.dy
  const c = clamp(nx, ny, box)
  pos.value = c
  if (Math.abs(nx - c.x) > 2 || Math.abs(ny - c.y) > 2) {
    // 处于边界夹紧状态，仍视为拖动
  }
  if (Math.abs(e.clientX - (c.x + dragState.dx)) > 3 || Math.abs(e.clientY - (c.y + dragState.dy)) > 3) {
    dragState.moved = true
    justDragged.value = true
  }
}
const stopDrag = () => {
  if (dragState && dragState.moved) {
    dragged.value = true
    try { localStorage.setItem(POS_KEY, JSON.stringify(pos.value)) } catch (e) { /* ignore */ }
  }
  dragState = null
  window.removeEventListener('pointermove', onDrag)
  window.removeEventListener('pointerup', stopDrag)
}
const onFabClick = () => {
  if (justDragged.value) { justDragged.value = false; return }
  open.value = true
}

onMounted(() => { loadPos() })

watch(open, (v) => {
  if (v) {
    unread.value = 0
    if (!dragged.value) setDefaultPos(true)
    else pos.value = clamp(pos.value.x, pos.value.y, PANEL)
    scrollToBottom()
  }
})

// ───────────── 消息逻辑 ─────────────
const scrollToBottom = async () => {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

const pushBot = (data) => {
  messages.value.push({
    role: 'bot',
    text: data.reply || '（无回复）',
    links: data.links || [],
    suggestions: data.suggestions || []
  })
  scrollToBottom()
}

const send = async (text) => {
  const content = (text ?? input.value).trim()
  if (!content || loading.value) return
  messages.value.push({ role: 'user', text: content })
  input.value = ''
  loading.value = true
  scrollToBottom()
  try {
    const data = await api.post('/api/chat', {
      message: content,
      batch_id: batchStore.currentBatchId ?? undefined
    })
    pushBot(data)
  } catch (e) {
    pushBot({
      reply: '抱歉，助手服务暂时不可用，请稍后重试或确认已登录。',
      suggestions: []
    })
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  // 拉取欢迎语 + 快捷提问（空消息触发兜底帮助）
  try {
    const data = await api.post('/api/chat', {
      message: '',
      batch_id: batchStore.currentBatchId ?? undefined
    })
    pushBot(data)
  } catch (e) {
    // 静默：用户展开后再试
  }
})
</script>

<style scoped>
.ai-bot-root {
  position: fixed;
  z-index: 2000;
  font-family: var(--font-family, -apple-system, "Microsoft YaHei", sans-serif);
}

/* 悬浮按钮 */
.ai-fab {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #185FA5, #2f7fd6);
  box-shadow: 0 6px 18px rgba(24, 95, 165, 0.4);
  cursor: grab;
  touch-action: none;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}
.ai-fab:active { cursor: grabbing; }
.ai-fab:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 10px 24px rgba(24, 95, 165, 0.5);
}
.ai-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 9px;
  background: #e64545;
  color: #fff;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  border: 2px solid #fff;
}

/* 面板 */
.ai-panel {
  width: 372px;
  height: 540px;
  max-height: calc(100vh - 48px);
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e3e8f0;
}
.ai-header {
  background: linear-gradient(135deg, #185FA5, #2f7fd6);
  color: #fff;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ai-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: grab;
  touch-action: none;
  user-select: none;
  flex: 1;
}
.ai-header-title:active { cursor: grabbing; }
.ai-close {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  opacity: 0.85;
}
.ai-close:hover { opacity: 1; }

.ai-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  background: #f5f7fb;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ai-msg {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-msg.user {
  align-items: flex-end;
}
.ai-msg.bot {
  align-items: flex-start;
}
.ai-bubble {
  max-width: 86%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.ai-msg.user .ai-bubble {
  background: #185FA5;
  color: #fff;
  border-bottom-right-radius: 3px;
}
.ai-msg.bot .ai-bubble {
  background: #fff;
  color: #2c3e50;
  border: 1px solid #e3e8f0;
  border-bottom-left-radius: 3px;
}
.ai-links {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ai-link {
  display: block;
  background: #eaf2fc;
  color: #185FA5;
  border: 1px solid #cfe0f5;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 12.5px;
  text-decoration: none;
  transition: background 0.15s;
}
.ai-link:hover { background: #dbe9fb; }
.ai-suggest {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-width: 86%;
}
.ai-chip {
  background: #fff;
  border: 1px solid #c9d6e8;
  color: #185FA5;
  border-radius: 14px;
  padding: 5px 11px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s;
}
.ai-chip:hover { background: #eaf2fc; }
.ai-typing {
  color: #8a96a8;
  font-style: italic;
}

.ai-input-bar {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #e3e8f0;
  background: #fff;
}
.ai-input {
  flex: 1;
  border: 1px solid #d4dce8;
  border-radius: 8px;
  padding: 9px 11px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.ai-input:focus { border-color: #185FA5; }
.ai-send {
  background: #185FA5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.ai-send:hover:not(:disabled) { background: #14507f; }
.ai-send:disabled { background: #a9c2dd; cursor: not-allowed; }
</style>
