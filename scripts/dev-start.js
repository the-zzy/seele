#!/usr/bin/env node
/**
 * 一键开发环境启动脚本
 * 1. 清理旧 Python / Node 进程
 * 2. 启动后端 (port 9000)
 * 3. 启动前端 (port 8000)
 */
const { spawn, execSync } = require('child_process')
const path = require('path')

const ROOT = path.resolve(__dirname, '..')
const BACKEND_DIR = path.join(ROOT, 'seele-backend')
const FRONTEND_DIR = path.join(ROOT, 'seele-frontend')

function log(msg) {
  console.log(`[dev-start] ${msg}`)
}

function getPidOnPort(port) {
  try {
    const output = execSync(
      `netstat -ano | findstr :${port}`,
      { encoding: 'utf-8', shell: 'cmd.exe' }
    )
    const lines = output.trim().split('\n')
    for (const line of lines) {
      const parts = line.trim().split(/\s+/)
      if (parts.length >= 5 && parts[1].endsWith(`:${port}`) && parts[3] === 'LISTENING') {
        return parseInt(parts[4], 10)
      }
    }
  } catch {
    // ignore
  }
  return null
}

function killPid(pid) {
  if (!pid) return
  try {
    execSync(`taskkill /F /PID ${pid} /T`, { stdio: 'ignore', shell: 'cmd.exe' })
    log(`已终止 PID ${pid}`)
  } catch {
    // ignore
  }
}

async function waitForPort(port, timeout = 30000) {
  const net = require('net')
  const start = Date.now()
  while (Date.now() - start < timeout) {
    try {
      await new Promise((resolve, reject) => {
        const socket = net.createConnection(port, '127.0.0.1')
        socket.on('connect', () => {
          socket.destroy()
          resolve()
        })
        socket.on('error', reject)
      })
      return true
    } catch {
      await new Promise(r => setTimeout(r, 500))
    }
  }
  return false
}

async function main() {
  log('=== 开始清理旧进程 ===')
  killPid(getPidOnPort(9000))
  killPid(getPidOnPort(8000))

  // 等待端口释放
  await new Promise(r => setTimeout(r, 1500))

  log('=== 启动后端 ===')
  const backend = spawn('python start.py', {
    cwd: BACKEND_DIR,
    stdio: 'inherit',
    shell: true
  })

  const backendReady = await waitForPort(9000, 30000)
  if (!backendReady) {
    log('后端启动超时')
    backend.kill()
    process.exit(1)
  }
  log('后端已就绪 (http://127.0.0.1:9000)')

  log('=== 启动前端 ===')
  const frontend = spawn('npm run serve', {
    cwd: FRONTEND_DIR,
    stdio: 'inherit',
    shell: true
  })

  const frontendReady = await waitForPort(8000, 60000)
  if (!frontendReady) {
    log('前端启动超时')
    frontend.kill()
    backend.kill()
    process.exit(1)
  }
  log('前端已就绪 (http://localhost:8000)')
  log('=== 全部启动完成 ===')

  // 优雅退出
  const cleanup = () => {
    log('正在关闭服务...')
    backend.kill()
    frontend.kill()
    process.exit(0)
  }
  process.on('SIGINT', cleanup)
  process.on('SIGTERM', cleanup)
}

main().catch(err => {
  console.error('[dev-start] 错误:', err)
  process.exit(1)
})
