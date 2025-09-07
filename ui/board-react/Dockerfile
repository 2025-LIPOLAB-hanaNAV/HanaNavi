FROM node:18-alpine as build
WORKDIR /app
# Cache deps
COPY ui/board-react/package*.json /app/
RUN npm ci || npm i
# Then copy sources
COPY ui/board-react/ /app
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY ui/board-react/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
