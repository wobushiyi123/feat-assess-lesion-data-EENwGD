<template>
  <el-config-provider :message="{ duration: 1000, max: 3 }">
    <router-view />
  </el-config-provider>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Microsoft YaHei', sans-serif; background-color: #f5f7fa; min-height: 100vh; }
</style>