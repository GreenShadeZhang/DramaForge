<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  visible: boolean
  title?: string
  message: string
  details?: string[]
  confirmText?: string
  cancelText?: string
  danger?: boolean
  loading?: boolean
  requireText?: string
  confirmInput?: string
}>(), {
  details: () => [],
  confirmInput: '',
})

const emit = defineEmits<{
  confirm: []
  cancel: []
  'update:confirmInput': [value: string]
}>()

const canConfirm = computed(() => {
  if (props.loading) return false
  if (!props.requireText) return true
  return (props.confirmInput || '').trim() === props.requireText
})

function handleConfirm() {
  if (canConfirm.value) emit('confirm')
}
</script>

<template>
  <Transition name="fade">
    <div v-if="visible" class="confirm-backdrop" @click.self="!loading && emit('cancel')">
      <div class="confirm-panel" :class="{ 'confirm-panel--danger': danger }">
        <div class="confirm-icon" :class="{ 'confirm-icon--danger': danger }">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 2.25l7 12.25H2L9 2.25z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M9 6.5v3.75" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <circle cx="9" cy="13" r="0.8" fill="currentColor"/>
          </svg>
        </div>
        <div class="confirm-content">
          <h3>{{ title || '确认操作' }}</h3>
          <p>{{ message }}</p>
          <ul v-if="details.length" class="confirm-details">
            <li v-for="item in details" :key="item">{{ item }}</li>
          </ul>
          <label v-if="requireText" class="confirm-require">
            <span>输入 <strong>{{ requireText }}</strong> 以确认</span>
            <input
              :value="confirmInput"
              :disabled="loading"
              autocomplete="off"
              @input="emit('update:confirmInput', ($event.target as HTMLInputElement).value)"
              @keydown.enter="handleConfirm"
            />
          </label>
        </div>
        <div class="confirm-actions">
          <button class="btn btn-outline btn-sm" :disabled="loading" @click="emit('cancel')">
            {{ cancelText || '取消' }}
          </button>
          <button
            class="confirm-submit btn btn-sm"
            :class="danger ? 'confirm-submit--danger' : 'btn-primary'"
            :disabled="!canConfirm"
            @click="handleConfirm"
          >
            {{ loading ? '处理中...' : (confirmText || '确认') }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(20, 16, 8, 0.48);
}

.confirm-panel {
  width: min(440px, 100%);
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 14px;
  padding: 20px;
  border: 1px solid #D4C898;
  border-radius: 8px;
  background: #FEF9E7;
  box-shadow: 0 18px 60px rgba(45, 37, 21, 0.2);
}

.confirm-panel--danger {
  border-color: rgba(220, 38, 38, 0.28);
}

.confirm-icon {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(232, 163, 23, 0.12);
  color: #9a5b00;
}

.confirm-icon--danger {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

.confirm-content h3 {
  margin: 0 0 8px;
  color: #2D2515;
  font-size: 16px;
  font-weight: 800;
}

.confirm-content p {
  margin: 0;
  color: #665c48;
  font-size: 13px;
  line-height: 1.6;
}

.confirm-details {
  margin: 12px 0 0;
  padding: 10px 12px 10px 26px;
  border-radius: 8px;
  background: rgba(45, 37, 21, 0.04);
  color: #665c48;
  font-size: 12px;
  line-height: 1.7;
}

.confirm-require {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 14px;
  color: #665c48;
  font-size: 12px;
  font-weight: 600;
}

.confirm-require strong {
  color: #2D2515;
}

.confirm-require input {
  height: 36px;
  border: 1px solid #D4C898;
  border-radius: 8px;
  padding: 0 10px;
  background: #FDF5D6;
  color: #2D2515;
  outline: none;
}

.confirm-require input:focus {
  border-color: #E8A317;
  box-shadow: 0 0 0 3px rgba(232, 163, 23, 0.12);
}

.confirm-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.confirm-submit--danger {
  background: #b91c1c;
  color: #fff;
}

.confirm-submit--danger:hover:not(:disabled) {
  background: #991b1b;
}

.confirm-submit:disabled,
.confirm-actions button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
</style>
