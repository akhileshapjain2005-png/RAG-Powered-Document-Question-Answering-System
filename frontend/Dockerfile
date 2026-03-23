FROM node:18-alpine AS builder

WORKDIR /app

ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
ARG VITE_API_KEY=
ENV VITE_API_KEY=${VITE_API_KEY}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
