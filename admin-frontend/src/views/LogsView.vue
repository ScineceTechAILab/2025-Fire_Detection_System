<template>
  <div class="logs-view">
    <el-card class="header-card">
      <div class="header-content">
        <h2>日志查询</h2>
      </div>
    </el-card>

    <el-card class="filter-card">
      <div class="filters">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm:ss"
          value-format="YYYY-MM-DD HH:mm:ss"
          style="min-width: 360px"
        />
        <el-select v-model="selectedLevels" multiple collapse-tags collapse-tags-tooltip placeholder="级别" style="width: 220px">
          <el-option label="DEBUG" value="DEBUG" />
          <el-option label="INFO" value="INFO" />
          <el-option label="WARNING" value="WARNING" />
          <el-option label="ERROR" value="ERROR" />
          <el-option label="CRITICAL" value="CRITICAL" />
        </el-select>
        <el-input v-model="keyword" clearable placeholder="关键字（内容或模块名）" style="width: 260px" @keyup.enter="handleSearch" />
        <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
        <el-button :disabled="loading" @click="handleReset">重置</el-button>
      </div>
    </el-card>

    <el-card class="table-card">
      <el-table v-loading="loading" :data="rows" stripe style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <pre class="log-detail">{{ row.message }}</pre>
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间" width="180" />
        <el-table-column label="级别" width="110">
          <template #default="{ row }">
            <el-tag :type="levelTagType(row.level)">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="logger" label="模块" width="220" show-overflow-tooltip />
        <el-table-column prop="message" label="内容" min-width="380" show-overflow-tooltip />
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[50, 100, 200, 500]"
          layout="total, sizes, prev, pager, next, jumper"
          background
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { logsApi } from '@/api/logs'
import type { LogEntry } from '@/types'

const loading = ref(false)
const rows = ref<LogEntry[]>([])
const total = ref(0)

const page = ref(1)
const pageSize = ref(100)

const timeRange = ref<[string, string] | null>(null)
const selectedLevels = ref<string[]>(['INFO', 'WARNING', 'ERROR', 'CRITICAL'])
const keyword = ref('')

const setDefaultRange = () => {
  const end = new Date()
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
  timeRange.value = [formatDateTime(start), formatDateTime(end)]
}

const formatDateTime = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  const yyyy = d.getFullYear()
  const MM = pad(d.getMonth() + 1)
  const dd = pad(d.getDate())
  const HH = pad(d.getHours())
  const mm = pad(d.getMinutes())
  const ss = pad(d.getSeconds())
  return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`
}

const handleSearch = async () => {
  loading.value = true
  try {
    const offset = (page.value - 1) * pageSize.value
    const res = await logsApi.query({
      start: timeRange.value?.[0],
      end: timeRange.value?.[1],
      levels: selectedLevels.value.length ? selectedLevels.value : undefined,
      keyword: keyword.value || undefined,
      offset,
      limit: pageSize.value,
      order: 'desc'
    })
    rows.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  page.value = 1
  pageSize.value = 100
  keyword.value = ''
  selectedLevels.value = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
  setDefaultRange()
  handleSearch()
}

const levelTagType = (level: string) => {
  const v = (level || '').toUpperCase()
  if (v === 'ERROR' || v === 'CRITICAL') return 'danger'
  if (v === 'WARNING') return 'warning'
  if (v === 'INFO') return 'info'
  return ''
}

onMounted(() => {
  setDefaultRange()
  handleSearch()
})
</script>

<style scoped>
.logs-view {
  padding: 20px;
}

.header-card,
.filter-card,
.table-card {
  margin-bottom: 20px;
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.header-content h2 {
  margin: 0;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.log-detail {
  white-space: pre-wrap;
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>

