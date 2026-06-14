const fs = require('fs')
const path = require('path')

const versionPath = path.resolve(__dirname, '..', '..', 'VERSION')
const packagePaths = [
  path.resolve(__dirname, '..', 'package.json'),
  path.resolve(__dirname, '..', '..', 'package.json')
]

if (!fs.existsSync(versionPath)) {
  console.warn('[sync-version] VERSION file not found, skip')
  process.exit(0)
}

const version = fs.readFileSync(versionPath, 'utf-8').trim()

packagePaths.forEach(packagePath => {
  if (!fs.existsSync(packagePath)) {
    console.warn(`[sync-version] ${packagePath} not found, skip`)
    return
  }

  const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf-8'))

  if (pkg.version !== version) {
    pkg.version = version
    fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + '\n')
    console.log(`[sync-version] updated ${path.basename(path.dirname(packagePath))}/package.json version to ${version}`)
  } else {
    console.log(`[sync-version] ${path.basename(path.dirname(packagePath))}/package.json version already ${version}`)
  }
})
