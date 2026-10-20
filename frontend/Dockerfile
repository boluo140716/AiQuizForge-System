# ========== 构建阶段 ==========
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖（利用 Docker 层缓存）
# 必须同时复制 package-lock.json，否则 npm 会忽略锁文件重新解析，容易触发依赖解析 bug
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# 复制源码并构建
COPY . .
RUN npm run build

# ========== 运行阶段 ==========
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置（反向代理 API 请求到 backend / ai-service）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
