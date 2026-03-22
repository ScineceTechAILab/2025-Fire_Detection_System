<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑联系人' : '新增联系人'"
    width="520px"
    destroy-on-close
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="请输入姓名" />
      </el-form-item>
      <el-form-item label="身份" prop="identity">
        <el-input v-model="form.identity" placeholder="请输入身份描述" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="form.phone" placeholder="请输入手机号（不含 +86）" />
        <p class="helper-text">系统会自动补全国家码 +86</p>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { ContactCreate, ContactUpdate } from '@/types'

interface Props {
  visible: boolean
  isEdit: boolean
  editData?: {
    name: string
    identity: string
    phone: string
  } | null
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'submit', data: ContactCreate | ContactUpdate): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()
const submitLoading = ref(false)

const form = ref<ContactCreate & ContactUpdate>({
  name: '',
  identity: '',
  phone: ''
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  identity: [{ required: true, message: '请输入身份', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }]
}

watch(
  () => props.visible,
  (val) => {
    dialogVisible.value = val
    if (!val) return

    if (props.isEdit && props.editData) {
      form.value = {
        name: props.editData.name,
        identity: props.editData.identity,
        phone: props.editData.phone.replace('+86', '')
      }
      return
    }

    form.value = { name: '', identity: '', phone: '' }
  }
)

watch(dialogVisible, (val) => emit('update:visible', val))

const handleClose = () => {
  dialogVisible.value = false
  formRef.value?.resetFields()
}

const handleSubmit = async () => {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    emit('submit', { ...form.value })
    handleClose()
  } finally {
    submitLoading.value = false
  }
}
</script>

<style scoped>
.helper-text {
  margin: 6px 0 0;
  line-height: 1.4;
  color: var(--fd-text-tertiary);
  font-size: 12px;
}
</style>
