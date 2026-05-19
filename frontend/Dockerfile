# ========== 构建阶段 ==========
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖（利用 Docker 层缓存）
COPY package.json ./
RUN npm install

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
