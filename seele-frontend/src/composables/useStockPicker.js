import { ref, computed } from 'vue'

/**
 * 通用选股策略 composable
 * 封装 loading / list / total / page / sort 通用状态，支持后端排序与前端排序两种模式
 *
 * @param {Object} options
 * @param {Function} options.fetcher - API 调用函数 (params) => Promise<{list, total}>
 * @param {string} options.defaultSortField - 默认排序字段（snake_case，与后端字段对齐）
 * @param {string} options.defaultSortOrder - 默认排序方向 'asc' | 'desc'，默认 'desc'
 * @param {boolean} options.serverSort - 是否使用后端排序，默认 false
 * @param {number} options.defaultPageSize - 默认每页条数，默认 20
 * @param {number} options.fetchPageSize - 前端排序模式下单次拉取的总条数，默认 500
 */
export function useStockPicker (options = {}) {
  const {
    fetcher,
    defaultSortField = '',
    defaultSortOrder = 'desc',
    serverSort = false,
    defaultPageSize = 20,
    fetchPageSize = 500
  } = options

  const loading = ref(false)
  const rawList = ref([])
  const serverTotal = ref(0)
  const pageNum = ref(1)
  const pageSize = ref(defaultPageSize)
  const sortField = ref(defaultSortField)
  const sortOrder = ref(defaultSortOrder)

  // 缓存上次 search 的 extraParams（来自 filter），便于 sort/page 切换时复用
  let lastExtraParams = {}

  function compareForSort (a, b) {
    if (a == null && b == null) return 0
    if (a == null) return 1
    if (b == null) return -1
    if (typeof a === 'number' && typeof b === 'number') {
      return a - b
    }
    return String(a).localeCompare(String(b), undefined, { numeric: true })
  }

  function getSortIcon (field) {
    if (sortField.value !== field) return '⇅'
    return sortOrder.value === 'asc' ? '▲' : '▼'
  }

  function buildParams () {
    const params = { ...lastExtraParams }
    if (serverSort) {
      params.sort_field = sortField.value
      params.sort_order = sortOrder.value
      params.page_num = pageNum.value
      params.page_size = pageSize.value
    } else {
      params.page_num = 1
      params.page_size = fetchPageSize
    }
    return params
  }

  async function reload () {
    if (!fetcher) return
    loading.value = true
    try {
      const data = await fetcher(buildParams())
      rawList.value = data?.list || []
      serverTotal.value = data?.total || 0
    } catch (error) {
      console.error('加载选股数据失败:', error)
      rawList.value = []
      serverTotal.value = 0
    } finally {
      loading.value = false
    }
  }

  /**
   * 触发新的搜索，重置页码到第 1 页
   * @param {Object} extraParams - 来自 filter 的查询参数（snake_case）
   */
  async function search (extraParams = {}) {
    lastExtraParams = { ...extraParams }
    pageNum.value = 1
    await reload()
  }

  function handleSort (field) {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = 'desc'
    }
    if (serverSort) {
      pageNum.value = 1
      reload()
    }
  }

  function handlePageChange (newPage) {
    pageNum.value = newPage
    if (serverSort) {
      reload()
    }
  }

  function handlePageSizeChange (newSize) {
    pageSize.value = newSize
    pageNum.value = 1
    if (serverSort) {
      reload()
    }
  }

  // 显示列表：serverSort 直接用 rawList；clientSort 本地排序+切片
  const displayList = computed(() => {
    if (serverSort) {
      return rawList.value
    }
    const list = [...rawList.value]
    if (sortField.value) {
      list.sort((a, b) => {
        const result = compareForSort(a[sortField.value], b[sortField.value])
        return sortOrder.value === 'asc' ? result : -result
      })
    }
    const start = (pageNum.value - 1) * pageSize.value
    return list.slice(start, start + pageSize.value)
  })

  // 显示总数：serverSort 用后端返回的 total；clientSort 用 rawList 长度
  const total = computed(() => {
    if (serverSort) return serverTotal.value
    return rawList.value.length
  })

  return {
    loading,
    rawList,
    total,
    pageNum,
    pageSize,
    sortField,
    sortOrder,
    displayList,
    search,
    reload,
    handleSort,
    handlePageChange,
    handlePageSizeChange,
    getSortIcon
  }
}
