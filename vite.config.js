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
  build: {
    // 打包优化：拆分大依赖为独立 vendor 分包，提升浏览器并行加载与长缓存命中率（不改变任何页面与业务逻辑）
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('echarts')) return 'echarts'
            if (id.includes('element-plus') || id.includes('@element-plus') || id.includes('@vue')) return 'element-plus'
            if (id.includes('/vue/') || id.includes('vue-router') || id.includes('pinia')) return 'vue'
            return 'vendor'
          }
        }
      }
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
        // 8084/8086/8094/8097/8098 均残留 Windows 孤儿监听套接字（taskkill 后仍 LISTENING），新进程绑定报 10048，
        //   故换用全新端口 8099 避孤儿；该端口已用最新代码启动并通过端到端冒烟（非靶 current_exam_date→评估主日期同步、PD 实际评估生效）。
        // 本端口载最新代码：assessment_date 改为可选、手动新增受试者/评估写入 batch_id（全表按批次同步）、各接口批次过滤、
        //   新增 _sync_assessment_date() 把评估主日期对齐最新病灶检查日期、非靶基线状态/当前检查日期字段补全。
        // 待用户在自己终端重启 8080 正确后端并清掉孤儿端口后，可改回 http://127.0.0.1:8080。
        target: 'http://127.0.0.1:8099',
        changeOrigin: true
      }
    }
  }
})
