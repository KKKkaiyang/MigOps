# MigOps 前端（Vue 3 / Vite / TypeScript）

## 技术栈
- Vue 3（`<script setup>`）+ Vite + TypeScript
- Vue Router 4（按模块 b01~b05 划分路由）
- Pinia（状态管理）
- Element Plus（UI 组件库）
- Axios（请求封装：`src/api/request.ts`）

## 目录结构
```
src/
├── api/        # 接口封装，按模块 b01~b05 分文件（space.ts 为示例）
├── components/ # 通用组件（common/ 放公共组件）
├── router/     # 路由定义
├── store/      # Pinia 状态
├── types/      # TS 类型（与后端 Schema 对齐）
├── utils/      # 工具函数
└── views/      # 页面级组件，按模块分目录
```

## 运行
```bash
npm install
npm run dev      # 开发：http://localhost:5173 （/api 代理到后端 8000）
npm run build    # 构建
```

## 约定
- 页面列表统一 `搜索 + 表格 + 分页 + 弹窗表单` 交互模式，复用 Element Plus 组件。
- 接口层只做请求封装，业务逻辑/数据获取优先放 `store` 或视图内调用。
- 新增模块请参照 `views/space/SpaceList.vue` + `api/space.ts` 的 b01 实现。
