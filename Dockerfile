FROM node:22.16.0-alpine AS build
WORKDIR /build
COPY package*.json ./
RUN npm ci --legacy-peer-deps
COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
COPY public ./public
RUN npm run build
FROM nginx:1.28.0-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html
EXPOSE 80
