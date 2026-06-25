<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBillingStore } from '@/stores/billing'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{
  (e: 'subscribe'): void
  (e: 'feedback'): void
  (e: 'notification'): void
  (e: 'message'): void
}>()

const router = useRouter()
const billingStore = useBillingStore()
const authStore = useAuthStore()
const userMenuOpen = ref(false)
const loggingOut = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

function openAIConfig() {
  router.push('/settings')
}

function handleAvatarClick() {
  if (authStore.isLoggedIn) {
    userMenuOpen.value = !userMenuOpen.value
  } else {
    router.push('/login')
  }
}

function closeUserMenu() {
  userMenuOpen.value = false
}

function handleDocumentClick(event: MouseEvent) {
  if (!userMenuRef.value) return
  if (!userMenuRef.value.contains(event.target as Node)) {
    closeUserMenu()
  }
}

function openSettings() {
  closeUserMenu()
  router.push('/settings')
}

async function handleLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await authStore.doLogout()
    closeUserMenu()
    router.push('/login')
  } finally {
    loggingOut.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<template>
  <div class="tba-root">
    <!-- Credits + Subscribe (Mario red capsule) -->
    <div class="tba-credits-group" @click="$emit('subscribe')">
      <span class="tba-credits-icon">✦</span>
      <span class="tba-credits-num">{{ billingStore.credits }}</span>
      <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 4L5 6L7 4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <div class="tba-divider" />
      <span class="tba-subscribe-label">订阅</span>
    </div>

    <!-- Feedback -->
    <button class="tba-icon-btn" title="反馈" @click="$emit('feedback')">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M4 5.5A1.5 1.5 0 015.5 4h9A1.5 1.5 0 0116 5.5v7a1.5 1.5 0 01-1.5 1.5H8.5L6 16v-3H5.5A1.5 1.5 0 014 11.5v-6z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M7.5 8h5M7.5 10.5h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
    </button>

    <!-- Notification -->
    <button class="tba-icon-btn" title="通知" @click="$emit('notification')">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 3a4 4 0 00-4 4v3c0 .9-.4 1.75-1.1 2.35l-.4.3a.75.75 0 00.5 1.35h10a.75.75 0 00.5-1.35l-.4-.3A3.5 3.5 0 0114 10V7a4 4 0 00-4-4z" stroke="currentColor" stroke-width="1.4"/><path d="M8 14s.5 2 2 2 2-2 2-2" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    </button>

    <!-- Messages -->
    <button class="tba-icon-btn" title="消息" @click="$emit('message')">
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect x="3" y="4.5" width="14" height="10" rx="1.5" stroke="currentColor" stroke-width="1.4"/><path d="M3 6l7 4.5L17 6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
    </button>

    <button class="tba-ai-config" title="AI Config" @click="openAIConfig">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
        <path d="M8 2.25l1.05 2.68 2.7 1.07-2.7 1.07L8 9.75 6.95 7.07 4.25 6l2.7-1.07L8 2.25z" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/>
        <path d="M12.25 9.25l.55 1.4 1.45.6-1.45.6-.55 1.4-.55-1.4-1.45-.6 1.45-.6.55-1.4z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
      </svg>
      <span>AI 配置</span>
    </button>

    <div ref="userMenuRef" class="tba-user-menu">
      <button
        class="tba-avatar"
        type="button"
        :title="authStore.isLoggedIn ? authStore.displayName : '未登录'"
        @click="handleAvatarClick"
      >
        {{ authStore.isLoggedIn ? authStore.displayName.charAt(0).toUpperCase() : 'U' }}
      </button>

      <Transition name="user-menu">
        <div v-if="authStore.isLoggedIn && userMenuOpen" class="tba-user-popover">
          <div class="tba-user-summary">
            <span class="tba-user-name">{{ authStore.displayName }}</span>
            <span class="tba-user-email">{{ authStore.user?.email || '已登录账号' }}</span>
          </div>
          <button type="button" class="tba-menu-item" @click="openSettings">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M8 2.25l1.05 2.68 2.7 1.07-2.7 1.07L8 9.75 6.95 7.07 4.25 6l2.7-1.07L8 2.25z" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/>
              <path d="M12.25 9.25l.55 1.4 1.45.6-1.45.6-.55 1.4-.55-1.4-1.45-.6 1.45-.6.55-1.4z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/>
            </svg>
            账号设置
          </button>
          <button type="button" class="tba-menu-item tba-menu-item--danger" :disabled="loggingOut" @click="handleLogout">
            <svg width="15" height="15" viewBox="0 0 16 16" fill="none">
              <path d="M6.25 3H4.5A1.5 1.5 0 003 4.5v7A1.5 1.5 0 004.5 13h1.75" stroke="currentColor" stroke-width="1.35" stroke-linecap="round"/>
              <path d="M9 5l3 3-3 3M12 8H6.5" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ loggingOut ? '退出中...' : '退出登录' }}
          </button>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.tba-root {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── Credits + Subscribe red capsule ── */
.tba-credits-group {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  border-radius: 2px;
  background: rgba(232, 163, 23, 0.15);
  cursor: pointer;
  transition: all 0.15s;
  border: 2px solid rgba(232, 163, 23, 0.2);
}
.tba-credits-group:hover {
  background: rgba(232, 163, 23, 0.25);
}

.tba-credits-icon {
  color: #E8A317;
  font-size: 15px;
}

.tba-credits-num {
  font-weight: 600;
  font-size: 14px;
  color: #E8A317;
}

.tba-credits-group svg {
  color: #E8A317;
  opacity: 0.6;
}

.tba-divider {
  width: 1px;
  height: 16px;
  background: rgba(232, 163, 23, 0.3);
  margin: 0 4px;
}

.tba-subscribe-label {
  font-size: 13px;
  font-weight: 600;
  color: #E8A317;
}

/* ── Icon buttons ── */
.tba-icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6B5D40;
  background: none;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}
.tba-icon-btn:hover {
  background: rgba(0,0,0,0.04);
  color: #111111;
}

/* ── Avatar ── */
.tba-user-menu {
  position: relative;
}

.tba-avatar {
  width: 32px;
  height: 32px;
  border-radius: 2px;
  background: #E8A317;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  margin-left: 2px;
  border: none;
}
.tba-avatar:hover {
  background: #C88A0C;
}

.tba-user-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 80;
  width: 210px;
  padding: 8px;
  border: 1px solid #D4C898;
  border-radius: 8px;
  background: #FEF9E7;
  box-shadow: 0 14px 40px rgba(45, 37, 21, 0.18);
}

.tba-user-summary {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 9px 10px;
  border-bottom: 1px solid rgba(212, 200, 152, 0.75);
  margin-bottom: 6px;
}

.tba-user-name {
  font-size: 13px;
  font-weight: 700;
  color: #2D2515;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tba-user-email {
  font-size: 11px;
  color: #8a7d62;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tba-menu-item {
  width: 100%;
  height: 34px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 9px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #6B5D40;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.tba-menu-item:hover:not(:disabled) {
  background: rgba(232, 163, 23, 0.1);
  color: #2D2515;
}

.tba-menu-item--danger {
  color: #b91c1c;
}

.tba-menu-item--danger:hover:not(:disabled) {
  background: rgba(220, 38, 38, 0.08);
  color: #991b1b;
}

.tba-menu-item:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.user-menu-enter-active,
.user-menu-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.user-menu-enter-from,
.user-menu-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.tba-ai-config {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border: 2px solid #D4C898;
  border-radius: 2px;
  background: transparent;
  color: #6B5D40;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.tba-ai-config:hover {
  border-color: #F5C34B;
  background: rgba(245, 195, 75, 0.08);
  color: #F5C34B;
}

.tba-ai-config svg {
  color: currentColor;
}

@media (max-width: 720px) {
  .tba-ai-config {
    width: 36px;
    padding: 0;
  }

  .tba-ai-config span {
    display: none;
  }
}
</style>
