<template>
  <div class="contact-list">
    <div class="toolbar">
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        新增联系人
      </el-button>
      <el-button @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    
    <el-table v-loading="loading" :data="contacts" border>
      <el-table-column prop="name" label="姓名" width="150" />
      <el-table-column prop="identity" label="身份" width="150" />
      <el-table-column prop="phone" label="手机号" width="180" />
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
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

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

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
    await ElMessageBox.confirm(
      `确定要删除联系人「${row.name}」吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    if (props.onDelete) {
      await props.onDelete(row.id)
      ElMessage.success('删除成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

const handleRefresh = () => {
  if (props.onRefresh) {
    props.onRefresh()
  }
}

const handleFormSubmit = async (data: ContactCreate | ContactUpdate) => {
  try {
    if (isEdit.value && editData.value) {
      if (props.onEdit) {
        await props.onEdit(editData.value.id, data)
        ElMessage.success('更新成功')
      }
    } else {
      if (props.onAdd) {
        await props.onAdd(data as ContactCreate)
        ElMessage.success('创建成功')
      }
    }
  } catch (error) {
    console.error(error)
  }
}
</script>

<style scoped>
.contact-list {
  padding: 20px;
  background: white;
  border-radius: 4px;
}

.toolbar {
  margin-bottom: 16px;
}
</style>
