# API Port Change: 8080 → 9090

## 📋 Summary

The default API port has been changed from **8080** to **9090** to avoid conflicts with other applications.

---

## ✅ What Changed

### **Files Updated**

1. **`.env`**
   - `API_PORT=9090`
   - `APP_API_PORT=9090`

2. **`apps/api/main.py`**
   - Default port in Settings: `9090`

3. **`Makefile`**
   - All curl commands now use port `9090`
   - API server starts on port `9090`

4. **`scripts/test_hybrid_api.py`**
   - API_BASE_URL: `http://localhost:9090`

5. **`scripts/run_e2e_test.sh`**
   - All health checks and API tests use port `9090`

---

## 🚀 How to Use

### **Start API Server**
```bash
make api
# Server runs on http://localhost:9090
```

### **Test Endpoints**
```bash
# Health check
curl http://localhost:9090/health

# ML forecast
curl -H "X-API-Key: changeme-dev-key" \
  "http://localhost:9090/v1/forecast?pair=USDINR&h=4h"

# Hybrid forecast
make curl-hybrid
```

---

## 🔄 Migration Guide

### **If You Have Existing Scripts**

Update any hardcoded URLs from:
```
http://localhost:8080
```

To:
```
http://localhost:9090
```

### **If You Need to Use a Different Port**

Set the `API_PORT` environment variable:

```bash
# Option 1: In .env file
API_PORT=8888

# Option 2: Command line
API_PORT=8888 make api

# Option 3: Export
export API_PORT=8888
make api
```

---

## 📊 Updated Commands

All Makefile commands now use port 9090:

```bash
make api              # Starts on :9090
make curl-health      # Tests :9090/health
make curl-forecast    # Tests :9090/v1/forecast
make curl-hybrid      # Tests :9090/v1/forecast?use_hybrid=true
make test-hybrid-api  # Tests :9090 endpoints
make e2e-quick        # Tests :9090 in E2E tests
```

---

## ✅ Verification

To verify the change worked:

```bash
# 1. Start API
make api

# 2. In another terminal, test
curl http://localhost:9090/health

# Expected output:
# {"status":"ok","env":"local"}
```

---

## 🐛 Troubleshooting

### **Port Already in Use**

If port 9090 is also in use:

```bash
# Check what's using port 9090
lsof -i :9090

# Use a different port
API_PORT=9191 make api
```

### **Connection Refused**

```bash
# Make sure API is running
make api

# Check it's listening on 9090
lsof -i :9090
```

---

## 📝 Notes

- **Default port**: 9090 (was 8080)
- **Configurable**: Yes, via `API_PORT` env var
- **Backward compatibility**: Update your scripts to use 9090
- **Documentation**: All docs updated to reflect new port

---

**Date**: November 29, 2025  
**Reason**: Avoid conflicts with other applications on port 8080
