const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  configureWebpack: {
    cache: {
      type: 'filesystem',
      buildDependencies: {
        config: [__filename]
      }
    }
  },
  css: {
    loaderOptions: {
      scss: {
        additionalData: '@use "~@/styles/variables.scss" as *;'
      }
    }
  },
  devServer: {
    port: 8000,
    historyApiFallback: true,
    proxy: {
      '/api': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        pathRewrite: {
          '^/api': '/api'
        }
      }
    }
  }
})
