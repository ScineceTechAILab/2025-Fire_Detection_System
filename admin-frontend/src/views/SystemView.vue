<template>
  <div class="system-view">
    <el-card class="header-card">
      <div class="header-content">
        <h2>系统参数管理</h2>
        <div class="header-actions">
          <el-button size="small" plain :loading="loading" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button size="small" plain @click="handleReload">
            <el-icon><RefreshRight /></el-icon>
            热加载
          </el-button>
          <el-button size="small" plain @click="handleExport">
            <el-icon><Download /></el-icon>
            导出配置
          </el-button>
          <el-upload
            :show-file-list="false"
            :before-upload="handleImport"
            accept=".json"
          >
            <el-button size="small" type="primary">
              <el-icon><Upload /></el-icon>
              导入配置
            </el-button>
          </el-upload>
        </div>
      </div>
    </el-card>

    <el-card class="filter-card">
      <el-form inline>
        <el-form-item label="参数分类">
          <el-select v-model="selectedCategory" placeholder="全部" clearable @change="loadParams">
            <el-option label="YOLO 检测" value="yolo_detection" />
            <el-option label="报警逻辑" value="alarm_logic" />
            <el-option label="硬件配置" value="hardware" />
            <el-option label="通用配置" value="general" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="searchKeyword" placeholder="搜索参数" clearable @input="debounceLoad" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="params-card">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="参数列表" name="list">
          <el-table v-loading="loading" :data="filteredParams" stripe style="width: 100%">
            <el-table-column prop="key" label="参数名" width="200" />
            <el-table-column prop="description" label="描述" min-width="200" />
            <el-table-column prop="category" label="分类" width="120">
              <template #default="{ row }">
                <el-tag :type="getCategoryTagType(row.category)">{{ getCategoryLabel(row.category) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="当前值" min-width="150">
              <template #default="{ row }">
                <el-tag v-if="row.type === 'boolean'" :type="row.value ? 'success' : 'info'">
                  {{ row.value ? '是' : '否' }}
                </el-tag>
                <span v-else>{{ formatValue(row.value) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column label="权限" width="100">
              <template #default="{ row }">
                <el-tag :type="getPermissionTagType(row.permission)">
                  {{ getPermissionLabel(row.permission) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="需重启" width="80" align="center">
              <template #default="{ row }">
                <el-icon v-if="row.requires_restart" color="#f56c6c"><Warning /></el-icon>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button
                  size="small"
                  :disabled="row.permission === 'read_only'"
                  @click="handleEdit(row)"
                >
                  编辑
                </el-button>
                <el-button size="small" @click="showVersions(row)">历史</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="审计日志" name="audit">
          <el-table v-loading="auditLoading" :data="auditLogs" stripe style="width: 100%">
            <el-table-column prop="action" label="操作" width="100">
              <template #default="{ row }">
                <el-tag :type="getActionTagType(row.action)">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="param_key" label="参数" width="200" />
            <el-table-column label="变更" min-width="200">
              <template #default="{ row }">
                <span v-if="row.old_value !== undefined && row.new_value !== undefined">
                  {{ formatValue(row.old_value) }} → {{ formatValue(row.new_value) }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="120" />
            <el-table-column prop="ip_address" label="IP地址" width="140" />
            <el-table-column prop="timestamp" label="时间" width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="editDialogVisible" title="编辑参数" width="500px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="参数名">
          <span>{{ editingParam?.key }}</span>
        </el-form-item>
        <el-form-item label="描述">
          <span>{{ editingParam?.description }}</span>
        </el-form-item>
        <el-form-item label="参数值">
          <el-switch
            v-if="editingParam?.type === 'boolean'"
            v-model="editForm.value"
          />
          <el-select
            v-else-if="editingParam?.options && editingParam.options.length > 0"
            v-model="editForm.value"
            style="width: 100%"
          >
            <el-option
              v-for="opt in editingParam.options"
              :key="opt"
              :label="String(opt)"
              :value="opt"
            />
          </el-select>
          <el-input-number
            v-else-if="editingParam?.type === 'integer'"
            v-model="editForm.value"
            :min="editingParam.min_value"
            :max="editingParam.max_value"
            style="width: 100%"
          />
          <el-input-number
            v-else-if="editingParam?.type === 'float'"
            v-model="editForm.value"
            :min="editingParam.min_value"
            :max="editingParam.max_value"
            :step="0.01"
            :precision="2"
            style="width: 100%"
          />
          <el-input
            v-else
            v-model="editForm.value"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
        <el-form-item label="修改原因">
          <el-input v-model="editForm.change_reason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="editForm.operator" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionsDialogVisible" title="历史版本" width="700px">
      <el-table v-loading="versionsLoading" :data="paramVersions" stripe style="width: 100%">
        <el-table-column prop="changed_at" label="时间" width="180" />
        <el-table-column label="变更" min-width="200">
          <template #default="{ row }">
            {{ formatValue(row.old_value) }} → {{ formatValue(row.new_value) }}
          </template>
        </el-table-column>
        <el-table-column prop="changed_by" label="操作人" width="120" />
        <el-table-column prop="change_reason" label="原因" min-width="150" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="handleRollback(row)">回滚</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, Upload, RefreshRight, Warning } from '@element-plus/icons-vue'
import {
  getSystemParams,
  updateSystemParams,
  getParamVersions,
  rollbackParam,
  getAuditLogs,
  exportConfig,
  importConfig,
  reloadConfig
} from '@/api/system'
import type { SystemParam, ParamVersion, ParamAuditLog, SystemConfigUpdate } from '@/types'

const loading = ref(false)
const auditLoading = ref(false)
const saving = ref(false)
const versionsLoading = ref(false)
const activeTab = ref('list')
const selectedCategory = ref<string>()
const searchKeyword = ref('')
const allParams = ref<SystemParam[]>([])
const auditLogs = ref<ParamAuditLog[]>([])
const paramVersions = ref<ParamVersion[]>([])

const editDialogVisible = ref(false)
const versionsDialogVisible = ref(false)
const editingParam = ref<SystemParam | null>(null)
const editForm = ref({
  value: null,
  change_reason: '',
  operator: ''
})

let debounceTimer: ReturnType<typeof setTimeout> | null = null

const filteredParams = computed(() => {
  let result = allParams.value
  if (selectedCategory.value) {
    result = result.filter(p => p.category === selectedCategory.value)
  }
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(p =>
      p.key.toLowerCase().includes(keyword) ||
      p.description.toLowerCase().includes(keyword)
    )
  }
  return result
})

const loadParams = async () => {
  loading.value = true
  try {
    const res = await getSystemParams(selectedCategory.value as any)
    allParams.value = res.data.params
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadAuditLogs = async () => {
  auditLoading.value = true
  try {
    const res = await getAuditLogs(100)
    auditLogs.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    auditLoading.value = false
  }
}

const debounceLoad = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    loadParams()
  }, 300)
}

const handleRefresh = () => {
  loadParams()
  if (activeTab.value === 'audit') {
    loadAuditLogs()
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
    const update: SystemConfigUpdate = {
      updates: { [editingParam.value.key]: editForm.value.value },
      change_reason: editForm.value.change_reason || undefined,
      operator: editForm.value.operator || undefined
    }
    await updateSystemParams(update)
    ElMessage.success('参数更新成功')
    editDialogVisible.value = false
    loadParams()
    loadAuditLogs()
  } catch (e) {
    console.error(e)
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
  } catch (e) {
    console.error(e)
  } finally {
    versionsLoading.value = false
  }
}

const handleRollback = async (version: ParamVersion) => {
  try {
    await ElMessageBox.confirm('确定要回滚到此版本吗？', '确认', { type: 'warning' })
    await rollbackParam(version.param_key, version.version_id)
    ElMessage.success('回滚成功')
    versionsDialogVisible.value = false
    loadParams()
    loadAuditLogs()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
}

const handleExport = async () => {
  try {
    const res = await exportConfig()
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `system-config-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    console.error(e)
  }
}

const handleImport = async (file: File) => {
  try {
    await ElMessageBox.confirm('导入配置将覆盖当前配置，确定继续吗？', '确认', { type: 'warning' })
    await importConfig(file)
    ElMessage.success('导入成功')
    loadParams()
    loadAuditLogs()
  } catch (e) {
    if (e !== 'cancel') console.error(e)
  }
  return false
}

const handleReload = async () => {
  try {
    await reloadConfig()
    ElMessage.success('热加载成功')
    loadParams()
  } catch (e) {
    console.error(e)
  }
}

const formatValue = (value: any) => {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const getCategoryLabel = (category: string) => {
  const labels: Record<string, string> = {
    yolo_detection: 'YOLO 检测',
    alarm_logic: '报警逻辑',
    hardware: '硬件配置',
    general: '通用配置'
  }
  return labels[category] || category
}

const getCategoryTagType = (category: string) => {
  const types: Record<string, any> = {
    yolo_detection: 'primary',
    alarm_logic: 'success',
    hardware: 'warning',
    general: 'info'
  }
  return types[category] || ''
}

const getPermissionLabel = (permission: string) => {
  const labels: Record<string, string> = {
    read_only: '只读',
    editable: '可编辑',
    restricted: '受限'
  }
  return labels[permission] || permission
}

const getPermissionTagType = (permission: string) => {
  const types: Record<string, any> = {
    read_only: 'info',
    editable: 'success',
    restricted: 'danger'
  }
  return types[permission] || ''
}

const getActionTagType = (action: string) => {
  const types: Record<string, any> = {
    create: 'success',
    update: 'primary',
    delete: 'danger',
    import: 'warning',
    export: 'info'
  }
  return types[action] || ''
}

onMounted(() => {
  loadParams()
  loadAuditLogs()
})
</script>

<style scoped>
.system-view {
  padding: 20px;
}

.header-card,
.filter-card,
.params-card {
  margin-bottom: 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.header-content h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-actions :deep(.el-upload) {
  display: inline-flex;
}

.header-actions :deep(.el-button) {
  height: 32px;
}
</style>
