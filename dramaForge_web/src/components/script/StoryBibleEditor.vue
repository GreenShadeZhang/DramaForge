<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { ScriptDetail, StoryBibleUpdate } from '@/types/script'

const props = defineProps<{
  script: ScriptDetail
}>()

const emit = defineEmits<{
  update: [field: string, value: string]
}>()

// ── Field definitions ──
interface BibleField {
  key: keyof StoryBibleUpdate
  label: string
  placeholder: string
  icon: string
  wide: boolean  // full-width for narrative fields
  rows: number
}

const fields: BibleField[] = [
  {
    key: 'premise', label: '核心故事命题', icon: '📖', wide: true, rows: 4,
    placeholder: '这部剧在讲一个什么样的故事？核心矛盾和主题是什么？\n\n例如：这是一部都市复仇题材的短剧，讲述豪门养女在订婚宴上遭养妹和未婚夫联手背叛后...',
  },
  {
    key: 'world_rules', label: '世界观和规则', icon: '🌍', wide: true, rows: 4,
    placeholder: '这个世界的运行法则、力量体系、社会结构或独特设定...\n\n例如：故事发生在当代都市A市，以上流社会商圈为核心舞台。世界的运行规则是"利益为王"...',
  },
  {
    key: 'character_relationships', label: '人物关系', icon: '👥', wide: true, rows: 4,
    placeholder: '主要角色之间的情感纽带、冲突关系、联盟与背叛...\n\n例如：沈念安↔沈薇薇：养姐妹→仇敌。沈薇薇嫉妒沈念安的才华...\n沈念安↔顾承泽：未婚夫妻→仇敌→复杂...',
  },
  {
    key: 'episode_arc', label: '分集节奏与阶段目标', icon: '📊', wide: true, rows: 4,
    placeholder: '每集的核心冲突、爽点和钩子如何递进，三幕结构如何分布...\n\n例如：第1集（开篇钩子）：订婚宴惊变→身份被揭穿→被赶出家门...\n第2集（三年后）：沈念安以全新身份登场...',
  },
  {
    key: 'timeline', label: '关键时间线', icon: '📅', wide: false, rows: 3,
    placeholder: '故事起止时间、关键时间节点、倒叙/闪回标记...\n\n例如：第0年（开篇）：订婚宴阴谋\n第3年（现在）：三年后归来',
  },
  {
    key: 'visual_style_rules', label: '视觉风格规则', icon: '🎨', wide: false, rows: 3,
    placeholder: '色调、光影、镜头语言偏好、转场风格...\n\n例如：色调以冷色调为主（蓝灰、深蓝），穿插暖色对比...',
  },
  {
    key: 'continuity_notes', label: '连续性注意事项', icon: '🔗', wide: false, rows: 3,
    placeholder: '需要跨集保持一致的人物外貌、道具、场景细节...\n\n例如：沈念安的标志性配饰——一条银色细链项链，必须在所有重要场景中佩戴...',
  },
]

// ── Local state ──
const localValues = ref<Record<string, string>>({})
const saveStatus = ref<Record<string, 'idle' | 'saving' | 'saved'>>({})
const textareaRefs = ref<Record<string, HTMLTextAreaElement>>({})

// Init from script prop
watch(() => props.script, (s) => {
  if (!s) return
  for (const f of fields) {
    if (!(f.key in localValues.value)) {
      localValues.value[f.key] = (s as any)[f.key] || ''
      saveStatus.value[f.key] = 'idle'
    }
  }
}, { immediate: true })

// ── Debounced save ──
const saveTimers: Record<string, ReturnType<typeof setTimeout>> = {}

function onInput(field: string, value: string) {
  localValues.value[field] = value
  autoResize(field)

  // Clear existing timer
  if (saveTimers[field]) clearTimeout(saveTimers[field])

  // Show saving state after brief delay
  saveStatus.value[field] = 'saving'

  saveTimers[field] = setTimeout(async () => {
    try {
      await emit('update', field, value)
      saveStatus.value[field] = 'saved'
      setTimeout(() => {
        if (saveStatus.value[field] === 'saved') saveStatus.value[field] = 'idle'
      }, 2000)
    } catch {
      saveStatus.value[field] = 'idle'
    }
  }, 1500)
}

// ── Auto-resize textarea ──
function autoResize(field: string) {
  nextTick(() => {
    const el = textareaRefs.value[field]
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.max(el.scrollHeight, 72) + 'px'
  })
}

// ── Character count ──
function charCount(field: string): number {
  return (localValues.value[field] || '').length
}

// ── Save status indicator ──
function statusIcon(status: string): string {
  if (status === 'saving') return '⏳'
  if (status === 'saved') return '✅'
  return ''
}

function statusText(status: string): string {
  if (status === 'saving') return '保存中...'
  if (status === 'saved') return '已保存'
  return ''
}

// ── Set textarea ref ──
function setRef(field: string, el: any) {
  if (el) textareaRefs.value[field] = el
}

// Compute grid fields (non-wide)
const wideFields = computed(() => fields.filter(f => f.wide))
const gridFields = computed(() => fields.filter(f => !f.wide))
</script>

<template>
  <div class="story-bible">
    <div class="story-bible-header">
      <span class="story-bible-icon">📜</span>
      <span class="story-bible-title">Story Bible</span>
      <span class="story-bible-badge">叙事基准</span>
    </div>
    <p class="story-bible-desc">
      约束后续角色、场景、分镜和成片生成的一致性基准。修改后自动保存。
    </p>

    <!-- Wide fields (full width, single column) -->
    <div class="bible-wide-section">
      <div v-for="field in wideFields" :key="field.key" class="bible-field bible-field-wide">
        <div class="field-header">
          <span class="field-icon">{{ field.icon }}</span>
          <label class="field-label">{{ field.label }}</label>
          <span class="field-count" :class="{ 'count-filled': charCount(field.key) > 50 }">
            {{ charCount(field.key) }} 字
          </span>
          <span
            v-if="statusIcon(saveStatus[field.key])"
            class="field-status"
            :class="{ 'status-saving': saveStatus[field.key] === 'saving', 'status-saved': saveStatus[field.key] === 'saved' }"
          >
            {{ statusIcon(saveStatus[field.key]) }} {{ statusText(saveStatus[field.key]) }}
          </span>
        </div>
        <textarea
          :ref="(el: any) => setRef(field.key, el)"
          class="field-textarea"
          :class="{ 'textarea-filled': charCount(field.key) > 0 }"
          :value="localValues[field.key] || ''"
          :placeholder="field.placeholder"
          :rows="field.rows"
          @input="onInput(field.key, ($event.target as HTMLTextAreaElement).value)"
        />
      </div>
    </div>

    <!-- Grid fields (2-column) -->
    <div class="bible-grid-section">
      <div v-for="field in gridFields" :key="field.key" class="bible-field bible-field-grid">
        <div class="field-header">
          <span class="field-icon">{{ field.icon }}</span>
          <label class="field-label">{{ field.label }}</label>
          <span class="field-count" :class="{ 'count-filled': charCount(field.key) > 30 }">
            {{ charCount(field.key) }} 字
          </span>
          <span
            v-if="statusIcon(saveStatus[field.key])"
            class="field-status"
            :class="{ 'status-saving': saveStatus[field.key] === 'saving', 'status-saved': saveStatus[field.key] === 'saved' }"
          >
            {{ statusIcon(saveStatus[field.key]) }} {{ statusText(saveStatus[field.key]) }}
          </span>
        </div>
        <textarea
          :ref="(el: any) => setRef(field.key, el)"
          class="field-textarea"
          :class="{ 'textarea-filled': charCount(field.key) > 0 }"
          :value="localValues[field.key] || ''"
          :placeholder="field.placeholder"
          :rows="field.rows"
          @input="onInput(field.key, ($event.target as HTMLTextAreaElement).value)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.story-bible {
  background: linear-gradient(135deg, #fefce8 0%, #fef9e7 100%);
  border: 1px solid #ead9a7;
  border-radius: 12px;
  padding: 24px 28px;
}

.story-bible-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.story-bible-icon { font-size: 20px; }

.story-bible-title {
  font-size: 17px;
  font-weight: 700;
  color: #2D2515;
}

.story-bible-badge {
  font-size: 11px;
  font-weight: 600;
  color: #92400E;
  background: rgba(245, 158, 11, 0.12);
  padding: 2px 8px;
  border-radius: 4px;
}

.story-bible-desc {
  font-size: 13px;
  color: #8B7A5A;
  margin: 0 0 24px;
  line-height: 1.6;
}

/* ── Sections ── */
.bible-wide-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 20px;
}

.bible-grid-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

@media (max-width: 640px) {
  .bible-grid-section {
    grid-template-columns: 1fr;
  }
}

/* ── Field ── */
.bible-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.field-icon { font-size: 14px; }

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #2D2515;
}

.field-count {
  margin-left: auto;
  font-size: 11px;
  color: #C0B090;
  transition: color 0.2s;
}
.field-count.count-filled {
  color: #8B7A5A;
}

/* ── Save status ── */
.field-status {
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  transition: opacity 0.2s;
}
.status-saving {
  color: #E8A317;
}
.status-saved {
  color: #059669;
}

/* ── Textarea ── */
.field-textarea {
  width: 100%;
  min-height: 72px;
  padding: 12px 14px;
  border: 1px solid #D4C898;
  border-radius: 8px;
  background: #FDF5D6;
  font-size: 13px;
  line-height: 1.8;
  color: #2D2515;
  resize: vertical;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
  overflow: hidden;
}

.field-textarea::placeholder {
  color: #C0B090;
  font-size: 12px;
  line-height: 1.6;
}

.field-textarea:focus {
  border-color: #E8A317;
  box-shadow: 0 0 0 3px rgba(232, 163, 23, 0.1);
  background: #FEF9E7;
}

.field-textarea.textarea-filled {
  border-left: 3px solid #059669;
  padding-left: 12px;
}
</style>
