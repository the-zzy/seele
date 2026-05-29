import request from '@/utils/request'

/**
 * 图库管理 API
 */
export const galleryApi = {
  /**
   * 获取图片列表
   * @returns {Promise<Array>}
   */
  getList () {
    return request({
      url: '/gallery/images',
      method: 'get'
    })
  },

  /**
   * 上传图片
   * @param {File} file - 图片文件
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Object>}
   */
  upload (file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    return request({
      url: '/gallery/upload',
      method: 'post',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  },

  /**
   * 删除图片
   * @param {number} id - 图片ID
   * @returns {Promise<Object>}
   */
  delete (id) {
    return request({
      url: `/gallery/images/${id}`,
      method: 'delete'
    })
  }
}
