<template>
  <el-tag :type="resolved.type" :effect="effect">{{ resolved.label }}</el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Mode = 'category' | 'permission' | 'action' | 'log-level' | 'boolean'
type TagType = '' | 'primary' | 'success' | 'warning' | 'danger' | 'info'

const props = withDefaults(
  defineProps<{
    mode: Mode
    value: string | number | boolean
    effect?: 'light' | 'dark' | 'plain'
  }>(),
  {
    effect: 'light'
  }
)

const maps: Record<Mode, Record<string, { label: string; type: TagType }>> = {
  category: {
    yolo_detection: { label: 'YOLO 检测', type: 'primary' },
    alarm_logic: { label: '报警逻辑', type: 'success' },
    hardware: { label: '硬件配置', type: 'warning' },
    general: { label: '通用配置', type: 'info' }
  },
  permission: {
    read_only: { label: '只读', type: 'info' },
    editable: { label: '可编辑', type: 'success' },
    restricted: { label: '受限', type: 'warning' }
  },
  action: {
    create: { label: '创建', type: 'success' },
    update: { label: '更新', type: 'primary' },
    delete: { label: '删除', type: 'danger' },
    import: { label: '导入', type: 'warning' },
    export: { label: '导出', type: 'info' },
    rollback: { label: '回滚', type: 'warning' }
  },
  'log-level': {
    DEBUG: { label: 'DEBUG', type: 'info' },
    INFO: { label: 'INFO', type: 'success' },
    WARNING: { label: 'WARNING', type: 'warning' },
    ERROR: { label: 'ERROR', type: 'danger' },
    CRITICAL: { label: 'CRITICAL', type: 'danger' }
  },
  boolean: {
    true: { label: '是', type: 'success' },
    false: { label: '否', type: 'info' }
  }
}

const resolved = computed(() => {
  const key = String(props.value)
  return maps[props.mode][key] || { label: key, type: 'info' as TagType }
})
</script>
