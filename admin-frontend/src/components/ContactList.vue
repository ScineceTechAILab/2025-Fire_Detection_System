<template>
  <div class="contact-list">
    <div class="toolbar">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增联系人
      </el-button>
      <el-button plain @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <el-table v-loading="loading" :data="contacts" stripe>
      <el-table-column prop="name" label="姓名" min-width="140" />
      <el-table-column prop="identity" label="身份" min-width="160" />
      <el-table-column prop="phone" label="手机号" min-width="180" />
      <el-table-column prop="created_at" label="创建时间" min-width="190">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <EmptyState title="暂无联系人" description="点击上方“新增联系人”开始配置。" />
      </template>
    </el-table>

    <ContactForm
      v-model:visible="formVisible"
      :is-edit="isEdit"
      :edit-data="editData"
      @submit="handleFormSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import ContactForm from './ContactForm.vue'
import EmptyState from './common/EmptyState.vue'
import type { Contact, ContactCreate, ContactUpdate } from '@/types'

interface Props {
  contacts: Contact[]
  loading: boolean
  onAdd?: (data: ContactCreate) => Promise<void>
  onEdit?: (id: string, data: ContactUpdate) => Promise<void>
  onDelete?: (id: string) => Promise<void>
  onRefresh?: () => Promise<void>
}

const props = defineProps<Props>()

const formVisible = ref(false)
const isEdit = ref(false)
const editData = ref<Contact | null>(null)

const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString('zh-CN')

const handleAdd = () => {
  isEdit.value = false
  editData.value = null
  formVisible.value = true
}

const handleEdit = (row: Contact) => {
  isEdit.value = true
  editData.value = row
  formVisible.value = true
}

const handleDelete = async (row: Contact) => {
  try {
    await ElMessageBox.confirm(`确定删除联系人「${row.name}」吗？`, '删除确认', { type: 'warning' })
    if (props.onDelete) {
      await props.onDelete(row.id)
      ElMessage.success('删除成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleRefresh = async () => {
  if (props.onRefresh) {
    await props.onRefresh()
  }
}

const handleFormSubmit = async (data: ContactCreate | ContactUpdate) => {
  if (isEdit.value && editData.value) {
    if (props.onEdit) {
      await props.onEdit(editData.value.id, data)
      ElMessage.success('更新成功')
    }
    return
  }

  if (props.onAdd) {
    await props.onAdd(data as ContactCreate)
    ElMessage.success('创建成功')
  }
}
</script>

<style scoped>
.contact-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
