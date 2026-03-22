<template>
  <div class="fd-page">
    <PageHeader title="系统参数管理" description="统一管理检测参数、报警策略与硬件配置，支持导入导出、版本回滚与审计追踪。">
      <template #actions>
        <ActionBar>
          <el-button plain :loading="loading" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button plain @click="handleReload">
            <el-icon><RefreshRight /></el-icon>
            热加载
          </el-button>
          <el-button plain @click="handleExport">
            <el-icon><Download /></el-icon>
            导出配置
          </el-button>
          <el-upload :show-file-list="false" :before-upload="handleImport" accept=".json">
            <el-button type="primary">
              <el-icon><Upload /></el-icon>
              导入配置
            </el-button>
          </el-upload>
        </ActionBar>
      </template>
    </PageHeader>

    <FilterBar>
      <el-form inline class="filter-form">
        <el-form-item label="参数分类">
          <el-select v-model="selectedCategory" placeholder="全部分类" clearable @change="loadParams">
            <el-option label="YOLO 检测" value="yolo_detection" />
            <el-option label="报警逻辑" value="alarm_logic" />
            <el-option label="硬件配置" value="hardware" />
            <el-option label="通用配置" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="searchKeyword" placeholder="按 key 或描述筛选" clearable />
        </el-form-item>
      </el-form>
    </FilterBar>

    <DataCard>
      <el-tabs v-model="activeTab" class="system-tabs">
        <el-tab-pane label="参数列表" name="params">
          <el-table v-loading="loading" :data="filteredParams" stripe>
            <el-table-column prop="key" label="参数键" min-width="220" />
            <el-table-column prop="description" label="描述" min-width="260" />
            <el-table-column label="分类" width="140">
              <template #default="{ row }">
                <StatusTag mode="category" :value="row.category" />
              </template>
            </el-table-column>
            <el-table-column label="当前值" min-width="180">
              <template #default="{ row }">
                <StatusTag v-if="row.type === 'boolean'" mode="boolean" :value="row.value" />
                <span v-else class="fd-mono">{{ formatValue(row.value) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="110" />
            <el-table-column label="权限" width="120">
              <template #default="{ row }">
                <StatusTag mode="permission" :value="row.permission" />
              </template>
            </el-table-column>
            <el-table-column label="重启生效" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.requires_restart ? 'warning' : 'info'">{{ row.requires_restart ? '是' : '否' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" :disabled="row.permission === 'read_only'" @click="handleEdit(row)">编辑</el-button>
                <el-button size="small" plain @click="showVersions(row)">历史</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <EmptyState title="暂无参数数据" description="请检查分类筛选或刷新后重试。" />
            </template>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="审计日志" name="audit">
          <el-table v-loading="auditLoading" :data="auditLogs" stripe>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <StatusTag mode="action" :value="row.action" />
              </template>
            </el-table-column>
            <el-table-column prop="param_key" label="参数键" width="220" />
            <el-table-column label="变更内容" min-width="260">
              <template #default="{ row }">
                <span v-if="row.old_value !== undefined && row.new_value !== undefined">
                  {{ formatValue(row.old_value) }} → {{ formatValue(row.new_value) }}
                </span>
                <span v-else class="fd-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="140" />
            <el-table-column prop="ip_address" label="IP 地址" width="160" />
            <el-table-column prop="timestamp" label="时间" width="190" />
            <template #empty>
              <EmptyState title="暂无审计日志" description="发生参数变更后会自动记录。" />
            </template>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </DataCard>

    <el-dialog v-model="editDialogVisible" title="编辑参数" width="560px">
      <el-form :model="editForm" label-width="120px" class="edit-form">
        <el-form-item label="参数键">
          <span class="fd-mono">{{ editingParam?.key }}</span>
        </el-form-item>
        <el-form-item label="参数描述">
          <span>{{ editingParam?.description }}</span>
        </el-form-item>
        <el-form-item label="参数值">
          <el-switch v-if="editingParam?.type === 'boolean'" v-model="editForm.value" />
          <el-select
            v-else-if="editingParam?.options && editingParam.options.length > 0"
            v-model="editForm.value"
            style="width: 100%"
          >
            <el-option v-for="opt in editingParam.options" :key="String(opt)" :label="String(opt)" :value="opt" />
          </el-select>
          <el-input-number
            v-else-if="editingParam?.type === 'integer'"
            v-model="editForm.value"
            :min="editingParam.min_value"
            :max="editingParam.max_value"
            controls-position="right"
            style="width: 100%"
          />
          <el-input-number
            v-else-if="editingParam?.type === 'float'"
            v-model="editForm.value"
            :min="editingParam.min_value"
            :max="editingParam.max_value"
            :precision="2"
            :step="0.01"
            controls-position="right"
            style="width: 100%"
          />
          <el-input v-else v-model="editForm.value" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="修改原因">
          <el-input v-model="editForm.change_reason" type="textarea" :rows="2" placeholder="可选：记录本次修改目的" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="editForm.operator" placeholder="可选：填写操作人标识" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionsDialogVisible" title="参数历史版本" width="760px">
      <el-table v-loading="versionsLoading" :data="paramVersions" stripe>
        <el-table-column prop="changed_at" label="时间" width="190" />
        <el-table-column label="变更内容" min-width="250">
          <template #default="{ row }">
            {{ formatValue(row.old_value) }} → {{ formatValue(row.new_value) }}
          </template>
        </el-table-column>
        <el-table-column prop="changed_by" label="操作人" width="130" />
        <el-table-column prop="change_reason" label="变更原因" min-width="170" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button size="small" type="danger" plain @click="handleRollback(row)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Refresh, RefreshRight, Upload } from '@element-plus/icons-vue'
import type { UploadRawFile } from 'element-plus'
import {
  exportConfig,
  getAuditLogs,
  getParamVersions,
  getSystemParams,
  importConfig,
  reloadConfig,
  rollbackParam,
  updateSystemParams
} from '@/api/system'
import type { ParamAuditLog, ParamVersion, SystemConfigUpdate, SystemParam } from '@/types'
import ActionBar from '@/components/layout/ActionBar.vue'
import DataCard from '@/components/layout/DataCard.vue'
import FilterBar from '@/components/layout/FilterBar.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'

const loading = ref(false)
const auditLoading = ref(false)
const saving = ref(false)
const versionsLoading = ref(false)
const activeTab = ref('params')
const selectedCategory = ref<string>()
const searchKeyword = ref('')
const allParams = ref<SystemParam[]>([])
const auditLogs = ref<ParamAuditLog[]>([])
const paramVersions = ref<ParamVersion[]>([])

const editDialogVisible = ref(false)
const versionsDialogVisible = ref(false)
const editingParam = ref<SystemParam | null>(null)
const editForm = ref({
  value: null as any,
  change_reason: '',
  operator: ''
})

const filteredParams = computed(() => {
  let list = allParams.value
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.trim().toLowerCase()
    list = list.filter((p) => p.key.toLowerCase().includes(keyword) || p.description.toLowerCase().includes(keyword))
  }
  return list
})

const loadParams = async () => {
  loading.value = true
  try {
    const res = await getSystemParams(selectedCategory.value as any)
    allParams.value = res.data.params
  } finally {
    loading.value = false
  }
}

const loadAuditLogs = async () => {
  auditLoading.value = true
  try {
    const res = await getAuditLogs(100)
    auditLogs.value = res.data
  } finally {
    auditLoading.value = false
  }
}

const handleRefresh = async () => {
  await loadParams()
  if (activeTab.value === 'audit') {
    await loadAuditLogs()
  }
}

const handleEdit = (row: SystemParam) => {
  editingParam.value = row
  editForm.value = {
    value: row.value,
    change_reason: '',
    operator: ''
  }
  editDialogVisible.value = true
}

const handleSave = async () => {
  if (!editingParam.value) return
  saving.value = true
  try {
    const payload: SystemConfigUpdate = {
      updates: { [editingParam.value.key]: editForm.value.value },
      change_reason: editForm.value.change_reason || undefined,
      operator: editForm.value.operator || undefined
    }
    await updateSystemParams(payload)
    ElMessage.success('参数更新成功')
    editDialogVisible.value = false
    await handleRefresh()
  } finally {
    saving.value = false
  }
}

const showVersions = async (row: SystemParam) => {
  editingParam.value = row
  versionsDialogVisible.value = true
  versionsLoading.value = true
  try {
    const res = await getParamVersions(row.key, 20)
    paramVersions.value = res.data
  } finally {
    versionsLoading.value = false
  }
}

const handleRollback = async (version: ParamVersion) => {
  try {
    await ElMessageBox.confirm('确定回滚到该版本吗？', '回滚确认', { type: 'warning' })
    await rollbackParam(version.param_key, version.version_id)
    ElMessage.success('参数回滚成功')
    versionsDialogVisible.value = false
    await handleRefresh()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('参数回滚失败')
    }
  }
}

const handleExport = async () => {
  const res = await exportConfig()
  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `system-config-${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('配置导出成功')
}

const handleImport = async (file: UploadRawFile) => {
  try {
    await ElMessageBox.confirm('导入会覆盖当前配置，确定继续吗？', '导入确认', { type: 'warning' })
    await importConfig(file)
    ElMessage.success('配置导入成功')
    await handleRefresh()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('配置导入失败')
    }
  }
  return false
}

const handleReload = async () => {
  await reloadConfig()
  ElMessage.success('配置热加载成功')
  await loadParams()
}

const formatValue = (value: unknown) => {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

watch(activeTab, (tab) => {
  if (tab === 'audit' && auditLogs.value.length === 0) {
    loadAuditLogs()
  }
})

onMounted(async () => {
  await loadParams()
  await loadAuditLogs()
})
</script>

<style scoped>
.filter-form {
  row-gap: 6px;
}

.system-tabs {
  margin-top: -4px;
}

.edit-form :deep(.el-input-number),
.edit-form :deep(.el-input),
.edit-form :deep(.el-textarea) {
  width: 100%;
}
</style>
