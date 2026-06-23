import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { storyboardApi } from '@/api/storyboard'
import type { StoryboardDetail, ShotDetail } from '@/types/shot'
import type { SegmentDetail } from '@/types/segment'

const MAX_HISTORY = 50

export const useStoryboardStore = defineStore('storyboard', () => {
  const storyboard = ref<StoryboardDetail | null>(null)
  const currentSegmentIndex = ref(0)
  const currentShotIndex = ref(0)
  const previewTarget = ref<'segment' | 'shot'>('shot')
  const loading = ref(false)
  const generatingStoryboard = ref(false)

  // ── Undo/Redo (P2-5) ──
  const undoStack = ref<Partial<ShotDetail>[]>([])
  const redoStack = ref<Partial<ShotDetail>[]>([])

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  const currentSegment = computed<SegmentDetail | null>(() => {
    if (!storyboard.value) return null
    return storyboard.value.segments[currentSegmentIndex.value] || null
  })

  const currentShot = computed<ShotDetail | null>(() => {
    if (!currentSegment.value) return null
    return currentSegment.value.shots[currentShotIndex.value] || null
  })

  async function fetchStoryboard(projectId: number, episodeId: number) {
    loading.value = true
    try {
      const prevSegmentIndex = currentSegmentIndex.value
      const prevShotIndex = currentShotIndex.value
      const { data } = await storyboardApi.get(projectId, episodeId)
      storyboard.value = data
      // Restore segment index within valid bounds
      const maxIndex = Math.max(0, (data.segments?.length || 1) - 1)
      currentSegmentIndex.value = Math.min(prevSegmentIndex, maxIndex)
      const currentShots = data.segments?.[currentSegmentIndex.value]?.shots || []
      const maxShotIndex = Math.max(0, currentShots.length - 1)
      currentShotIndex.value = Math.min(prevShotIndex, maxShotIndex)
      undoStack.value = []
      redoStack.value = []
    } finally {
      loading.value = false
    }
  }

  async function generateStoryboard(projectId: number, episodeId: number) {
    generatingStoryboard.value = true
    try {
      await storyboardApi.generate(projectId, episodeId)
      // API now returns immediately; polling will pick up the result
    } catch (e: any) {
      generatingStoryboard.value = false
      throw e
    }
  }

  function onStoryboardGenerated() {
    generatingStoryboard.value = false
  }

  function selectSegment(index: number) {
    currentSegmentIndex.value = index
    currentShotIndex.value = 0
    previewTarget.value = 'segment'
  }

  function selectShot(index: number) {
    currentShotIndex.value = index
    previewTarget.value = 'shot'
  }

  // ── Undo/Redo actions (P2-5) ──
  function pushUndo(snapshot: Partial<ShotDetail>) {
    undoStack.value.push(snapshot)
    if (undoStack.value.length > MAX_HISTORY) undoStack.value.shift()
    redoStack.value = [] // Clear redo on new action
  }

  async function undo(projectId: number, episodeId: number) {
    if (!canUndo.value || !currentShot.value) return
    const prev = undoStack.value.pop()!
    // Save current state to redo
    redoStack.value.push({
      camera_type: currentShot.value.camera_type,
      camera_angle: currentShot.value.camera_angle,
      camera_movement: currentShot.value.camera_movement,
      transition: currentShot.value.transition,
      time_of_day: currentShot.value.time_of_day,
      duration: currentShot.value.duration,
      dialogue: currentShot.value.dialogue,
      emotion: currentShot.value.emotion,
      narration: currentShot.value.narration,
      scene_ref: currentShot.value.scene_ref,
      background: currentShot.value.background,
      visual_references: currentShot.value.visual_references,
    })
    // Restore previous state
    await storyboardApi.updateShot(projectId, episodeId, currentShot.value.id, prev as any)
    await fetchStoryboard(projectId, episodeId)
  }

  async function redo(projectId: number, episodeId: number) {
    if (!canRedo.value || !currentShot.value) return
    const next = redoStack.value.pop()!
    // Save current to undo
    undoStack.value.push({
      camera_type: currentShot.value.camera_type,
      camera_angle: currentShot.value.camera_angle,
      camera_movement: currentShot.value.camera_movement,
      transition: currentShot.value.transition,
      time_of_day: currentShot.value.time_of_day,
      duration: currentShot.value.duration,
      dialogue: currentShot.value.dialogue,
      emotion: currentShot.value.emotion,
      narration: currentShot.value.narration,
      scene_ref: currentShot.value.scene_ref,
      background: currentShot.value.background,
      visual_references: currentShot.value.visual_references,
    })
    // Apply redo state
    await storyboardApi.updateShot(projectId, episodeId, currentShot.value.id, next as any)
    await fetchStoryboard(projectId, episodeId)
  }

  return {
    storyboard,
    currentSegmentIndex,
    currentShotIndex,
    previewTarget,
    currentSegment,
    currentShot,
    loading,
    generatingStoryboard,
    undoStack,
    redoStack,
    canUndo,
    canRedo,
    fetchStoryboard,
    generateStoryboard,
    onStoryboardGenerated,
    selectSegment,
    selectShot,
    pushUndo,
    undo,
    redo,
  }
})
