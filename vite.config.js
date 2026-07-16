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
        // 端口迁移说明（2026-07-16）：
        // 8080/8081/8082/8083 是用户本机会话旧后端（沙箱杀不掉），代码过期（非靶误存 CR、无病灶编辑 API 等）。
        // 8084/8086/8093/8094/8097/8098/8099 均残留 Windows 孤儿监听套接字（taskkill 后仍 LISTENING，新进程绑定报 10048），
        //   其中 8099(PID 23180) 经实测为孤儿套接字，沙箱无法终止、无法复用。
        // 故本次切换至全新端口 8101，并由沙箱启动载最新代码的后端（含 AI 助手 /api/chat 路由、手动新增受试者写入 batch_id、
        //   各接口批次过滤、_sync_assessment_date 对齐最新病灶检查日期、非靶字段补全等）。
        // 该端口已通过 /api/chat 四类意图（标准/列表/详情/统计）端到端冒烟。
        // 生产部署时用户在自己终端用 `uvicorn app.main:app --port 8080` 启动正确后端即可，dist 由 SERVE_FRONTEND 同源托管，不依赖此代理。
        target: 'http://127.0.0.1:8101',
        changeOrigin: true
      }
    }
  }
})
