FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
# Note: --legacy-peer-deps is used to handle peer dependency conflicts
# between React 18 and some older packages. This is a temporary workaround.
# TODO: Resolve peer dependency conflicts properly by upgrading conflicting packages.
RUN npm install --legacy-peer-deps
RUN npm install -g serve

# Copy application code
COPY . .

# Copy and set entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Build the application
ARG REACT_APP_IS_DEMO
ENV REACT_APP_IS_DEMO=$REACT_APP_IS_DEMO
RUN npm run build

# Expose port
EXPOSE 3000

# Use entrypoint script to ensure dependencies are installed
ENTRYPOINT ["/app/docker-entrypoint.sh"]
