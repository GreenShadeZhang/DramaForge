<script setup lang="ts">
import { computed } from 'vue'
import type { SegmentDetail } from '@/types/segment'
import { SegmentStatus, SegmentStatusLabel } from '@/types/enums'

const props = defineProps<{
  segment: SegmentDetail
  index: number
  active: boolean
}>()

const thumbUrl = computed(() =>
  props.segment.thumbnail_url || props.segment.shots?.find(shot => shot.image_url)?.image_url || ''
)

const durationLabel = computed(() => {
  const duration = props.segment.duration
  if (!duration) return '--'
  return `${Math.round(duration)}s`
})

const shotCountLabel = computed(() => `${props.segment.shots?.length || 0} 分镜`)
const statusLabel = computed(() => SegmentStatusLabel[props.segment.status] || props.segment.status)

const statusDot: Record<string, string> = {
  [SegmentStatus.PENDING]: 'dot-muted',
  [SegmentStatus.GENERATING]: 'dot-active',
  [SegmentStatus.COMPLETED]: 'dot-done',
  [SegmentStatus.FAILED]: 'dot-error',
}
</script>

<template>
  <button
    class="timeline-item"
    :class="{ active }"
    type="button"
    :aria-label="`选择片段 ${index + 1}`"
  >
    <span class="timeline-thumb">
      <img v-if="thumbUrl" :src="thumbUrl" alt="" loading="lazy" />
      <span v-else class="timeline-fallback">片段 {{ String(index + 1).padStart(2, '0') }}</span>

      <span class="timeline-index">{{ String(index + 1).padStart(2, '0') }}</span>
      <span class="timeline-duration">{{ durationLabel }}</span>
      <span
        class="timeline-status-dot"
        :class="statusDot[segment.status] || 'dot-muted'"
        :title="statusLabel"
      />
    </span>

    <span class="timeline-label">
      <span class="timeline-name">片段 {{ String(index + 1).padStart(2, '0') }}</span>
      <span class="timeline-meta">{{ shotCountLabel }}</span>
    </span>
  </button>
</template>

<style scoped>
.timeline-item {
  width: 118px;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 5px;
  border: 1px solid rgba(168, 130, 60, 0.22);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.48);
  color: inherit;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.timeline-item:hover {
  background: #fffaf0;
  border-color: rgba(168, 130, 60, 0.72);
  transform: translateY(-1px);
}

.timeline-item.active {
  background: #fff7db;
  border-color: #2d2515;
  box-shadow: 0 0 0 1px rgba(45, 37, 21, 0.1), 0 10px 22px rgba(72, 42, 10, 0.14);
}

.timeline-thumb {
  position: relative;
  height: 56px;
  display: block;
  overflow: hidden;
  border-radius: 6px;
  background: #f2ead8;
  box-shadow: inset 0 0 0 1px rgba(93, 52, 12, 0.08);
}

.timeline-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.timeline-thumb::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(20, 14, 8, 0.1), rgba(20, 14, 8, 0.42));
  pointer-events: none;
}

.timeline-fallback {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b49b64;
  font-size: 11px;
  font-weight: 700;
}

.timeline-index {
  position: absolute;
  top: 5px;
  left: 5px;
  min-width: 20px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  background: rgba(45, 37, 21, 0.86);
  color: #fff7db;
  font-size: 10px;
  font-weight: 800;
  z-index: 1;
}

.timeline-duration {
  position: absolute;
  right: 6px;
  bottom: 6px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  padding: 0 6px;
  border-radius: 4px;
  background: rgba(255, 247, 219, 0.9);
  color: #2d2515;
  font-size: 10px;
  font-weight: 800;
  z-index: 1;
}

.timeline-status-dot {
  position: absolute;
  top: 7px;
  right: 7px;
  width: 8px;
  height: 8px;
  border: 1px solid #fff;
  border-radius: 50%;
  z-index: 1;
}

.dot-muted {
  background: #b49b64;
}

.dot-active {
  background: #E8A317;
  animation: pulse 1.1s ease-in-out infinite;
}

.dot-done {
  background: #22c55e;
}

.dot-error {
  background: #ef4444;
}

.timeline-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: #6f5c38;
  font-size: 11px;
  line-height: 1.2;
}

.timeline-name {
  min-width: 0;
  display: flex;
  align-items: center;
  white-space: nowrap;
  color: #2d2515;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-meta {
  color: #8c7247;
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-item.active .timeline-label {
  color: #2d2515;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.35);
    opacity: 0.7;
  }
}
</style>
