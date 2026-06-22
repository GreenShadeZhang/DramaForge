<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '@/stores/project'
import { useAssetsStore } from '@/stores/assets'
import { assetsApi } from '@/api/assets'
import CharacterCard from '@/components/assets/CharacterCard.vue'
import SceneCard from '@/components/assets/SceneCard.vue'
import CharacterEditModal from '@/components/assets/CharacterEditModal.vue'
import SceneEditModal from '@/components/assets/SceneEditModal.vue'
import GenerateAssetsModal from '@/components/assets/GenerateAssetsModal.vue'
import RegenerateModal from '@/components/assets/RegenerateModal.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { ProjectStep, VideoStyle } from '@/types/enums'
import type { CharacterDetail, CharacterUpdate, RefImage } from '@/types/character'
import type { SceneDetail, SceneUpdate } from '@/types/scene'

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const assetsStore = useAssetsStore()

const projectId = Number(route.params.id)
const activeTab = ref<'characters' | 'scenes'>('characters')
const approving = ref(false)

// ── Generate modal state ──
const showGenModal = ref(false)
const isGenerating = ref(false)
const genProgress = ref('')

// ── Regenerate modal state ──
const showRegenModal = ref(false)
const regenType = ref<'character' | 'scene'>('character')
const regenTarget = ref<CharacterDetail | SceneDetail | null>(null)
const regenLoading = ref(false)

// ── Edit modal state ──
const editingCharacter = ref<CharacterDetail | null>(null)
const showCharEdit = ref(false)
const editingScene = ref<SceneDetail | null>(null)
const showSceneEdit = ref(false)

onMounted(async () => {
  await assetsStore.fetchAssets(projectId)
  // Ensure project step is at least ASSETS when on this page
  if (projectStore.currentProject && projectStore.currentProject.status === ProjectStep.SCRIPT) {
    projectStore.currentProject.status = ProjectStep.ASSETS
  }
})

const charCount = computed(() => assetsStore.characters.length)
const sceneCount = computed(() => assetsStore.scenes.length)

// ── Generate all assets ──

const genProgressMessages = [
  '正在分析剧本角色特征...',
  '生成角色形象描述...',
  '绘制角色形象图...',
  '分析场景环境要素...',
  '生成场景描述...',
  '绘制场景图...',
  '整理优化中...',
]

async function handleGenerate(options: { style: string; target: string }) {
  isGenerating.value = true
  genProgress.value = genProgressMessages[0]

  // Simulate progress updates
  let msgIdx = 0
  const progressTimer = setInterval(() => {
    msgIdx = Math.min(msgIdx + 1, genProgressMessages.length - 1)
    genProgress.value = genProgressMessages[msgIdx]
  }, 2500)

  try {
    await assetsStore.generateAll(projectId)
  } catch (e: any) {
    console.error('Failed to generate assets:', e)
  } finally {
    clearInterval(progressTimer)
    isGenerating.value = false
    showGenModal.value = false
    genProgress.value = ''
    await assetsStore.fetchAssets(projectId)
  }
}

// ── Canvas workspace state ──
const canvasChar = ref<CharacterDetail | null>(null)
const canvasImages = ref<RefImage[]>([])
const canvasSaving = ref(false)

function openImageCanvas(char: CharacterDetail) {
  canvasChar.value = char
  canvasImages.value = (char.reference_images || []).map(img =>
    typeof img === 'string' ? { url: img, name: '' } : { ...img }
  )
  // Reset upload state when opening canvas
  uploadingCharId.value = null
}

function closeImageCanvas() {
  canvasChar.value = null
  canvasImages.value = []
}

function canvasImageName(img: RefImage, idx: number) {
  return img.name || `形象图 ${idx + 1}`
}

async function canvasSave() {
  if (!canvasChar.value) return
  canvasSaving.value = true
  try {
    await assetsApi.updateCharacter(
      projectId, canvasChar.value.id,
      { reference_images: canvasImages.value } as CharacterUpdate,
    )
    await assetsStore.fetchAssets(projectId)
  } finally { canvasSaving.value = false }
}

function canvasUpdateName(idx: number, name: string) {
  canvasImages.value[idx] = { ...canvasImages.value[idx], name }
}

async function canvasDeleteImage(idx: number) {
  canvasImages.value = canvasImages.value.filter((_, i) => i !== idx)
  await canvasSave()
}

// Trigger upload from canvas
async function canvasHandleFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploadingCharId.value = canvasChar.value?.id || null
  try {
    const fd = new FormData(); fd.append('file', file)
    const { data } = await assetsApi.uploadAsset(fd)
    if (data?.url) {
      canvasImages.value = [...canvasImages.value, { url: data.url, name: file.name.replace(/\.[^.]+$/, '') }]
      await canvasSave()
    }
  } catch (err) { console.error('Upload failed', err) }
  finally {
    uploadingCharId.value = null
    if (charFileInput.value) charFileInput.value.value = ''
  }
}

// ── Character actions ──
const uploadingCharId = ref<number | null>(null)
const charFileInput = ref<HTMLInputElement | null>(null)

function openCharEdit(char: CharacterDetail) {
  editingCharacter.value = char
  showCharEdit.value = true
}

function triggerCharImageUpload(char: CharacterDetail) {
  uploadingCharId.value = char.id
  charFileInput.value?.click()
}

async function handleCharImageFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  const charId = uploadingCharId.value
  if (!file || !charId) { uploadingCharId.value = null; return }

  try {
    const formData = new FormData()
    formData.append('file', file)
    const { data: uploaded } = await assetsApi.uploadAsset(formData)
    if (uploaded?.url) {
      const char = assetsStore.characters.find(c => c.id === charId)
      const existing = char?.reference_images || []
      await assetsApi.updateCharacter(projectId, charId, {
        reference_images: [...existing, { url: uploaded.url, name: uploaded.name || '形象图' }],
      } as CharacterUpdate)
      await assetsStore.fetchAssets(projectId)
    }
  } catch (err) {
    console.error('上传形象图失败', err)
  } finally {
    uploadingCharId.value = null
    if (charFileInput.value) charFileInput.value.value = ''
  }
}

async function saveCharEdit(data: Partial<CharacterDetail>) {
  if (!editingCharacter.value) return
  try {
    await assetsApi.updateCharacter(projectId, editingCharacter.value.id, data as CharacterUpdate)
    showCharEdit.value = false
    await assetsStore.fetchAssets(projectId)
  } catch (e: any) {
    console.error('Failed to update character:', e)
  }
}

// ── Regenerate (opens modal) ──
function openRegenCharacter(char: CharacterDetail) {
  regenType.value = 'character'
  regenTarget.value = char
  showRegenModal.value = true
}
function openRegenScene(scene: SceneDetail) {
  regenType.value = 'scene'
  regenTarget.value = scene
  showRegenModal.value = true
}

async function confirmRegenerate(prompt: string) {
  if (!regenTarget.value) return
  regenLoading.value = true
  try {
    if (regenType.value === 'character') {
      const char = regenTarget.value as CharacterDetail
      await assetsApi.regenerateCharacter(projectId, char.id, prompt || undefined)
    } else {
      const scene = regenTarget.value as SceneDetail
      await assetsApi.regenerateScene(projectId, scene.id, prompt || undefined)
    }
    showRegenModal.value = false
    await assetsStore.fetchAssets(projectId)
  } catch (e: any) {
    console.error('Regenerate failed:', e)
    // Keep modal open on error so user can retry
  } finally {
    regenLoading.value = false
  }
}

// ── Scene actions ──

function openSceneEdit(scene: SceneDetail) {
  editingScene.value = scene
  showSceneEdit.value = true
}

async function saveSceneEdit(data: Partial<SceneDetail>) {
  if (!editingScene.value) return
  try {
    await assetsApi.updateScene(projectId, editingScene.value.id, data as SceneUpdate)
    showSceneEdit.value = false
    await assetsStore.fetchAssets(projectId)
  } catch (e: any) {
    console.error('Failed to update scene:', e)
  }
}

// ── Navigation ──

function goBackToScript() {
  if (projectStore.currentProject) {
    projectStore.currentProject.status = ProjectStep.SCRIPT
  }
  router.push(`/projects/${projectId}/script`)
}

// ── Approve ──

async function handleApprove() {
  approving.value = true
  try {
    await assetsApi.approve(projectId)
    // Force-update store so StepNavigator reflects the change immediately
    if (projectStore.currentProject) {
      projectStore.currentProject.status = ProjectStep.STORYBOARD
    }
    router.push(`/projects/${projectId}/episodes`)
  } finally {
    approving.value = false
  }
}
</script>

<template>
  <LoadingOverlay :visible="assetsStore.loading" message="正在加载资产..." />

  <div class="page-container-wide">
    <!-- ═══ Header with nav ═══ -->
    <div class="assets-header">
      <div class="assets-header-left">
        <h1 class="assets-title">角色 & 场景资产</h1>
        <p class="assets-subtitle">管理剧中角色和场景的视觉设定</p>
      </div>
      <div class="assets-header-actions">
        <button class="btn btn-primary btn-sm" @click="showGenModal = true" :disabled="isGenerating">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M13.5 2.5l-4 4M8.5 2.5h5v5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M6 3H3.5a1 1 0 00-1 1v8.5a1 1 0 001 1H12a1 1 0 001-1V10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
          {{ isGenerating ? '生成中...' : '生成资产' }}
        </button>
        <button class="btn btn-outline btn-sm" @click="goBackToScript">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9 2L4 7l5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
          返回剧本
        </button>
        <button class="btn btn-outline btn-sm" @click="router.push(`/projects/${projectId}/episodes`)">
          管理剧集
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 2l5 5-5 5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="assets-tabs">
      <button
        class="assets-tab"
        :class="{ active: activeTab === 'characters' }"
        @click="activeTab = 'characters'"
      >
        全部角色 {{ charCount }}
      </button>
      <button
        class="assets-tab"
        :class="{ active: activeTab === 'scenes' }"
        @click="activeTab = 'scenes'"
      >
        全部场景 {{ sceneCount }}
      </button>
    </div>

    <!-- Characters: canvas workspace or grid -->
    <div v-if="activeTab === 'characters'">
      <!-- ═══ Canvas Workspace (when a character is selected) ═══ -->
      <div v-if="canvasChar" class="canvas-workspace">
        <!-- Canvas header -->
        <div class="canvas-header">
          <button class="canvas-back-btn" @click="closeImageCanvas">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9 2L4 7l5 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span>返回角色列表</span>
          </button>
          <div class="canvas-header-info">
            <span class="canvas-char-name">{{ canvasChar.name }}</span>
            <span class="canvas-char-role">· {{ canvasChar.role }} · {{ canvasImages.length }} 张形象图</span>
          </div>
          <div class="canvas-header-actions">
            <button class="btn btn-primary btn-sm" @click="charFileInput?.click()" :disabled="!!uploadingCharId">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><line x1="7" y1="2" x2="7" y2="12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="2" y1="7" x2="12" y2="7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
              上传形象图
            </button>
          </div>
        </div>

        <!-- Canvas area -->
        <div class="canvas-area">
          <div v-if="!canvasImages.length" class="canvas-empty">
            <span class="text-6xl mb-4">🖼️</span>
            <p class="text-gray-600 text-lg mb-2">暂无形象图</p>
            <p class="text-gray-500">点击上方「上传形象图」或使用 AI 生成角色形象</p>
          </div>

          <div v-else class="canvas-grid">
            <div
              v-for="(img, idx) in canvasImages"
              :key="idx"
              class="canvas-card group"
            >
              <!-- Image -->
              <div class="canvas-card-pic">
                <img :src="img.url" :alt="canvasImageName(img, idx)" class="w-full h-full object-cover" />
                <!-- Delete overlay -->
                <button class="canvas-delete-btn" title="删除" @click="canvasDeleteImage(idx)">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2.5 4h9M5 4V2.5a.5.5 0 01.5-.5h3a.5.5 0 01.5.5V4M10.5 4v6a2 2 0 01-2 2h-3a2 2 0 01-2-2V4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </button>
              </div>
              <!-- Name -->
              <div class="canvas-card-name">
                <input
                  :value="canvasImageName(img, idx)"
                  class="canvas-name-input"
                  placeholder="形象图名称"
                  @input="canvasUpdateName(idx, ($event.target as HTMLInputElement).value)"
                  @blur="canvasSave()"
                />
              </div>
            </div>

            <!-- Add card -->
            <button
              class="canvas-card canvas-card-add"
              :disabled="!!uploadingCharId"
              @click="charFileInput?.click()"
            >
              <div class="canvas-card-pic canvas-add-pic">
                <svg v-if="uploadingCharId" class="animate-spin" width="36" height="36" viewBox="0 0 36 36" fill="none">
                  <circle cx="18" cy="18" r="14" stroke="currentColor" stroke-width="2.5" stroke-dasharray="56 18" stroke-linecap="round"/>
                </svg>
                <template v-else>
                  <svg width="36" height="36" viewBox="0 0 36 36" fill="none"><line x1="18" y1="8" x2="18" y2="28" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="8" y1="18" x2="28" y2="18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>
                  <span class="text-sm mt-2 font-semibold">添加形象图</span>
                </template>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- ═══ Character Grid (default view) ═══ -->
      <template v-else>
        <EmptyState
          v-if="!assetsStore.loading && !charCount"
          title="暂无角色"
          description="生成资产后将在这里显示"
          icon="👤"
        />
        <div v-else class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-5">
          <CharacterCard
            v-for="char in assetsStore.characters"
            :key="char.id"
            :character="char"
            :regenerating="false"
            :uploading-image="uploadingCharId === char.id"
            @edit="openCharEdit"
            @regenerate="openRegenCharacter"
            @add-image="triggerCharImageUpload"
            @open-gallery="openImageCanvas"
          />
        </div>
      </template>

      <!-- Hidden file input (shared between grid upload and canvas upload) -->
      <input
        ref="charFileInput"
        type="file"
        accept="image/*"
        class="hidden"
        @change="canvasChar ? canvasHandleFile($event) : handleCharImageFile($event)"
      />
    </div>

    <!-- Scenes grid -->
    <div v-if="activeTab === 'scenes'">
      <EmptyState
        v-if="!assetsStore.loading && !sceneCount"
        title="暂无场景"
        description="生成资产后将在这里显示"
        icon="🏠"
      />
      <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        <SceneCard
          v-for="scene in assetsStore.scenes"
          :key="scene.id"
          :scene="scene"
          :regenerating="false"
          @edit="openSceneEdit"
          @regenerate="openRegenScene"
        />
      </div>
    </div>
  </div>

  <!-- ── Generate Modal ── -->
  <GenerateAssetsModal
    :visible="showGenModal"
    :generating="isGenerating"
    :progress="genProgress"
    :char-count="charCount"
    :scene-count="sceneCount"
    @close="showGenModal = false"
    @generate="handleGenerate"
  />

  <!-- ── Regenerate Modal ── -->
  <RegenerateModal
    :visible="showRegenModal"
    :type="regenType"
    :name="(regenTarget as any)?.name || ''"
    :description="(regenTarget as any)?.description || ''"
    :loading="regenLoading"
    :current-prompt="(regenTarget as any)?.description || ''"
    @close="showRegenModal = false"
    @confirm="confirmRegenerate"
  />

  <!-- ── Edit Modals ── -->
  <CharacterEditModal
    :visible="showCharEdit"
    :character="editingCharacter"
    @close="showCharEdit = false"
    @save="saveCharEdit"
  />
  <SceneEditModal
    :visible="showSceneEdit"
    :scene="editingScene"
    @close="showSceneEdit = false"
    @save="saveSceneEdit"
  />

  <!-- Bottom bar -->
  <div class="bottom-action-bar">
    <div class="bar-hint">
      <div class="bar-icon">🤖</div>
      <span>角色和场景设定会应用到整部剧集中，建议调整完毕后再继续</span>
    </div>
    <div class="bar-actions">
      <button class="btn btn-outline btn-sm" @click="goBackToScript">
        ← 上一步
      </button>
      <button class="btn btn-primary btn-sm" @click="handleApprove" :disabled="approving">
        {{ approving ? '确认中...' : '下一步 →' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* ── Header ── */
.assets-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}
.assets-header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.assets-title {
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}
.assets-subtitle {
  font-size: 13px;
  color: #9CA3AF;
  margin: 0;
}
.assets-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.assets-tabs {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 28px;
  border-bottom: 1px solid #FDF4D8;
}

.assets-tab {
  position: relative;
  padding: 10px 4px;
  font-size: 15px;
  font-weight: 500;
  color: #999;
  background: none;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}

.assets-tab:hover {
  color: #555;
}

.assets-tab.active {
  color: #2D2515;
  font-weight: 600;
}

.assets-tab.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: #2D2515;
  border-radius: 1px;
}

/* ═══ Canvas Workspace ═══ */
.canvas-workspace {
  border: 2px solid #D4C898;
  border-radius: 2px;
  background: #FEF9E7;
  box-shadow: 4px 4px 0 0 rgba(0,0,0,0.08);
  overflow: hidden;
}
.canvas-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 2px solid #D4C898;
  background: #FDF5D6;
}
.canvas-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 2px;
  border: 2px solid #D4C898;
  background: transparent;
  color: #6B5D40;
  font-size: 12px;
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  letter-spacing: 1px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
}
.canvas-back-btn:hover {
  background: rgba(232,163,23,0.08);
  border-color: #E8A317;
  color: #E8A317;
}
.canvas-header-info {
  flex: 1;
  display: flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
}
.canvas-char-name {
  font-family: 'Press Start 2P', monospace;
  font-size: 13px;
  color: #2D2515;
  letter-spacing: 2px;
}
.canvas-char-role {
  font-size: 13px;
  color: #8B7A5A;
}
.canvas-header-actions {
  flex-shrink: 0;
}

/* Canvas area */
.canvas-area {
  padding: 20px;
  min-height: 400px;
  background:
    linear-gradient(45deg, #FDF4D8 25%, transparent 25%),
    linear-gradient(-45deg, #FDF4D8 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #FDF4D8 75%),
    linear-gradient(-45deg, transparent 75%, #FDF4D8 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0;
}
.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

/* Canvas image grid */
.canvas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

/* Canvas image card */
.canvas-card {
  display: flex;
  flex-direction: column;
  border-radius: 2px;
  overflow: hidden;
  border: 2px solid #D4C898;
  background: #FDF5D6;
  box-shadow: 4px 4px 0 0 rgba(0,0,0,0.1);
  transition: box-shadow 0.15s, transform 0.15s;
}
.canvas-card:hover {
  box-shadow: 2px 2px 0 0 rgba(0,0,0,0.1);
  transform: translate(2px, 2px);
}
.canvas-card-pic {
  aspect-ratio: 1;
  position: relative;
  overflow: hidden;
  background: #FDF4D8;
}
.canvas-delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 30px; height: 30px;
  border-radius: 2px;
  background: rgba(231,76,60,0.85);
  color: #fff;
  border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
}
.group:hover .canvas-delete-btn { opacity: 1; }
.canvas-delete-btn:hover { background: #E74C3C; }

.canvas-card-name {
  padding: 10px 12px;
}
.canvas-name-input {
  width: 100%;
  border: none;
  border-bottom: 2px solid transparent;
  outline: none;
  background: transparent;
  font-family: 'Press Start 2P', monospace;
  font-size: 9px;
  color: #4A3F28;
  letter-spacing: 1px;
  text-align: center;
  padding: 4px 0;
  transition: border-color 0.15s;
}
.canvas-name-input:focus {
  border-bottom-color: #E8A317;
}
.canvas-name-input::placeholder {
  color: #A89870;
}

/* Add card */
.canvas-card-add {
  cursor: pointer;
  border-style: dashed;
  background: transparent;
}
.canvas-card-add:hover {
  border-color: #E8A317;
  background: rgba(232,163,23,0.05);
}
.canvas-card-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.canvas-add-pic {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #A89870;
}
</style>
