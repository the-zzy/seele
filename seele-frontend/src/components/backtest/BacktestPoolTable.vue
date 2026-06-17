<script setup>
defineProps({
  list: {
    type: Array,
    default: () => []
  }
})

function fmt (v) {
  if (v == null) return '-'
  const n = Number(v)
  if (Number.isNaN(n)) return '-'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<template>
  <div class="table-wrap">
    <div v-if="!list.length" class="state empty">当日无买入池子</div>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th>股票代码</th>
          <th>股票名称</th>
          <th class="num">层</th>
          <th class="num">收盘价</th>
          <th class="num">MA5</th>
          <th class="num">MA10</th>
          <th class="num">MA20</th>
          <th class="num">评分</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in list" :key="item.symbol" class="data-row">
          <td class="mono">{{ item.symbol }}</td>
          <td>{{ item.name }}</td>
          <td class="num">{{ item.layer }}</td>
          <td class="num">{{ fmt(item.close) }}</td>
          <td class="num">{{ fmt(item.ma5) }}</td>
          <td class="num">{{ fmt(item.ma10) }}</td>
          <td class="num">{{ fmt(item.ma20) }}</td>
          <td class="num">{{ item.score?.total ?? '-' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped lang="scss">
.table-wrap {
  overflow: auto;
  border: 1px solid var(--rule);
  border-radius: 8px;
}

.stock-table {
  min-width: 560px;
  width: 100%;
}

.state {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
