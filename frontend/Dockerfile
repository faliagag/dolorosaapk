FROM node:20-alpine AS builder
WORKDIR /app

# Copiar solo archivos de dependencias primero (cache de Docker)
COPY package.json ./
# Instalar con npm para evitar conflictos de lockfile
RUN npm install --legacy-peer-deps && \
    npm install ajv@^8 --legacy-peer-deps

COPY . .

# Recibe la URL del backend desde CapRover en tiempo de build
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL
ENV GENERATE_SOURCEMAP=false
ENV NODE_OPTIONS=--max-old-space-size=1536
ENV CI=false

RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
