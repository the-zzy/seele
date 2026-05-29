const { execSync } = require('child_process')

function getPidsOnPort (port) {
  try {
    const stdout = execSync(
      `powershell -NoProfile -Command "Try { \$conns = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction Stop; \$conns | ForEach-Object { \$_.OwningProcess } | Select-Object -Unique } Catch { }"`,
      { encoding: 'utf-8', timeout: 5000 }
    )
    return stdout.trim().split('\n').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n > 0)
  } catch {
    return []
  }
}

function isPortInUse (port) {
  try {
    const stdout = execSync(
      `powershell -NoProfile -Command "Try { \$conns = Get-NetTCPConnection -LocalPort ${port} -State Listen -ErrorAction Stop; if (\$conns) { 'true' } } Catch { 'false' }"`,
      { encoding: 'utf-8', timeout: 5000 }
    )
    return stdout.trim().toLowerCase() === 'true'
  } catch {
    return false
  }
}

function killPort (port) {
  const currentPid = process.pid
  const pids = getPidsOnPort(port).filter(pid => pid !== currentPid)

  if (pids.length === 0) {
    console.log(`[cleanup] Port ${port} is clean`)
    return
  }

  for (const pid of pids) {
    try {
      execSync(`taskkill /PID ${pid} /F`, { stdio: 'ignore' })
      console.log(`[cleanup] Killed PID ${pid} occupying port ${port}`)
    } catch {
      console.log(`[cleanup] Failed to kill PID ${pid}`)
    }
  }

  for (let i = 0; i < 5; i++) {
    if (!isPortInUse(port)) {
      console.log(`[cleanup] Port ${port} is now free`)
      return
    }
    try {
      execSync('powershell -Command "Start-Sleep 1"', { stdio: 'ignore' })
    } catch {}
  }

  console.log(`[cleanup] WARNING: Port ${port} is still in use after cleanup`)
}

const port = parseInt(process.argv[2], 10) || 8000
killPort(port)
