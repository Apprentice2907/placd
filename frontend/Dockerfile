# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Define build arguments
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

# Install dependencies (assuming package.json exists)
# We use a trick to gracefully fail if package.json doesn't exist yet,
# since frontend code might not be initialized.
COPY package*.json ./
RUN if [ -f package.json ]; then npm ci; fi

# Copy source and build
COPY . .
RUN if [ -f package.json ]; then npm run build; else mkdir dist && echo "Building React App Placeholder" > dist/index.html; fi

# Stage 2: Serve
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
