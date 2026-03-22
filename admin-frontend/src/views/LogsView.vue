<template>
  <div class="fd-page">
    <PageHeader title="日志查询" description="按时间、级别和关键词快速检索日志，支持分页查看与详情展开。">
      <template #actions>
        <ActionBar>
          <el-button :loading="loading" @click="handleSearch">刷新</el-button>
          <el-button plain @click="handleReset">重置条件</el-button>
        </ActionBar>
      </template>
    </PageHeader>

    <FilterBar>
      <div class="filters">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm:ss"
          value-format="YYYY-MM-DD HH:mm:ss"
          class="filter-date"
        />
        <el-select
          v-model="selectedLevels"
          multiple
          collapse-tags
          collapse-tags-tooltip
          placeholder="日志级别"
          class="filter-levels"
        >
          <el-option label="DEBUG" value="DEBUG" />
          <el-option label="INFO" value="INFO" />
          <el-option label="WARNING" value="WARNING" />
          <el-option label="ERROR" value="ERROR" />
          <el-option label="CRITICAL" value="CRITICAL" />
        </el-select>
        <el-input v-model="keyword" clearable placeholder="关键词（内容或模块）" class="filter-keyword" @keyup.enter="handleSearch" />
        <el-button type="primary" :loading="loading" @click="handleSearch">查询</el-button>
      </div>
    </FilterBar>

    <DataCard>
      <el-table v-loading="loading" :data="rows" stripe>
        <el-table-column type="expand">
          <template #default="{ row }">
            <pre class="log-detail fd-mono">{{ row.message }}</pre>
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间" width="190" />
        <el-table-column label="级别" width="120">
          <template #default="{ row }">
            <StatusTag mode="log-level" :value="(row.level || '').toUpperCase()" />
          </template>
        </el-table-column>
        <el-table-column prop="logger" label="模块" min-width="220" show-overflow-tooltip />
        <el-table-column prop="message" label="内容" min-width="420" show-overflow-tooltip />
        <template #empty>
          <EmptyState title="暂无日志" description="请调整筛选条件后重试。" />
        </template>
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
    </DataCard>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { logsApi } from '@/api/logs'
import type { LogEntry } from '@/types'
import ActionBar from '@/components/layout/ActionBar.vue'
import DataCard from '@/components/layout/DataCard.vue'
import FilterBar from '@/components/layout/FilterBar.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'

const loading = ref(false)
const rows = ref<LogEntry[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(100)
const timeRange = ref<[string, string] | null>(null)
const selectedLevels = ref<string[]>(['INFO', 'WARNING', 'ERROR', 'CRITICAL'])
const keyword = ref('')

const formatDateTime = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const setDefaultRange = () => {
  const end = new Date()
  const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000)
  timeRange.value = [formatDateTime(start), formatDateTime(end)]
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

const handleReset = async () => {
  page.value = 1
  pageSize.value = 100
  keyword.value = ''
  selectedLevels.value = ['INFO', 'WARNING', 'ERROR', 'CRITICAL']
  setDefaultRange()
  await handleSearch()
}

onMounted(async () => {
  setDefaultRange()
  await handleSearch()
})
</script>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-date {
  min-width: 340px;
}

.filter-levels {
  width: 240px;
}

.filter-keyword {
  width: 280px;
}

.log-detail {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 12px;
}

.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .filter-date,
  .filter-levels,
  .filter-keyword {
    width: 100%;
    min-width: 0;
  }
}
</style>
