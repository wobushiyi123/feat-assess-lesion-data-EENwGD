import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173, 
    allowedHosts: true,

 // 将 /api 请求代理到本机后端（127.0.0.1），从而：
    // 1) 局域网设备只需访问 5173（node 已被防火墙放行），无需为后端端口单独开放防火墙
    // 2) 浏览器视角下前后端同源，彻底消除跨域(CORS)问题
    proxy: {
      '/api': {
        // 注意：8080 上是用户本机会话里跑的旧后端（沙箱无法重启），曾把非靶误存 CR、且不写病灶明细。
        // 8081/8082/8083 同样是旧进程（沙箱杀不掉，路由里没有病灶编辑 API 或旧版 nadir bug）。
        // 8084/8086 残留 Windows 孤儿监听套接字无法释放，新进程绑定报 10048，故换用全新端口 8093 避孤儿。
        // 本端口载最新代码：assessment_date 改为可选、手动新增受试者/评估写入 batch_id（全表按批次同步）、各接口批次过滤。
        // 待用户在自己终端重启 8080 正确后端并清掉孤儿端口后，可改回 http://127.0.0.1:8080。
        target: 'http://127.0.0.1:8098',
        changeOrigin: true
      }
    }
  }
})
