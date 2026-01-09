# Copyright (c) 2024 Steven Noble <snoble@sonn.com>
# Version: 1.0.0
#
# Makefile for DCMS (Datacenter Management System)
# Builds Docker images and distribution packages

.PHONY: help build build-backend build-frontend build-all installers clean clean-all version

# Variables
VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
IMAGE_PREFIX ?= dcms
REGISTRY ?= 
BACKEND_IMAGE = $(IMAGE_PREFIX)-backend
FRONTEND_IMAGE = $(IMAGE_PREFIX)-frontend
INSTALLER_DIR = installers
TIMESTAMP = $(shell date +%Y%m%d_%H%M%S)

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "DCMS Build System"
	@echo "=================="
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Variables:"
	@echo "  VERSION=$(VERSION)"
	@echo "  IMAGE_PREFIX=$(IMAGE_PREFIX)"
	@echo "  REGISTRY=$(REGISTRY)"
	@echo ""

version: ## Show version information
	@echo "Version: $(VERSION)"
	@echo "Timestamp: $(TIMESTAMP)"

build-backend: ## Build backend Docker image
	@echo "Building backend Docker image..."
	docker build -t $(BACKEND_IMAGE):$(VERSION) -t $(BACKEND_IMAGE):latest ./backend
	@echo "✓ Backend image built: $(BACKEND_IMAGE):$(VERSION)"

build-frontend: ## Build frontend Docker image
	@echo "Building frontend Docker image..."
	docker build -t $(FRONTEND_IMAGE):$(VERSION) -t $(FRONTEND_IMAGE):latest ./frontend
	@echo "✓ Frontend image built: $(FRONTEND_IMAGE):$(VERSION)"

build-all: build-backend build-frontend ## Build all Docker images
	@echo "✓ All images built successfully"

# Installer targets
installers: build-all installer-docker installer-archive ## Build all installers
	@echo "✓ All installers built successfully"

installer-docker: build-all ## Create Docker image installer packages
	@echo "Creating Docker image installer packages..."
	@mkdir -p $(INSTALLER_DIR)
	@echo "Saving backend image..."
	docker save $(BACKEND_IMAGE):$(VERSION) | gzip > $(INSTALLER_DIR)/$(BACKEND_IMAGE)-$(VERSION).tar.gz
	@echo "Saving frontend image..."
	docker save $(FRONTEND_IMAGE):$(VERSION) | gzip > $(INSTALLER_DIR)/$(FRONTEND_IMAGE)-$(VERSION).tar.gz
	@echo "✓ Docker image installers created in $(INSTALLER_DIR)/"

installer-archive: ## Create distribution archive installer
	@echo "Creating distribution archive installer..."
	@mkdir -p $(INSTALLER_DIR)
	@TMP_DIR=$$(mktemp -d) && \
	ARCHIVE_NAME="dcms-$(VERSION)-$(TIMESTAMP).tar.gz" && \
	mkdir -p $$TMP_DIR/dcms-$(VERSION) && \
	cp -r backend frontend docker-compose.yml README.md LICENSE env.example* $$TMP_DIR/dcms-$(VERSION)/ 2>/dev/null || true && \
	cp -r docs $$TMP_DIR/dcms-$(VERSION)/ 2>/dev/null || true && \
	tar -czf $(INSTALLER_DIR)/$$ARCHIVE_NAME -C $$TMP_DIR dcms-$(VERSION) && \
	rm -rf $$TMP_DIR && \
	echo "✓ Distribution archive created: $(INSTALLER_DIR)/$$ARCHIVE_NAME"

installer-compose: ## Create docker-compose installer package
	@echo "Creating docker-compose installer package..."
	@mkdir -p $(INSTALLER_DIR)
	@TMP_DIR=$$(mktemp -d) && \
	INSTALLER_NAME="dcms-docker-compose-$(VERSION)-$(TIMESTAMP)" && \
	mkdir -p $$TMP_DIR/$$INSTALLER_NAME && \
	cp docker-compose.yml README.md LICENSE $$TMP_DIR/$$INSTALLER_NAME/ && \
	cp env.example* $$TMP_DIR/$$INSTALLER_NAME/ 2>/dev/null || true && \
	echo "#!/bin/bash" > $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	echo "# DCMS Docker Compose Installer" >> $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	echo "echo 'Installing DCMS...'" >> $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	echo "docker compose up -d" >> $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	echo "echo 'DCMS installed successfully!'" >> $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	chmod +x $$TMP_DIR/$$INSTALLER_NAME/install.sh && \
	tar -czf $(INSTALLER_DIR)/$$INSTALLER_NAME.tar.gz -C $$TMP_DIR $$INSTALLER_NAME && \
	rm -rf $$TMP_DIR && \
	echo "✓ Docker Compose installer created: $(INSTALLER_DIR)/$$INSTALLER_NAME.tar.gz"

# Tag and push images to registry
tag: build-all ## Tag images with version and latest
	@if [ -n "$(REGISTRY)" ]; then \
		echo "Tagging images for registry $(REGISTRY)..."; \
		docker tag $(BACKEND_IMAGE):$(VERSION) $(REGISTRY)/$(BACKEND_IMAGE):$(VERSION); \
		docker tag $(BACKEND_IMAGE):latest $(REGISTRY)/$(BACKEND_IMAGE):latest; \
		docker tag $(FRONTEND_IMAGE):$(VERSION) $(REGISTRY)/$(FRONTEND_IMAGE):$(VERSION); \
		docker tag $(FRONTEND_IMAGE):latest $(REGISTRY)/$(FRONTEND_IMAGE):latest; \
		echo "✓ Images tagged for registry"; \
	else \
		echo "REGISTRY not set, skipping registry tagging"; \
	fi

push: tag ## Push images to registry
	@if [ -n "$(REGISTRY)" ]; then \
		echo "Pushing images to registry $(REGISTRY)..."; \
		docker push $(REGISTRY)/$(BACKEND_IMAGE):$(VERSION); \
		docker push $(REGISTRY)/$(BACKEND_IMAGE):latest; \
		docker push $(REGISTRY)/$(FRONTEND_IMAGE):$(VERSION); \
		docker push $(REGISTRY)/$(FRONTEND_IMAGE):latest; \
		echo "✓ Images pushed to registry"; \
	else \
		echo "REGISTRY not set, cannot push images"; \
		exit 1; \
	fi

# Cleanup targets
clean: ## Remove installer packages
	@echo "Cleaning installer packages..."
	@rm -rf $(INSTALLER_DIR)
	@echo "✓ Installer packages cleaned"

clean-images: ## Remove Docker images
	@echo "Removing Docker images..."
	@docker rmi $(BACKEND_IMAGE):$(VERSION) $(BACKEND_IMAGE):latest 2>/dev/null || true
	@docker rmi $(FRONTEND_IMAGE):$(VERSION) $(FRONTEND_IMAGE):latest 2>/dev/null || true
	@echo "✓ Docker images removed"

clean-all: clean clean-images ## Remove all build artifacts
	@echo "✓ All build artifacts cleaned"

# Development targets
dev-up: ## Start development environment
	docker compose up -d

dev-down: ## Stop development environment
	docker compose down

dev-logs: ## Show development logs
	docker compose logs -f

dev-rebuild: ## Rebuild and restart development environment
	docker compose up -d --build

# Production build targets
prod-build-backend: ## Build production backend image
	@echo "Building production backend image..."
	docker build -t $(BACKEND_IMAGE):$(VERSION) -t $(BACKEND_IMAGE):latest \
		--target production \
		--build-arg VERSION=$(VERSION) \
		./backend || \
	docker build -t $(BACKEND_IMAGE):$(VERSION) -t $(BACKEND_IMAGE):latest ./backend
	@echo "✓ Production backend image built"

prod-build-frontend: ## Build production frontend image (with build step)
	@echo "Building production frontend image..."
	@cd frontend && npm run build
	docker build -t $(FRONTEND_IMAGE):$(VERSION) -t $(FRONTEND_IMAGE):latest \
		--target production \
		--build-arg VERSION=$(VERSION) \
		./frontend || \
	docker build -t $(FRONTEND_IMAGE):$(VERSION) -t $(FRONTEND_IMAGE):latest ./frontend
	@echo "✓ Production frontend image built"

prod-build: prod-build-backend prod-build-frontend ## Build all production images

# List targets
list-images: ## List all DCMS Docker images
	@echo "DCMS Docker Images:"
	@docker images | grep -E "$(IMAGE_PREFIX)|REPOSITORY" || echo "No DCMS images found"

list-installers: ## List all installer packages
	@echo "Installer Packages:"
	@ls -lh $(INSTALLER_DIR)/ 2>/dev/null || echo "No installer packages found"

# Migration targets
migrate: ## Run database migrations safely (with constraint verification and tests)
	@echo "Running safe migration with full regression testing..."
	@cd backend && python3 scripts/safe_migrate.py

migrate-no-tests: ## Run migrations without running tests (not recommended)
	@echo "Running safe migration (tests skipped)..."
	@cd backend && python3 scripts/safe_migrate.py --skip-tests

migrate-verify: ## Verify constraints after migration
	@echo "Verifying database constraints..."
	@cd backend && python3 scripts/verify_constraints_after_migration.py

migrate-check: ## Check migration safety before committing (REQUIRED before push!)
	@echo "Checking migration safety..."
	@cd backend && python3 scripts/check_migration_safety.py
	@echo "Checking for single migration head..."
	@cd backend && python3 scripts/check_single_head.py
	@echo ""
	@echo "✓ All migration checks passed. Safe to commit/push."

pre-push-check: ## Run all checks before pushing (migrations, tests, etc.)
	@echo "Running pre-push checks..."
	@echo ""
	@echo "1. Checking migration safety..."
	@$(MAKE) migrate-check
	@echo ""
	@echo "2. Checking Python syntax..."
	@cd backend && find . -name "*.py" -path "*/alembic/versions/*" -exec python3 -m py_compile {} \; || (echo "❌ Syntax errors found!" && exit 1)
	@echo ""
	@echo "✓ All pre-push checks passed!"

test-critical: ## Run critical regression tests
	@echo "Running critical regression tests..."
	@cd backend && python3 scripts/run_critical_tests.py

setup-db: ## Seamless database setup (migrations + bootstrap)
	@echo "Running seamless database setup..."
	@cd backend && python3 scripts/setup_database.py

