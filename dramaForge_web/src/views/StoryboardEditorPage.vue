<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { useStoryboardStore } from '@/stores/storyboard'
import { useAssetsStore } from '@/stores/assets'
import { useUserAIConfigStore } from '@/stores/user-ai-config'
import { storyboardApi } from '@/api/storyboard'
import type { StoryboardGenerationStatus } from '@/api/storyboard'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import TopbarActions from '@/components/common/TopbarActions.vue'
import AssetPanel from '@/components/storyboard/AssetPanel.vue'
import StoryboardScript from '@/components/storyboard/StoryboardScript.vue'
import PreviewPanel from '@/components/storyboard/PreviewPanel.vue'
import Timeline from '@/components/storyboard/Timeline.vue'
import ShotEditor from '@/components/storyboard/ShotEditor.vue'
import type { ShotDetail, ShotUpdate, ShotVisualReference } from '@/types/shot'
import type { CharacterDetail } from '@/types/character'
import type { SceneDetail } from '@/types/scene'
import type { SegmentDetail } from '@/types/segment'

const route = useRoute()
const router = useRouter()
const sbStore = useStoryboardStore()
const assetsStore = useAssetsStore()
const aiConfigStore = useUserAIConfigStore()

const projectId = Number(route.params.id)
const episodeId = Number(route.params.epId)

// ── Asset lock state (episode-scoped) ──
const lockedCharacterIds = ref(new Set<number>())

function toggleCharacterLock(charId: number) {
  const next = new Set(lockedCharacterIds.value)
  if (next.has(charId)) {
    next.delete(charId)
  } else {
    next.add(charId)
  }
  lockedCharacterIds.value = next
}

// ── Model selection (dynamic from user config) ──
const modelOptions = computed(() => {
  const models = aiConfigStore.modelsByType.video
  if (!models.length) return []
  return models.map(m => ({
    value: String(m.id),
    label: `${m.provider_name} · ${m.display_name || m.model_id}`,
    supportsReferences: supportsVideoReferences(effectiveVideoCapabilities(m)),
  }))
})
const selectedModel = ref('')
const selectedAspectRatio = ref<'9:16' | '16:9' | '1:1'>('9:16')
const selectedGenerationResolution = ref('720x1280')
const selectedVideoModel = computed(() => {
  const id = Number(selectedModel.value)
  return aiConfigStore.modelsByType.video.find(model => model.id === id) || null
})
function effectiveVideoCapabilities(model: any) {
  return { ...(model?.effective_capabilities_json || model?.capabilities_json || {}) }
}
const currentVideoCapabilities = computed(() => effectiveVideoCapabilities(selectedVideoModel.value))
const currentModelSupportsReferences = computed(() =>
  supportsVideoReferences(currentVideoCapabilities.value)
)
const currentModelSupportsSize = computed(() =>
  supportsVideoSize(currentVideoCapabilities.value)
)
const currentModelSupportsAspectRatio = computed(() =>
  Boolean(currentVideoCapabilities.value.video_aspect_ratio)
)
const referenceCapableModels = computed(() =>
  aiConfigStore.modelsByType.video.filter(model => supportsVideoReferences(effectiveVideoCapabilities(model)))
)
const referenceModelHint = computed(() => {
  if (!aiConfigStore.modelsByType.video.length) return '请先在设置页配置视频模型'
  if (currentModelSupportsReferences.value) return '当前模型支持参考图'
  if (referenceCapableModels.value.length) {
    return `可切换：${referenceCapableModels.value.map(model => model.display_name || model.model_id).join('、')}`
  }
  return '可用模型：Veo 3.1 Fast、Sora 2、Runway Gen-4 Turbo、Kling I2V'
})
function supportsVideoReferences(caps: Record<string, any> | undefined) {
  return Boolean(caps?.video_reference_images || caps?.video_first_frame || caps?.video_multi_reference)
}
function supportsVideoSize(caps: Record<string, any> | undefined) {
  return Boolean(caps?.video_size || supportedVideoSizes(caps).length)
}
function supportedVideoSizes(caps: Record<string, any> | undefined) {
  const value = caps?.video_supported_sizes
  if (Array.isArray(value)) return value.map(item => String(item).trim()).filter(Boolean)
  if (typeof value === 'string') {
    return value.split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
  }
  return []
}

const aspectRatioOptions = [
  { value: '9:16', label: '竖屏 9:16' },
  { value: '16:9', label: '横屏 16:9' },
  { value: '1:1', label: '方形 1:1' },
] as const

const generationResolutionOptions = computed(() => {
  if (!currentModelSupportsSize.value) return []
  const configured = supportedVideoSizes(currentVideoCapabilities.value)
  if (configured.length) {
    return configured.map(value => ({ value, label: value }))
  }
  if (!currentModelSupportsAspectRatio.value) {
    return [
      { value: '720x1280', label: '720P · 720x1280' },
      { value: '1080x1920', label: '1080P · 1080x1920' },
      { value: '1280x720', label: '720P · 1280x720' },
      { value: '1920x1080', label: '1080P · 1920x1080' },
    ]
  }
  if (selectedAspectRatio.value === '16:9') {
    return [
      { value: '1280x720', label: '720P · 1280x720' },
      { value: '1920x1080', label: '1080P · 1920x1080' },
    ]
  }
  if (selectedAspectRatio.value === '1:1') {
    return [
      { value: '720x720', label: '720P · 720x720' },
      { value: '1024x1024', label: '1024 · 1024x1024' },
    ]
  }
  return [
    { value: '720x1280', label: '720P · 720x1280' },
    { value: '1080x1920', label: '1080P · 1080x1920' },
  ]
})

watch(generationResolutionOptions, (opts) => {
  if (!opts.find(opt => opt.value === selectedGenerationResolution.value)) {
    selectedGenerationResolution.value = opts[0]?.value || ''
  }
}, { immediate: true })

function videoGenerateOptions() {
  return {
    video_model_config_id: Number(selectedModel.value) || undefined,
    resolution: currentModelSupportsSize.value ? selectedGenerationResolution.value || undefined : undefined,
    aspect_ratio: currentModelSupportsAspectRatio.value ? selectedAspectRatio.value || undefined : undefined,
  }
}
// Sync selectedModel when modelOptions load
watch(modelOptions, (opts) => {
  if (opts.length && !opts.find(o => o.value === selectedModel.value)) {
    selectedModel.value = opts[0].value
  }
}, { immediate: true })

// ── Editing state ──
const editingShot = ref(false)
const savingShot = ref(false)
const savingScript = ref(false)

// ── Generation state ──
const generatingSegmentIds = ref<Set<number>>(new Set())
const generatingShotIds = ref<Set<number>>(new Set())
const storyboardGenerationStatus = ref<StoryboardGenerationStatus>({
  status: 'idle',
  progress: 0,
  message: '尚未生成分镜',
})
const composing = ref(false)
const downloading = ref(false)
const exporting = ref(false)
const addingShot = ref(false)
const deletingShotId = ref<number | null>(null)

// ── Compose options (P1-2 & P1-3) ──
const composeQuality = ref<'high' | 'medium' | 'low'>('high')
const composeResolution = ref('')
const composeSubtitleText = ref('')
const composeSubtitleFontSize = ref(24)
const composeBgmVolume = ref(0.15)
const bgmUploading = ref(false)
const hasBgm = ref(false)
const showComposeOptions = ref(false)

// ── Toast messages ──
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'info'>('info')
let toastTimer: ReturnType<typeof setTimeout> | null = null

function showToast(msg: string, type: 'success' | 'error' | 'info' = 'info') {
  toastMessage.value = msg
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMessage.value = '' }, 4000)
}

// ── Polling ──
let pollTimer: ReturnType<typeof setInterval> | null = null
let previousSegmentStatuses: Record<number, string> = {}
let pollCount = 0
const MAX_POLL_COUNT = 200  // ~10 minutes max
const POLL_INTERVAL = 3000

function startPolling() {
  if (pollTimer) return
  pollCount = 0
  // Snapshot current segment count to detect new segments appearing
  const segmentCountBefore = sbStore.storyboard?.segments?.length || 0
  pollTimer = setInterval(async () => {
    pollCount++
    try {
      await sbStore.fetchStoryboard(projectId, episodeId)
      const segments = sbStore.storyboard?.segments || []

      if (sbStore.generatingStoryboard) {
        const { data: status } = await storyboardApi.getGenerationStatus(projectId, episodeId)
        storyboardGenerationStatus.value = status
        if (status.status === 'failed' || status.status === 'cancelled') {
          sbStore.onStoryboardGenerated()
          if (status.status === 'cancelled') {
            showToast(status.message || '分镜生成已取消', 'info')
          } else {
            showToast(status.message || '分镜脚本生成失败', 'error')
          }
        }
      }

      // Detect storyboard generation: segments appeared where there were none,
      // or segment count increased (background task finished)
      if (sbStore.generatingStoryboard && segments.length > 0) {
        if (segmentCountBefore === 0 || segments.length > segmentCountBefore) {
          sbStore.onStoryboardGenerated()
          storyboardGenerationStatus.value = {
            status: 'completed',
            progress: 100,
            message: '分镜脚本已生成完成',
          }
          notifyUser('分镜脚本', '分镜脚本已生成完成')
        }
      }

      // Track segment status changes for notification and cleanup
      for (const seg of segments) {
        const prev = previousSegmentStatuses[seg.id]
        if (prev && prev === 'generating' && seg.status !== 'generating') {
          // Segment finished generating — notify and clean up
          const label = seg.status === 'completed' ? '已完成' : '生成失败'
          notifyUser(`片段 ${seg.index + 1}`, `素材生成${label}`)
          // Remove from tracking set
          const next = new Set(generatingSegmentIds.value)
          next.delete(seg.id)
          generatingSegmentIds.value = next
        }
        previousSegmentStatuses[seg.id] = seg.status
      }

      const nextShotIds = new Set(generatingShotIds.value)
      for (const seg of segments) {
        for (const shot of seg.shots || []) {
          if (!nextShotIds.has(shot.id)) continue
          if (shot.video_url || shot.shot_status === 'failed') {
            const label = shot.video_url ? '已完成' : '生成失败'
            notifyUser(`分镜 ${shot.index + 1}`, `视频生成${label}`)
            nextShotIds.delete(shot.id)
          }
        }
      }
      generatingShotIds.value = nextShotIds

      // Stop condition
      const stillGenerating = segments.some(s => s.status === 'generating')
      const shouldStop = !stillGenerating && generatingSegmentIds.value.size === 0 && generatingShotIds.value.size === 0 && !sbStore.generatingStoryboard

      // Safety: force stop after max poll count to prevent infinite polling
      if (shouldStop || pollCount >= MAX_POLL_COUNT) {
        if (pollCount >= MAX_POLL_COUNT) {
          console.warn('[StoryboardEditor] Polling stopped after reaching max count')
          if (sbStore.generatingStoryboard) sbStore.onStoryboardGenerated()
        }
        stopPolling()
      }
    } catch { /* silent */ }
  }, POLL_INTERVAL)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  pollCount = 0
}

// ── Browser notification ──
let notificationPermission: NotificationPermission = 'default'

async function requestNotificationPermission() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') {
    notificationPermission = 'granted'
    return
  }
  if (Notification.permission === 'denied') {
    notificationPermission = 'denied'
    return
  }
  notificationPermission = await Notification.requestPermission()
}

function notifyUser(title: string, body: string) {
  if (notificationPermission === 'granted') {
    new Notification(`DramaForge · ${title}`, {
      body,
      icon: '/favicon.ico',
    })
  }
  // Also show in-page toast
  showToast(`${title}：${body}`, 'success')
}

onMounted(async () => {
  // Reset store to prevent stale data from a previous project leaking in
  sbStore.reset()
  await Promise.all([
    sbStore.fetchStoryboard(projectId, episodeId),
    assetsStore.fetchAssets(projectId),
    aiConfigStore.fetchProviders(),
  ])
  document.addEventListener('keydown', onKeydown)
  requestNotificationPermission()
})

onBeforeUnmount(() => {
  stopPolling()
  document.removeEventListener('keydown', onKeydown)
})

// ── Navigation guard ──
onBeforeRouteLeave((_to, _from, next) => {
  if (generatingSegmentIds.value.size > 0 || generatingShotIds.value.size > 0 || sbStore.generatingStoryboard) {
    const leave = window.confirm('有任务正在后台生成中，确定要离开吗？生成将在后台继续。')
    if (!leave) return next(false)
  }
  stopPolling()
  next()
})

// ── Computed ──
const totalDuration = computed(() => sbStore.storyboard?.total_duration || 0)
const episodeTitle = computed(() => sbStore.storyboard?.episode_title || '分镜编辑器')

const allSegmentsCompleted = computed(() => {
  const segs = sbStore.storyboard?.segments
  if (!segs || segs.length === 0) return false
  return segs.every(s => s.status === 'completed')
})

function goBack() {
  router.push(`/projects/${projectId}/episodes`)
}

// ── Shot selection ──
function handleSelectShot(_shot: ShotDetail, index: number) {
  sbStore.selectShot(index)
}

// ── Asset selection ──
const selectedCharacterId = ref<number | undefined>()
const selectedSceneId = ref<number | undefined>()

function handleSelectCharacter(char: CharacterDetail) {
  selectedCharacterId.value = char.id
  selectedSceneId.value = undefined
}
function handleSelectScene(scene: SceneDetail) {
  selectedSceneId.value = scene.id
  selectedCharacterId.value = undefined
}
function handleSelectNarrator() {
  selectedCharacterId.value = undefined
  selectedSceneId.value = undefined
}
function handleAddAsset() {
  router.push(`/projects/${projectId}/assets`)
}

function handlePreviewDownload(url: string) {
  if (url) window.open(url, '_blank')
}

// ── Edit / Save ──
function handleEditScript() {
  // Save snapshot for undo
  if (sbStore.currentShot) {
    sbStore.pushUndo({
      camera_type: sbStore.currentShot.camera_type,
      camera_angle: sbStore.currentShot.camera_angle,
      camera_movement: sbStore.currentShot.camera_movement,
      transition: sbStore.currentShot.transition,
      time_of_day: sbStore.currentShot.time_of_day,
      duration: sbStore.currentShot.duration,
      dialogue: sbStore.currentShot.dialogue,
      emotion: sbStore.currentShot.emotion,
      narration: sbStore.currentShot.narration,
      scene_ref: sbStore.currentShot.scene_ref,
      background: sbStore.currentShot.background,
      visual_references: sbStore.currentShot.visual_references,
    })
  }
  editingShot.value = true
}

async function handleSaveShot(data: Partial<ShotDetail>) {
  if (!sbStore.currentShot) return
  savingShot.value = true
  try {
    await storyboardApi.updateShot(projectId, episodeId, sbStore.currentShot.id, data as any)
    editingShot.value = false
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('分镜已保存', 'success')
  } catch (e: any) {
    showToast('保存失败，请重试', 'error')
  } finally {
    savingShot.value = false
  }
}

async function handleSaveScript(updates: Array<{ shot: ShotDetail; data: ShotUpdate }>) {
  if (!updates.length) return
  savingScript.value = true
  try {
    await Promise.all(
      updates.map(({ shot, data }) =>
        storyboardApi.updateShot(projectId, episodeId, shot.id, data)
      )
    )
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('脚本已保存', 'success')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '脚本保存失败，请重试', 'error')
  } finally {
    savingScript.value = false
  }
}

async function handleUpdateShotReferences(shot: ShotDetail, references: ShotVisualReference[]) {
  try {
    await storyboardApi.updateShot(projectId, episodeId, shot.id, { visual_references: references })
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('参考图已更新', 'success')
  } catch (e: any) {
    showToast('参考图保存失败', 'error')
  }
}

// ── Undo/Redo (P2-5) ──
async function handleUndo() {
  await sbStore.undo(projectId, episodeId)
  showToast('已撤销', 'info')
}
async function handleRedo() {
  await sbStore.redo(projectId, episodeId)
  showToast('已重做', 'info')
}

// Keyboard shortcuts
function onKeydown(e: KeyboardEvent) {
  if (e.ctrlKey && e.key === 'z' && !e.shiftKey) {
    e.preventDefault()
    handleUndo()
  } else if (e.ctrlKey && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
    e.preventDefault()
    handleRedo()
  }
}

function handleCancelEdit() {
  editingShot.value = false
}

// ── Generate single segment ──
async function handleGenerateSegment(segment?: SegmentDetail) {
  const seg = segment || sbStore.currentSegment
  if (!seg) return

  const segId = seg.id
  generatingSegmentIds.value = new Set([...generatingSegmentIds.value, segId])
  generatingShotIds.value = new Set([
    ...generatingShotIds.value,
    ...seg.shots.map(shot => shot.id),
  ])
  startPolling()

  try {
    await storyboardApi.generateSegment(projectId, episodeId, segId, {
      ...videoGenerateOptions(),
    })
    showToast('素材生成任务已提交', 'info')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '素材生成失败', 'error')
    const next = new Set(generatingSegmentIds.value)
    next.delete(segId)
    generatingSegmentIds.value = next
  }
}

// ── Generate single shot ──
async function handleGenerateShot(shot: ShotDetail) {
  generatingShotIds.value = new Set([...generatingShotIds.value, shot.id])
  startPolling()

  try {
    await storyboardApi.generateShot(projectId, episodeId, shot.id, {
      ...videoGenerateOptions(),
    })
    showToast(`分镜 ${shot.index + 1} 生成任务已提交`, 'info')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '分镜生成失败', 'error')
    const next = new Set(generatingShotIds.value)
    next.delete(shot.id)
    generatingShotIds.value = next
  }
}

// ── Regenerate segment ──
async function handleRegenerateSegment() {
  if (!sbStore.currentSegment) return
  const segId = sbStore.currentSegment.id
  generatingSegmentIds.value = new Set([...generatingSegmentIds.value, segId])
  generatingShotIds.value = new Set([
    ...generatingShotIds.value,
    ...sbStore.currentSegment.shots.map(shot => shot.id),
  ])
  startPolling()

  try {
    await storyboardApi.regenerateSegment(projectId, episodeId, segId, {
      ...videoGenerateOptions(),
    })
    showToast('重新生成任务已提交', 'info')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '重新生成失败', 'error')
    const next = new Set(generatingSegmentIds.value)
    next.delete(segId)
    generatingSegmentIds.value = next
  }
}

// ── Compose episode ──
async function handleCompose() {
  composing.value = true
  try {
    await storyboardApi.composeEpisode(projectId, episodeId, {
      quality: composeQuality.value,
      resolution: composeResolution.value || undefined,
      subtitle_text: composeSubtitleText.value || undefined,
      subtitle_font_size: composeSubtitleFontSize.value,
      subtitle_position: 'bottom',
      bgm_volume: hasBgm.value ? composeBgmVolume.value : 0,
    })
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('全集合成完成', 'success')
    showComposeOptions.value = false
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '合成失败，请确保所有片段素材已生成', 'error')
  } finally {
    composing.value = false
  }
}

// ── BGM upload ──
async function handleBgmUpload(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  bgmUploading.value = true
  try {
    await storyboardApi.uploadBgm(projectId, file)
    hasBgm.value = true
    showToast('BGM 上传成功', 'success')
  } catch (err: any) {
    showToast('BGM 上传失败', 'error')
  } finally {
    bgmUploading.value = false
  }
}

// ── Download episode video ──
async function handleDownload() {
  downloading.value = true
  try {
    await storyboardApi.downloadEpisode(projectId, episodeId)
    showToast('下载已开始', 'success')
  } catch (e: any) {
    showToast('下载失败', 'error')
  } finally {
    downloading.value = false
  }
}

// ── Add shot ──
async function handleAddShot() {
  const seg = sbStore.currentSegment
  if (!seg) return
  addingShot.value = true
  try {
    await storyboardApi.createShot(projectId, episodeId, seg.id)
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('新分镜已添加', 'success')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '添加分镜失败', 'error')
  } finally {
    addingShot.value = false
  }
}

// ── Delete shot ──
async function handleDeleteShot(shotId: number) {
  if (!window.confirm('确定要删除这个分镜吗？')) return
  deletingShotId.value = shotId
  try {
    await storyboardApi.deleteShot(projectId, episodeId, shotId)
    await sbStore.fetchStoryboard(projectId, episodeId)
    showToast('分镜已删除', 'success')
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '删除分镜失败', 'error')
  } finally {
    deletingShotId.value = null
  }
}

// ── Export ──
async function handleExport() {
  exporting.value = true
  try {
    await storyboardApi.exportProject(projectId)
    showToast('项目已导出', 'success')
    router.push(`/projects/${projectId}/episodes`)
  } catch (e: any) {
    showToast(e?.response?.data?.detail || '导出失败', 'error')
  } finally {
    exporting.value = false
  }
}

// ── Generate storyboard (initial) ──
async function handleGenerateStoryboard() {
  storyboardGenerationStatus.value = {
    status: 'generating',
    progress: 1,
    message: '分镜任务提交中',
  }
  try {
    await sbStore.generateStoryboard(projectId, episodeId)
    // API returned immediately; start polling to wait for completion
    startPolling()
    showToast('分镜脚本生成任务已提交', 'info')
  } catch (e: any) {
    storyboardGenerationStatus.value = {
      status: 'failed',
      progress: 100,
      message: e?.response?.data?.detail || '分镜生成失败',
    }
    showToast(e?.response?.data?.detail || '分镜生成失败', 'error')
  }
}

async function handleCancelStoryboard() {
  stopPolling()
  await sbStore.cancelStoryboardGeneration(projectId, episodeId)
  storyboardGenerationStatus.value = {
    status: 'idle',
    progress: 0,
    message: '分镜生成已取消',
  }
  showToast('分镜生成已取消', 'info')
}

// ── Reset editing when segment changes ──
watch(() => sbStore.currentSegmentIndex, () => {
  editingShot.value = false
})
</script>

<template>
  <LoadingOverlay :visible="sbStore.loading && !sbStore.storyboard" message="正在加载分镜..." />

  <div class="sb-root">
    <!-- ═══ Top Bar ═══ -->
    <header class="sb-topbar">
      <div class="sb-topbar-left">
        <button class="sb-back-btn" @click="goBack">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M10 3L5 8L10 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span>返回</span>
        </button>
        <div class="sb-topbar-sep" />
        <div class="sb-topbar-title-area">
          <span class="sb-topbar-ep">第{{ route.params.epId }}集</span>
          <span class="sb-topbar-title">{{ episodeTitle }}</span>
        </div>
      </div>

      <div class="sb-topbar-right">
        <!-- Undo/Redo -->
        <button class="sb-btn sb-btn--ghost" :disabled="!sbStore.canUndo" title="撤销 (Ctrl+Z)" @click="handleUndo">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M4 3.5L1.5 6 4 8.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M1.5 6h7.5a3.5 3.5 0 010 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        </button>
        <button class="sb-btn sb-btn--ghost" :disabled="!sbStore.canRedo" title="重做 (Ctrl+Y)" @click="handleRedo">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M10 3.5L12.5 6 10 8.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M12.5 6H5a3.5 3.5 0 100 7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/></svg>
        </button>
        <div class="sb-topbar-sep" />

        <TopbarActions />
        <div class="sb-topbar-sep" />

        <!-- Model selector -->
        <select v-if="modelOptions.length" v-model="selectedModel" class="sb-model-select">
          <option v-for="opt in modelOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }} · {{ opt.supportsReferences ? '可用参考图' : '普通视频' }}
          </option>
        </select>
        <router-link v-else to="/settings" class="text-[12px] text-purple-500 hover:text-purple-700 underline">
          配置视频模型
        </router-link>

        <select
          v-if="currentModelSupportsAspectRatio"
          v-model="selectedAspectRatio"
          class="sb-model-select sb-model-select--compact"
          title="视频比例"
        >
          <option v-for="opt in aspectRatioOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <select
          v-if="currentModelSupportsSize && generationResolutionOptions.length"
          v-model="selectedGenerationResolution"
          class="sb-model-select sb-model-select--size"
          title="生成尺寸"
        >
          <option v-for="opt in generationResolutionOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <!-- Export -->
        <button class="sb-btn sb-btn--outline" :disabled="exporting" @click="handleExport">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1.5v8M4 6.5l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 11.5h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
          {{ exporting ? '导出中...' : '导出' }}
        </button>

        <!-- Compose -->
        <button
          class="sb-btn sb-btn--primary"
          :disabled="composing || !allSegmentsCompleted"
          :title="!allSegmentsCompleted ? '请先生成所有片段素材' : '合成全集视频'"
          @click="handleCompose"
        >
          <svg v-if="composing" class="animate-spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
            <path d="M7 1.5a5.5 5.5 0 015.1 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <svg v-else width="14" height="14" viewBox="0 0 14 14" fill="none">
            <polygon points="4,2 4,12 11.5,7" fill="currentColor"/>
          </svg>
          {{ composing ? '合成中...' : '合成全集' }}
        </button>

        <!-- Download -->
        <button
          class="sb-btn sb-btn--outline"
          :disabled="downloading || !allSegmentsCompleted"
          :title="!allSegmentsCompleted ? '请先合成全集视频' : '下载视频'"
          @click="handleDownload"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1.5v8M4 6.5l3 3 3-3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M2 11.5h10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
          </svg>
          {{ downloading ? '下载中...' : '下载' }}
        </button>

        <!-- Compose options toggle -->
        <button
          class="sb-btn sb-btn--ghost"
          :class="{ 'sb-btn--active': showComposeOptions }"
          @click="showComposeOptions = !showComposeOptions"
          title="合成选项"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="5.5" stroke="currentColor" stroke-width="1.3"/>
            <path d="M7 4v6M4 7h6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
          选项
        </button>
      </div>
    </header>

    <!-- Compose options panel -->
    <div v-if="showComposeOptions" class="sb-compose-options">
      <div class="sb-options-grid">
        <!-- Quality -->
        <div class="sb-option-group">
          <label class="sb-option-label">视频质量</label>
          <div class="sb-option-tabs">
            <button
              v-for="q in (['high', 'medium', 'low'] as const)"
              :key="q"
              :class="['sb-option-tab', { active: composeQuality === q }]"
              @click="composeQuality = q"
            >{{ { high: '高', medium: '中', low: '低' }[q] }}</button>
          </div>
        </div>

        <!-- Resolution -->
        <div class="sb-option-group">
          <label class="sb-option-label">分辨率</label>
          <select v-model="composeResolution" class="sb-option-select">
            <option value="">默认 (720x1280)</option>
            <option value="1080x1920">1080x1920 (高清)</option>
            <option value="720x1280">720x1280 (标清)</option>
            <option value="540x960">540x960 (流畅)</option>
          </select>
        </div>

        <!-- BGM -->
        <div class="sb-option-group">
          <label class="sb-option-label">背景音乐</label>
          <div class="sb-bgm-row">
            <label class="sb-upload-btn" :class="{ uploading: bgmUploading }">
              <input type="file" accept=".mp3,.wav,.m4a,.aac,.ogg" class="hidden" @change="handleBgmUpload" />
              {{ bgmUploading ? '上传中...' : hasBgm ? '已上传 ✓' : '选择文件' }}
            </label>
            <div v-if="hasBgm" class="sb-bgm-volume">
              <span class="text-[11px] text-gray-400">音量</span>
              <input
                v-model.number="composeBgmVolume"
                type="range"
                min="0"
                max="1"
                step="0.05"
                class="sb-volume-slider"
              />
              <span class="text-[11px] text-gray-500 w-8">{{ Math.round(composeBgmVolume * 100) }}%</span>
            </div>
          </div>
        </div>

        <!-- Subtitle -->
        <div class="sb-option-group">
          <label class="sb-option-label">片头字幕</label>
          <input
            v-model="composeSubtitleText"
            type="text"
            class="sb-option-input"
            placeholder="输入字幕文本（留空不添加）"
          />
          <div v-if="composeSubtitleText" class="sb-subtitle-extra">
            <label class="text-[11px] text-gray-400">字号</label>
            <select v-model.number="composeSubtitleFontSize" class="sb-option-select-sm">
              <option :value="18">18px</option>
              <option :value="24">24px</option>
              <option :value="32">32px</option>
              <option :value="40">40px</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Main 3-col ═══ -->
    <div class="sb-main">
      <!-- LEFT: Asset Panel -->
      <AssetPanel
        :characters="assetsStore.characters"
        :scenes="assetsStore.scenes"
        :selected-character-id="selectedCharacterId"
        :selected-scene-id="selectedSceneId"
        :locked-character-ids="lockedCharacterIds"
        @select-character="handleSelectCharacter"
        @select-scene="handleSelectScene"
        @select-narrator="handleSelectNarrator"
        @add-asset="handleAddAsset"
        @toggle-lock="toggleCharacterLock"
      />

      <div class="sb-workspace">
        <div class="sb-content">
          <!-- CENTER: Script / Editor -->
          <div class="sb-center">
            <template v-if="sbStore.storyboard && sbStore.storyboard.segments.length">
              <!-- Shot Editor (when editing) -->
              <ShotEditor
                v-if="editingShot && sbStore.currentShot"
                :shot="sbStore.currentShot"
                :characters="assetsStore.characters"
                :scenes="assetsStore.scenes"
                @save="handleSaveShot"
                @cancel="handleCancelEdit"
              />
              <!-- Storyboard Script (normal view) -->
              <StoryboardScript
                v-else
                :segment="sbStore.currentSegment"
                :segment-index="sbStore.currentSegmentIndex"
                :generating="generatingSegmentIds.has(sbStore.currentSegment?.id || -1)"
                :adding-shot="addingShot"
                :deleting-shot-id="deletingShotId"
                :locked-character-ids="lockedCharacterIds"
                :characters="assetsStore.characters"
                :scenes="assetsStore.scenes"
                :references-enabled="currentModelSupportsReferences"
                :reference-model-hint="referenceModelHint"
                :saving-script="savingScript"
                :generating-shot-ids="generatingShotIds"
                :selected-shot="sbStore.currentShot"
                @edit-script="handleEditScript"
                @save-script="handleSaveScript"
                @generate-shot="handleGenerateShot"
                @generate-segment="handleGenerateSegment()"
                @regenerate="handleRegenerateSegment"
                @select-shot="handleSelectShot"
                @add-shot="handleAddShot"
                @delete-shot="handleDeleteShot"
                @update-shot-references="handleUpdateShotReferences"
              />
            </template>

            <!-- Loading skeleton -->
            <div v-else-if="sbStore.loading" class="sb-center-inner p-6">
              <div v-for="n in 3" :key="n" class="animate-pulse mb-6">
                <div class="h-5 bg-gray-200 rounded w-24 mb-3" />
                <div class="h-3 bg-gray-100 rounded w-full mb-2" />
                <div class="h-3 bg-gray-100 rounded w-3/4 mb-2" />
                <div class="h-3 bg-gray-100 rounded w-1/2" />
              </div>
            </div>

            <!-- Empty state (no storyboard yet) -->
            <div v-else-if="!sbStore.loading && !sbStore.generatingStoryboard" class="sb-empty">
              <div class="sb-empty-icon">
                <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
                  <rect x="4" y="8" width="48" height="36" rx="6" stroke="#A89870" stroke-width="2.5"/>
                  <polygon points="22,18 22,34 38,26" fill="#A89870"/>
                </svg>
              </div>
              <h3 class="sb-empty-title">尚未生成分镜脚本</h3>
              <p class="sb-empty-desc">AI 将根据剧本和角色场景设定自动拆分镜头</p>
              <button class="sb-btn sb-btn--primary sb-btn--lg" @click="handleGenerateStoryboard">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M2 4l6-3 6 3v8l-6 3-6-3V4z" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>
                  <polygon points="6.5,6 6.5,11 10.5,8.5" fill="currentColor"/>
                </svg>
                生成分镜脚本
              </button>
            </div>

            <!-- Generating storyboard state -->
            <div v-else-if="sbStore.generatingStoryboard" class="sb-empty">
              <h3 class="sb-empty-title">正在生成分镜脚本...</h3>
              <p class="sb-empty-desc">{{ storyboardGenerationStatus.message || 'AI 正在分析剧本并拆分镜头，请稍候' }}</p>

              <!-- Enhanced progress bar -->
              <div class="sb-storyboard-progress">
                <div class="sb-storyboard-progress-head">
                  <span>分镜生成进度</span>
                  <strong>{{ storyboardGenerationStatus.progress || 1 }}%</strong>
                </div>
                <div class="sb-storyboard-progress-track">
                  <span
                    class="sb-progress-fill"
                    :style="{ width: `${storyboardGenerationStatus.progress || 1}%` }"
                  />
                </div>
              </div>

              <!-- Cancel button -->
              <button class="sb-btn sb-btn--outline sb-btn--sm mt-3" @click="handleCancelStoryboard">
                取消生成
              </button>
            </div>
          </div>

          <!-- RIGHT: Preview Panel -->
          <PreviewPanel
            :shot="sbStore.currentShot"
            :segment="sbStore.currentSegment"
            :target="sbStore.previewTarget"
            @download="handlePreviewDownload"
          />
        </div>

        <!-- ═══ Bottom Timeline ═══ -->
        <Timeline
          v-if="sbStore.storyboard && sbStore.storyboard.segments.length"
          :segments="sbStore.storyboard.segments"
          :current-index="sbStore.currentSegmentIndex"
          :total-duration="totalDuration"
          @select="sbStore.selectSegment"
        />
      </div>
    </div>

    <!-- ═══ Toast ═══ -->
    <Transition name="toast">
      <div v-if="toastMessage" class="sb-toast" :class="'sb-toast--' + toastType">
        <span>{{ toastMessage }}</span>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* ═══ Root Layout ═══ */
.sb-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FDF5D6;
  overflow: hidden;
  position: relative;
}

/* ═══ Top Bar ═══ */
.sb-topbar {
  height: 52px;
  border-bottom: 1px solid #FDF4D8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  background: #FDF5D6;
  z-index: 10;
}

.sb-topbar-left {
  display: flex;
  align-items: center;
  gap: 0;
}

.sb-back-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #666;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 2px;
  transition: all 0.15s;
  font-weight: 500;
}
.sb-back-btn:hover { color: #333; background: #FDF4D8; }

.sb-topbar-sep {
  width: 1px;
  height: 22px;
  background: #D4C898;
  margin: 0 14px;
}

.sb-topbar-title-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sb-topbar-ep {
  font-size: 13px;
  font-weight: 600;
  color: #E8A317;
  background: rgba(232, 163, 23, 0.08);
  padding: 2px 10px;
  border-radius: 2px;
}

.sb-topbar-title {
  font-size: 14px;
  font-weight: 600;
  color: #2D2515;
}

.sb-topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.sb-model-select {
  height: 34px;
  font-size: 13px;
  border: 1px solid #D4C898;
  border-radius: 9px;
  padding: 0 12px;
  background: #FDF5D6;
  outline: none;
  color: #555;
  cursor: pointer;
  font-weight: 500;
  transition: border-color 0.15s;
}
.sb-model-select:hover { border-color: #A89870; }
.sb-model-select:focus { border-color: #E8A317; }

.sb-model-select--compact {
  width: 104px;
  padding: 0 8px;
}

.sb-model-select--size {
  width: 148px;
  padding: 0 8px;
}

/* ── Topbar buttons ── */
.sb-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
  white-space: nowrap;
}
.sb-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sb-btn--sm {
  height: 30px;
  padding: 0 12px;
  font-size: 12px;
  border-radius: 7px;
}

.sb-btn--outline {
  background: #FDF5D6;
  color: #555;
  border: 1px solid #D4C898;
}
.sb-btn--outline:hover:not(:disabled) {
  background: #FEF9E7;
  border-color: #A89870;
  color: #333;
}

.sb-btn--primary {
  background: #2D2515;
  color: #FFFFFF;
}
.sb-btn--primary:hover:not(:disabled) {
  background: #333;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.sb-btn--lg {
  height: 42px;
  padding: 0 24px;
  font-size: 14px;
  border-radius: 2px;
}

/* ═══ Main 3-col ═══ */
.sb-main {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-height: 0;
}

.sb-workspace {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f3f4f6;
}

.sb-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.sb-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}

.sb-center > :deep(*) {
  min-height: 0;
}

/* ═══ Empty State ═══ */
.sb-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  background: #FEF9E7;
}

.sb-empty-icon { margin-bottom: 4px; }

.sb-empty-title {
  font-size: 17px;
  font-weight: 700;
  color: #555;
  margin: 0;
}

.sb-empty-desc {
  font-size: 14px;
  color: #aaa;
  margin: 0 0 8px;
}

.sb-storyboard-progress {
  width: min(420px, 78%);
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.sb-storyboard-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #7b5a12;
  font-size: 12px;
  font-weight: 700;
}

.sb-storyboard-progress-head span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sb-storyboard-progress-head strong {
  color: #2D2515;
  font-variant-numeric: tabular-nums;
}

.sb-storyboard-progress-track {
  height: 8px;
  overflow: hidden;
  border-radius: 2px;
  background: rgba(168, 130, 60, 0.24);
  border: 1px solid rgba(168, 130, 60, 0.12);
}

/* ═══ 进度条增强 ═══ */
.sb-progress-fill {
  display: block;
  height: 100%;
  min-width: 8px;
  border-radius: inherit;
  background: linear-gradient(90deg, #E8A317 0%, #F5C34B 40%, #2D2515 100%);
  transition: width 0.35s ease;
  position: relative;
  overflow: hidden;
}

/* 光泽扫过 */
.sb-progress-fill::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.35) 30%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.35) 70%,
    transparent 100%
  );
  animation: sb-shimmer 1.8s ease-in-out infinite;
}

@keyframes sb-shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}

/* ═══ Toast ═══ */
.sb-toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  border-radius: 2px;
  font-size: 13px;
  font-weight: 500;
  z-index: 100;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  pointer-events: none;
}
.sb-toast--success { background: #2D2515; color: #FFFFFF; }
.sb-toast--error   { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
.sb-toast--info    { background: rgba(232, 163, 23, 0.08); color: #C88A0C; border: 1px solid #D4C898; }

.toast-enter-active { transition: all 0.3s ease; }
.toast-leave-active { transition: all 0.3s ease; }
.toast-enter-from { opacity: 0; transform: translateX(-50%) translateY(10px); }
.toast-leave-to   { opacity: 0; transform: translateX(-50%) translateY(10px); }

/* ═══ Compose Options Panel ═══ */
.sb-compose-options {
  padding: 14px 20px;
  background: #FEF9E7;
  border-bottom: 1px solid #FDF4D8;
  display: flex;
  flex-shrink: 0;
}

.sb-options-grid {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.sb-option-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 120px;
}

.sb-option-label {
  font-size: 11px;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sb-option-tabs {
  display: flex;
  gap: 2px;
  background: #eee;
  border-radius: 7px;
  padding: 2px;
}

.sb-option-tab {
  padding: 4px 12px;
  border: none;
  background: none;
  font-size: 12px;
  font-weight: 500;
  color: #777;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.15s;
}
.sb-option-tab.active {
  background: #FDF5D6;
  color: #333;
  box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}

.sb-option-select {
  height: 30px;
  font-size: 12px;
  border: 1px solid #D4C898;
  border-radius: 7px;
  padding: 0 8px;
  background: #FDF5D6;
  color: #555;
  outline: none;
}
.sb-option-select-sm {
  height: 26px;
  font-size: 11px;
  border: 1px solid #D4C898;
  border-radius: 2px;
  padding: 0 6px;
  background: #FDF5D6;
  color: #555;
}

.sb-option-input {
  height: 30px;
  font-size: 12px;
  border: 1px solid #D4C898;
  border-radius: 7px;
  padding: 0 10px;
  background: #FDF5D6;
  color: #333;
  outline: none;
  width: 200px;
}
.sb-option-input:focus { border-color: #E8A317; }

.sb-bgm-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.sb-upload-btn {
  display: inline-flex;
  align-items: center;
  height: 30px;
  padding: 0 12px;
  font-size: 12px;
  border: 1px dashed #A89870;
  border-radius: 7px;
  cursor: pointer;
  color: #777;
  transition: all 0.15s;
}
.sb-upload-btn:hover { border-color: #E8A317; color: #E8A317; }
.sb-upload-btn.uploading { opacity: 0.5; pointer-events: none; }

.sb-bgm-volume {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sb-volume-slider {
  width: 60px;
  height: 4px;
  cursor: pointer;
}

.sb-subtitle-extra {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

/* ── Ghost button for options toggle ── */
.sb-btn--ghost {
  background: none;
  color: #888;
  border: none;
}
.sb-btn--ghost:hover { color: #555; background: #FDF4D8; }
.sb-btn--ghost.sb-btn--active { color: #E8A317; background: rgba(232, 163, 23, 0.08); }

.hidden { display: none; }
</style>
