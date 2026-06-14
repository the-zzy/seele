const { defineConfig } = require('@vue/cli-service')
const fs = require('fs')
const path = require('path')

const versionPath = path.resolve(__dirname, '..', 'VERSION')
const appVersion = fs.existsSync(versionPath)
  ? fs.readFileSync(versionPath, 'utf-8').trim()
  : require('./package.json').version

process.env.VUE_APP_VERSION = appVersion

module.exports = defineConfig({
  filenameHashing: true,
  transpileDependencies: true,
  configureWebpack: {
    cache: {
      type: 'filesystem',
      buildDependencies: {
        config: [__filename]
      }
    },
    output: {
      filename: 'js/[name].[contenthash:8].js',
      chunkFilename: 'js/[name].[contenthash:8].js'
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
