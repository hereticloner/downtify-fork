<template>
  <div class="flex flex-col gap-2">
    <div
      v-for="(node, index) in nodes"
      :key="index"
      class="flex flex-col gap-2 border-2 border-line-2 p-3"
    >
      <template v-if="node.op">
        <div class="flex flex-wrap items-end gap-2">
          <UiSelect
            :model-value="node.op"
            :options="groupOptions"
            :label="t('collections.ruleGroup')"
            block
            class="sm:w-36"
            @update:model-value="changeGroup(index, $event)"
          />
          <UiButton
            size="sm"
            variant="ghost"
            icon="plus"
            @click="addNode(index, blankRule())"
          >
            {{ t('collections.addRule') }}
          </UiButton>
          <UiButton
            size="sm"
            variant="ghost"
            icon="plus"
            :disabled="node.op === 'not'"
            @click="addNode(index, blankGroup())"
          >
            {{ t('collections.addGroup') }}
          </UiButton>
          <UiIconButton
            icon="trash"
            :label="t('common.delete')"
            class="ms-auto self-end"
            @click="removeNode(index)"
          />
        </div>
        <CollectionRuleEditor
          :model-value="node.rules"
          class="mt-1"
          @update:model-value="setChildren(index, $event)"
        />
      </template>

      <template v-else>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-end">
          <UiSelect
            :model-value="node.type"
            :options="typeOptions"
            :label="t('collections.ruleType')"
            block
            class="sm:w-40"
            @update:model-value="changeType(node, $event)"
          />
          <template v-if="node.type === 'added'">
            <UiInput
              v-model="node.from"
              type="date"
              :label="t('collections.ruleFrom')"
            />
            <UiInput
              v-model="node.to"
              type="date"
              :label="t('collections.ruleTo')"
            />
          </template>
          <template v-else-if="node.type === 'plays'">
            <UiInput
              v-model="node.min"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('collections.ruleMin')"
            />
            <UiInput
              v-model="node.max"
              type="number"
              min="0"
              inputmode="numeric"
              :label="t('collections.ruleMax')"
            />
          </template>
          <UiInput
            v-else
            v-model="node.value"
            :label="t('collections.ruleValue')"
            :placeholder="t('collections.ruleValuePlaceholder')"
          />
          <UiIconButton
            icon="trash"
            :label="t('common.delete')"
            class="self-end"
            @click="removeNode(index)"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '/src/i18n'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiInput from '/src/components/ui/UiInput.vue'
import UiSelect from '/src/components/ui/UiSelect.vue'
import {
  GROUP_OPS,
  RULE_TYPES,
  blankGroup,
  blankRule,
} from '/src/lib/collectionRules'

defineOptions({ name: 'CollectionRuleEditor' })
const props = defineProps({
  modelValue: { type: Array, required: true },
})
const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const nodes = computed(() => props.modelValue)
const groupOptions = computed(() =>
  GROUP_OPS.map((op) => ({
    value: op,
    label: t(`collections.rule${op[0].toUpperCase()}${op.slice(1)}`),
  }))
)
const typeOptions = computed(() =>
  RULE_TYPES.map((type) => ({
    value: type,
    label: t(`collections.rule${type[0].toUpperCase()}${type.slice(1)}`),
  }))
)

function changed() {
  emit('update:modelValue', [...props.modelValue])
}
function addNode(index, node) {
  nodes.value[index].rules.push(node)
  changed()
}
function removeNode(index) {
  nodes.value.splice(index, 1)
  changed()
}
function setChildren(index, children) {
  nodes.value[index].rules = children
  changed()
}
function changeGroup(index, op) {
  const node = nodes.value[index]
  node.op = op
  if (op === 'not' && node.rules.length > 1) node.rules = node.rules.slice(0, 1)
  changed()
}
function changeType(node, type) {
  if (node.type === type) return
  const fresh = blankRule(type)
  for (const key of Object.keys(node)) delete node[key]
  Object.assign(node, fresh)
  changed()
}
</script>
