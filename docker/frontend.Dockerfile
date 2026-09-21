FROM node:20-alpine AS build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# VITE_API_URL is baked into the bundle at build time: there is no runtime
# fallback. Production builds MUST pass --build-arg VITE_API_URL=<api origin>.
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build:prod

FROM nginx:alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY docker/nginx.frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
