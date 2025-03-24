// 模拟浏览器的 localStorage
const localStorageMock = {
  store: {} as { [key: string]: string },
  length: 0,
  clear() {
    this.store = {}
    this.length = 0
  },
  getItem(key: string) {
    return this.store[key] || null
  },
  setItem(key: string, value: string) {
    this.store[key] = String(value)
    this.length = Object.keys(this.store).length
  },
  removeItem(key: string) {
    delete this.store[key]
    this.length = Object.keys(this.store).length
  },
  key(n: number) {
    return Object.keys(this.store)[n] || null
  }
}

Object.defineProperty(global, 'localStorage', {
  value: localStorageMock
}) 